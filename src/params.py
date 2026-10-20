"""
Project-wide constants, read once from params.yaml at the repository root (PRAHAR_MASTER_PLAN.md WS-02.1).

Usage:  from src.params import P;  P["qc"]["rain_max_mm_h"]
"""
from pathlib import Path

import yaml

PARAMS_FILE = Path(__file__).resolve().parent.parent / "params.yaml"
P: dict = yaml.safe_load(PARAMS_FILE.read_text(encoding="utf-8"))
