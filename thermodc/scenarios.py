"""Reproducible operating scenarios."""
from .model import Inputs

SCENARIOS = {
    "Normal operation": Inputs(),
    "Peak IT load": Inputs(100, 22, 85, 3.0, 25, 25),
    "Airflow failure": Inputs(80, 22, 40, 2.5, 40, 30),
    "Efficient cooling": Inputs(65, 19, 130, 5.0, 5, 0),
}
