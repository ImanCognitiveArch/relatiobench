"""Local engineering experiments on authored, synthetic interaction events."""
__version__ = "0.1.0a2"

from .engine import replay
from .schema import ValidationError, load_scenario
from .scoring import score

__all__ = ["replay", "score", "load_scenario", "ValidationError", "__version__"]
