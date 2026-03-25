"""
EcoDispatch: Carbon-Aware Data Center Energy Optimizer

This package provides tools for simulating and optimizing energy dispatch
in data centers to minimize carbon emissions.
"""

from .env_utils import load_local_env
from .simulation import EcoDispatch

load_local_env()

__version__ = "0.1.0"
__all__ = ["EcoDispatch"]
