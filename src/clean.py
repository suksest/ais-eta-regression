"""Milestone 2: apply cleaning rules from configs/cleaning.yaml and build the cleaning funnel.

Every rule logs rows before/after; the funnel is written to
reports/cleaning_funnel.csv for the report. Output: data/processed/clean.parquet.
"""
from __future__ import annotations

import pandas as pd

from src.config import get_logger, load_config, path

log = get_logger(__name__)


def build_target(df: pd.DataFrame) -> pd.DataFrame:
    """Parse eta (handling missing year and year rollover) and add
    time_to_arrival_h and log1p target."""
    raise NotImplementedError("Milestone 2")


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply each rule in order. Returns (clean_df, funnel_df) where funnel_df has
    columns: rule, rows_before, rows_after, dropped."""
    raise NotImplementedError("Milestone 2")


def main() -> None:
    raise NotImplementedError("Milestone 2")


if __name__ == "__main__":
    main()
