"""Milestone 3: feature engineering (haversine, bearing, cyclic encodings).

Output: data/processed/features.parquet. `eta`, MMSI and IMO are never features.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import get_logger, load_config, path

log = get_logger(__name__)

EARTH_RADIUS_NM = 3440.065


def haversine_nm(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Great-circle distance in nautical miles (vectorized, degrees in)."""
    raise NotImplementedError("Milestone 3")


def bearing_deg(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Initial bearing from point 1 to point 2, degrees in [0, 360)."""
    raise NotImplementedError("Milestone 3")


def heading_offset(cog, bearing) -> np.ndarray:
    """Absolute angular difference between COG and bearing, in [0, 180]."""
    raise NotImplementedError("Milestone 3")


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("Milestone 3")


def main() -> None:
    raise NotImplementedError("Milestone 3")


if __name__ == "__main__":
    main()
