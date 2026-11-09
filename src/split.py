"""Milestone 5: train/val/test split by MMSI with GroupShuffleSplit (70/15/15).

Output: data/processed/splits.parquet mapping each MMSI to its split.
"""
from __future__ import annotations

import pandas as pd

from src.config import SEED, get_logger, path, project

log = get_logger(__name__)


def split_by_vessel(df: pd.DataFrame, group_col: str = "mmsi") -> pd.Series:
    """Return a Series aligned with df holding 'train' / 'val' / 'test'."""
    raise NotImplementedError("Milestone 5")


def main() -> None:
    raise NotImplementedError("Milestone 5")


if __name__ == "__main__":
    main()
