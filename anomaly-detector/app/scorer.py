import json
import logging
import os

import torch

from app import config
from app.features import (
    CONT_FEATURE_DIM,
    CONT_FEATURE_DIM_V2,
    build_sequence_tensor,
    build_sequence_tensor_v2,
)
from app.model import LogSequenceAutoencoder, sequence_errors

logger = logging.getLogger(__name__)


def _feature_fn():
    if config.FEATURE_VERSION == "v2":
        return build_sequence_tensor_v2, CONT_FEATURE_DIM_V2
    return build_sequence_tensor, CONT_FEATURE_DIM


class AnomalyScorer:
    def __init__(self):
        self.build, cont_dim = _feature_fn()
        self.model = LogSequenceAutoencoder(cont_dim=cont_dim)
        # weights_only=True restricts unpickling to plain tensors/primitives.
        # training/train.py saves a bare state_dict, so nothing here needs the
        # unrestricted loader - and since the .pt ships in the public repo,
        # this stops a swapped-in malicious checkpoint from executing code at
        # load time. (Becomes torch's default in 2.6+; set explicitly because
        # this project pins torch 2.3.1, where the default is still False.)
        state_dict = torch.load(config.MODEL_PATH, map_location="cpu", weights_only=True)
        self.model.load_state_dict(state_dict)
        self.model.eval()

        with open(config.THRESHOLD_PATH) as f:
            stats = json.load(f)
        self.threshold = stats["threshold"]

        logger.info("Loaded %s anomaly model from %s (threshold=%.5f)",
                    config.FEATURE_VERSION, config.MODEL_PATH, self.threshold)

    @torch.no_grad()
    def score(self, events):
        """events: time-sorted list of enriched dicts (see kafka_consumer).
        Returns (score, is_anomaly)."""
        template_ids, service_ids, cont, mask = self.build(events)
        recon, target = self.model(
            template_ids.unsqueeze(0), service_ids.unsqueeze(0), cont.unsqueeze(0)
        )
        error = sequence_errors(recon, target, mask.unsqueeze(0)).item()
        return error, error > self.threshold


def try_load_scorer():
    """Returns an AnomalyScorer if a trained model exists on disk, else None.
    A missing model isn't an error - it just means training/train.py hasn't
    been run yet. The service still starts and buffers traces either way;
    it simply won't flag anomalies until a model appears and it's restarted.
    """
    if not (os.path.exists(config.MODEL_PATH) and os.path.exists(config.THRESHOLD_PATH)):
        logger.warning(
            "No trained model found at %s - /anomalies will stay empty until you run "
            "training/train.py (see README) and restart this service.",
            config.MODEL_PATH,
        )
        return None
    return AnomalyScorer()
