"""
EcoDispatch: Carbon-Aware Data Center Energy Optimization Prototype

This package provides tools for simulating and comparing energy-dispatch
strategies in data-center scenarios with carbon, cost, solar, battery,
and flexible-load considerations.
"""

from .env_utils import load_local_env
from .simulation import EcoDispatch

load_local_env()

__version__ = "0.1.0"
__all__ = ["EcoDispatch"]
