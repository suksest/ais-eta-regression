"""Shared helpers: config loading, paths, logging, seed."""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "configs"


@lru_cache(maxsize=None)
def load_config(name: str) -> dict[str, Any]:
    """Load configs/<name>.yaml (name without extension)."""
    with open(CONFIG_DIR / f"{name}.yaml") as f:
        return yaml.safe_load(f)


def project() -> dict[str, Any]:
    return load_config("project")


def path(key: str) -> Path:
    """Absolute path for a key under `paths` in configs/project.yaml."""
    return ROOT / project()["paths"][key]


SEED: int = project()["seed"]


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger(name)
