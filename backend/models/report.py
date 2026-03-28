"""
Re-export Report from models.simulation for backwards compatibility.
The Report SQLAlchemy model is defined in models/simulation.py
alongside Simulation and SimulationEvent (they share the same table relationships).
"""
from models.simulation import Report  # noqa: F401

__all__ = ["Report"]
