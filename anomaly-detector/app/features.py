import torch

# The 4 known services get stable ids 1-4; id 0 is reserved as the
# "unknown service" bucket AND doubles as nn.Embedding's padding_idx, so
# padded timesteps and unrecognized services both map to the same zero row.
SERVICES = ["order-service", "payment-service", "inventory-service", "notification-service"]
SERVICE_TO_ID = {name: i + 1 for i, name in enumerate(SERVICES)}
SERVICE_VOCAB_SIZE = len(SERVICES) + 1

# Upper bound on distinct Drain3 templates we embed. Comfortably above what
# 4 small services should ever produce; id 0 is padding/overflow.
TEMPLATE_VOCAB_SIZE = 128

# A full happy-path order (order-service -> payment-service ->
# notification-service, back to order-service -> inventory-service, back to
# order-service) produces 10 log lines - 16 leaves headroom without wasting
# much compute on padding.
MAX_SEQ_LEN = 16
MIN_SEQ_LEN = 2  # shorter traces are discarded as noise, not trained/scored on

TEMPLATE_EMB_DIM = 8
SERVICE_EMB_DIM = 4
CONT_FEATURE_DIM = 2  # [inter-arrival time, error/warn flag]

_LEVEL_WEIGHT = {"ERROR": 1.0, "WARN": 0.5}


def service_id(service: str) -> int:
    return SERVICE_TO_ID.get(service, 0)


def clamp_template_id(cluster_id: int) -> int:
    """Keeps the id inside the embedding table's valid range. In practice
    this is a bounds safety net, not the anomaly signal itself: a template
    that only ever appears after training was frozen still gets a real
    (in-range) id, but its embedding row was never updated by training, so
    the autoencoder reconstructs it about as well as random noise - the
    anomaly signal falls out of the reconstruction-error scoring on its own.
    """
    return cluster_id if 0 < cluster_id < TEMPLATE_VOCAB_SIZE else 0


def level_flag(level: str) -> float:
    return _LEVEL_WEIGHT.get((level or "").upper(), 0.0)


def build_sequence_tensor(events):
    """events: time-sorted list of dicts with template_id/service_id/level/timestamp.
    Pads or truncates to MAX_SEQ_LEN and returns
    (template_ids, service_ids, cont_features, mask) tensors ready for the model.
    """
    events = events[:MAX_SEQ_LEN]
    template_ids = torch.zeros(MAX_SEQ_LEN, dtype=torch.long)
    service_ids = torch.zeros(MAX_SEQ_LEN, dtype=torch.long)
    cont = torch.zeros(MAX_SEQ_LEN, CONT_FEATURE_DIM, dtype=torch.float)
    mask = torch.zeros(MAX_SEQ_LEN, dtype=torch.float)

    prev_ts = None
    for i, ev in enumerate(events):
        template_ids[i] = ev["template_id"]
        service_ids[i] = ev["service_id"]
        ts = ev["timestamp"]
        inter_arrival = 0.0 if prev_ts is None else max(0.0, ts - prev_ts)
        prev_ts = ts
        cont[i, 0] = min(inter_arrival / 5.0, 5.0)  # squash: gaps >5s all read as "slow"
        cont[i, 1] = level_flag(ev["level"])
        mask[i] = 1.0

    return template_ids, service_ids, cont, mask
