"""Milestone 1: read raw daily AIS message files and build one row per position report.

Each Class A position report is joined to the most recent earlier voyage message
(destination, crew ETA, draught, dimensions) of the same vessel. Column names come
from configs/columns.yaml. Output: data/processed/loaded/<day>.parquet.

`python -m src.load --inspect` prints an overview instead.
"""
from __future__ import annotations

import argparse
import csv

import pandas as pd

from src.config import get_logger, load_config, path

log = get_logger(__name__)


def raw_files():
    cfg = load_config("columns")
    files = sorted(path("raw_dir").glob(cfg["raw_glob"]))
    if not files:
        raise FileNotFoundError(f"No raw files in {path('raw_dir')}; run `make download`")
    return files


def read_day(f) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (positions, voyages) for one daily file, with canonical column names."""
    cfg = load_config("columns")
    pos_map = {raw: canon for canon, raw in cfg["position_columns"].items()}
    voy_map = {raw: canon for canon, raw in cfg["voyage_columns"].items()}
    usecols = sorted(set(pos_map) | set(voy_map) | {"msg_type"})
    df = pd.read_csv(
        f, sep=cfg["read"]["sep"], index_col=cfg["read"]["index_col"], usecols=usecols,
        quoting=csv.QUOTE_NONE, low_memory=False,
    )
    mt = cfg["message_types"]
    pos = df.loc[df["msg_type"].isin(mt["position"]), list(pos_map)].rename(columns=pos_map)
    voy = df.loc[df["msg_type"].isin(mt["voyage"]), list(voy_map)].rename(columns=voy_map)
    for d in (pos, voy):
        d["timestamp"] = pd.to_datetime(d["timestamp"], format=cfg["formats"]["timestamp"], utc=True)
        d.dropna(subset=["mmsi", "timestamp"], inplace=True)
        d["mmsi"] = d["mmsi"].astype("int64")
    log.info("%s: %d messages, %d positions, %d voyage messages", f.name, len(df), len(pos), len(voy))
    return pos, voy


def join_voyage(pos: pd.DataFrame, voy: pd.DataFrame) -> pd.DataFrame:
    """Attach to each position the latest voyage message of the same MMSI, if not too old."""
    cfg = load_config("columns")["join"]
    voy = voy.rename(columns={"timestamp": "voyage_timestamp"})
    out = pd.merge_asof(
        pos.sort_values("timestamp"), voy.sort_values("voyage_timestamp"),
        left_on="timestamp", right_on="voyage_timestamp", by="mmsi", direction="backward",
        tolerance=pd.Timedelta(hours=cfg["max_voyage_age_hours"]),
    )
    out["length"] = out.pop("to_bow") + out.pop("to_stern")
    out["width"] = out.pop("to_port") + out.pop("to_starboard")
    return out


def load(save: bool = True, files=None) -> pd.DataFrame | None:
    """Process raw files one day at a time (all days would not fit in memory).

    The latest voyage message per vessel is carried into the next day, so positions
    just after midnight still get yesterday's destination and ETA. With save=True each
    day is written to data/processed/loaded/<day>.parquet and nothing is returned;
    with save=False the joined days are returned (use for small inspections only).
    """
    out_dir = path("loaded")
    out_dir.mkdir(parents=True, exist_ok=True)
    carry = None
    kept, n_rows, vessels = [], 0, set()
    for f in files or raw_files():
        pos, voy = read_day(f)
        voy_all = voy if carry is None else pd.concat([carry, voy], ignore_index=True)
        day = join_voyage(pos, voy_all).sort_values(["mmsi", "timestamp"]).reset_index(drop=True)
        carry = voy_all.sort_values("timestamp").drop_duplicates("mmsi", keep="last")
        n_rows += len(day)
        vessels.update(day["mmsi"].unique())
        if save:
            day.to_parquet(out_dir / f"{f.name.split('.')[0]}.parquet", index=False)
        else:
            kept.append(day)
    log.info("Loaded %d positions from %d vessels", n_rows, len(vessels))
    return None if save else pd.concat(kept, ignore_index=True)


def read_loaded(columns: list[str] | None = None, days: list[str] | None = None) -> pd.DataFrame:
    """Read the per-day parquet files written by load()."""
    files = sorted(path("loaded").glob("*.parquet"))
    if days is not None:
        files = [f for f in files if f.stem in set(days)]
    if not files:
        raise FileNotFoundError(f"No loaded data in {path('loaded')}; run `make load`")
    return pd.concat((pd.read_parquet(f, columns=columns) for f in files), ignore_index=True)


def inspect(df: pd.DataFrame) -> None:
    pd.set_option("display.width", 200, "display.max_columns", 50)
    print("\n== dtypes ==\n" + df.dtypes.to_string())
    print("\n== sample rows ==\n" + df.sample(5, random_state=42).T.to_string())
    miss = (df.isna().mean() * 100).round(2)
    print("\n== missing % ==\n" + miss[miss > 0].to_string())
    print(f"\nrows: {len(df):,}  vessels: {df['mmsi'].nunique():,}")
    print(f"timestamp range: {df['timestamp'].min()} -> {df['timestamp'].max()}")
    print("\n== nav_status ==\n" + df["nav_status"].value_counts().head(10).to_string())
    print("\n== vessel_type (per vessel) ==\n"
          + df.drop_duplicates("mmsi", keep="last")["vessel_type"].value_counts().head(10).to_string())
    print("\n== destination (per vessel, top 20) ==\n"
          + df.drop_duplicates("mmsi", keep="last")["destination"].value_counts().head(20).to_string())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true", help="print dataset overview")
    args = parser.parse_args()
    if args.inspect:  # first raw day only, to stay fast
        inspect(load(save=False, files=raw_files()[:1]))
    else:
        load()


if __name__ == "__main__":
    main()
