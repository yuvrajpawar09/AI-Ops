from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from drain3.template_miner_config import TemplateMinerConfig

from app import config


def build_template_miner() -> TemplateMiner:
    """Builds (or resumes) the Drain3 template miner.

    Both the live service and training/train.py call this, pointed at the
    same persisted state file (models/drain3_state.bin) and the same
    drain3.ini settings - so a template ID assigned during training means
    the same cluster later during live inference, which is what lets the
    LSTM's learned embeddings stay meaningful at serving time.
    """
    miner_config = TemplateMinerConfig()
    miner_config.load(config.DRAIN_CONFIG_PATH)
    persistence = FilePersistence(config.DRAIN_STATE_PATH)
    return TemplateMiner(persistence_handler=persistence, config=miner_config)
