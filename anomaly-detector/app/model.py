import torch
import torch.nn as nn

from app.features import (
    CONT_FEATURE_DIM,
    SERVICE_EMB_DIM,
    SERVICE_VOCAB_SIZE,
    TEMPLATE_EMB_DIM,
    TEMPLATE_VOCAB_SIZE,
)

HIDDEN_DIM = 32


class LogSequenceAutoencoder(nn.Module):
    """Sequence-to-sequence LSTM autoencoder over per-trace log sequences.

    Each log line is one timestep: its Drain3 template id and service name
    are embedded and concatenated with two numeric features (inter-arrival
    time, error/warn flag). An encoder LSTM compresses the whole sequence
    into a single fixed-size hidden state; a decoder LSTM is handed that
    same vector at every timestep and tries to reconstruct the original
    per-timestep feature vectors from it.

    Trained only on normal traffic, the network gets good at compressing and
    reconstructing normal call patterns through that bottleneck. A sequence
    that doesn't fit those patterns - wrong call order, a missing step, an
    unusual timing gap, a template the model barely saw during training -
    reconstructs poorly. That reconstruction error is the anomaly score,
    which is why no labeled anomaly examples are needed: the model never
    sees an "anomaly" class, it just gets worse at reconstructing things
    that don't look like what it was shown.
    """

    def __init__(self, cont_dim=CONT_FEATURE_DIM):
        super().__init__()
        self.template_emb = nn.Embedding(TEMPLATE_VOCAB_SIZE, TEMPLATE_EMB_DIM, padding_idx=0)
        self.service_emb = nn.Embedding(SERVICE_VOCAB_SIZE, SERVICE_EMB_DIM, padding_idx=0)
        self.cont_dim = cont_dim
        self.input_dim = TEMPLATE_EMB_DIM + SERVICE_EMB_DIM + cont_dim

        self.encoder = nn.LSTM(self.input_dim, HIDDEN_DIM, batch_first=True)
        self.decoder = nn.LSTM(HIDDEN_DIM, HIDDEN_DIM, batch_first=True)
        self.output_layer = nn.Linear(HIDDEN_DIM, self.input_dim)

    def embed(self, template_ids, service_ids, cont_feats):
        return torch.cat([
            self.template_emb(template_ids),
            self.service_emb(service_ids),
            cont_feats,
        ], dim=-1)

    def forward(self, template_ids, service_ids, cont_feats):
        x = self.embed(template_ids, service_ids, cont_feats)  # (B, T, input_dim)
        seq_len = x.size(1)

        _, (h_n, _) = self.encoder(x)  # h_n: (1, B, HIDDEN_DIM) - the sequence's compressed summary

        # Repeat that single summary vector across every decoder timestep,
        # forcing the whole sequence's information through one bottleneck -
        # the core trick that makes reconstruction error a meaningful signal
        # (same idea as Malhotra et al.'s LSTM encoder-decoder anomaly detector).
        context = h_n.permute(1, 0, 2).repeat(1, seq_len, 1)  # (B, T, HIDDEN_DIM)
        decoded, _ = self.decoder(context)
        reconstruction = self.output_layer(decoded)  # (B, T, input_dim)
        return reconstruction, x


def sequence_errors(reconstruction, target, mask):
    """Per-sample mean squared reconstruction error over valid (non-padded)
    timesteps only. Shapes: reconstruction/target (B,T,D), mask (B,T) ->
    returns (B,). This is the anomaly score."""
    m = mask.unsqueeze(-1)
    se = (reconstruction - target) ** 2 * m
    return se.sum(dim=(1, 2)) / m.sum(dim=(1, 2)).clamp(min=1e-8) / target.shape[-1]


def masked_mse_loss(reconstruction, target, mask):
    return sequence_errors(reconstruction, target, mask).mean()
