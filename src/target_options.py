"""Milestone 2 decision experiment: how much data does each target definition give?

Option A, observed arrival: hours until the vessel's next stop (see `arrival` in
configs/cleaning.yaml). Option B, crew ETA: hours until the ETA the crew typed in.

Reads data/processed/loaded/ one day at a time and keeps only compact numpy arrays
(~1.3 GB for all 181 days), so it fits in a 12 GB Colab or laptop. Writes
reports/target_options.json and prints a summary.

    python -m src.target_options [--days N]   # N = first N days only (quick test)
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

import numpy as np
import pandas as pd

from src.config import ROOT, get_logger, load_config, path

log = get_logger(__name__)
COLS = ["mmsi", "timestamp", "lat", "lon", "sog", "nav_status", "vessel_type",
        "destination", "eta_month", "eta_day", "eta_hour", "eta_minute"]


def crew_eta_hours(day: pd.DataFrame, rollover_days: float) -> pd.Series:
    """Hours from timestamp to the crew ETA (year inferred); NaN when ETA is n/a."""
    ok = (day.eta_month.between(1, 12) & day.eta_day.between(1, 31)
          & (day.eta_hour < 24) & (day.eta_minute < 60))
    ts = day.timestamp.dt.tz_localize(None)
    eta = pd.to_datetime(dict(year=ts.dt.year, month=day.eta_month, day=day.eta_day,
                              hour=day.eta_hour, minute=day.eta_minute), errors="coerce").where(ok)
    eta = eta.where(eta >= ts - pd.Timedelta(days=rollover_days), eta + pd.DateOffset(years=1))
    return (eta - ts).dt.total_seconds() / 3600


def describe(x: np.ndarray) -> dict:
    if len(x) == 0:
        return {"count": 0}
    q = np.percentile(x, [5, 25, 50, 75, 90, 99])
    return {"count": int(len(x)), "mean": round(float(x.mean()), 2), "max": round(float(x.max()), 2),
            **{f"p{p}": round(float(v), 2) for p, v in zip([5, 25, 50, 75, 90, 99], q)}}


def run(n_days: int | None = None) -> dict:
    clean = load_config("cleaning")
    arr_cfg, sog_cfg, tgt = clean["arrival"], clean["sog"], clean["target"]
    moored = set(load_config("columns")["nav_status_values"]["moored"])
    files = sorted(path("loaded").glob("*.parquet"))[:n_days]
    if not files:
        raise FileNotFoundError("No loaded data; run `make load` first")

    # --- per-day pass: option B counts, and compact arrays for option A ---
    b = Counter()
    b_vessels, dest_counts, b_hours = set(), Counter(), []
    parts = {k: [] for k in ("mmsi", "t", "stopped", "lat", "lon", "vt", "sog")}
    vt_codes: dict[str, int] = {}
    for i, f in enumerate(files, 1):
        day = pd.read_parquet(f, columns=COLS)
        h = crew_eta_hours(day, clean["eta"]["rollover_if_past_days"])
        moving = day.sog.between(arr_cfg["stop_sog_kn"], sog_cfg["valid_range_kn"][1])
        good = moving & (h > tgt["min_hours"]) & (h <= tgt["max_hours"]) & day.destination.notna()
        b.update(rows=len(day), eta_valid=int(h.notna().sum()), eta_past=int((h <= 0).sum()),
                 moving=int(moving.sum()), usable=int(good.sum()))
        b_vessels.update(day.loc[good, "mmsi"].unique())
        dest_counts.update(day.loc[good, "destination"].str.upper()
                           .str.replace(r"[^A-Z]", "", regex=True).value_counts().to_dict())
        b_hours.append(h[good].to_numpy(np.float32))

        stopped = (day.sog < arr_cfg["stop_sog_kn"]) | day.nav_status.isin(moored)
        vt = day.vessel_type.fillna("NA").str.replace("ShipType.", "", regex=False).str.split("_").str[0]
        parts["mmsi"].append(day.mmsi.to_numpy(np.int64))
        parts["t"].append(day.timestamp.dt.tz_localize(None).to_numpy("datetime64[s]").astype(np.int64))
        parts["stopped"].append(stopped.to_numpy(bool))
        parts["lat"].append(day.lat.to_numpy(np.float32))
        parts["lon"].append(day.lon.to_numpy(np.float32))
        parts["sog"].append(day.sog.to_numpy(np.float32))
        parts["vt"].append(vt.map(lambda s: vt_codes.setdefault(s, len(vt_codes))).to_numpy(np.int16))
        if i % 20 == 0 or i == len(files):
            log.info("read %d/%d days", i, len(files))

    total = sum(dest_counts.values())
    top = dest_counts.most_common()
    option_b = {
        **dict(b), "vessels": len(b_vessels), "distinct_destinations": len(dest_counts),
        "row_share_top_10_30_100": [round(sum(c for _, c in top[:n]) / total, 3) for n in (10, 30, 100)],
        "top_destinations": dict(top[:30]),
        "hours_to_eta": describe(np.concatenate(b_hours)),
    }

    # --- option A on all days at once: segments of moving / stopped per vessel ---
    a = {k: np.concatenate(v) for k, v in parts.items()}
    del parts
    order = np.lexsort((a["t"], a["mmsi"]))
    a = {k: v[order] for k, v in a.items()}
    m, t, st = a["mmsi"], a["t"], a["stopped"]
    same = np.r_[False, m[1:] == m[:-1]]
    gap = np.r_[np.inf, np.diff(t)].astype(float)
    new = ~same | (gap > arr_cfg["max_gap_minutes"] * 60) | np.r_[True, st[1:] != st[:-1]]
    start = np.flatnonzero(new)
    end = np.r_[start[1:], len(m)] - 1
    s_stop, s_mmsi, t0, t1 = st[start], m[start], t[start], t[end]
    nxt = slice(1, None)
    contig = np.r_[(s_mmsi[nxt] == s_mmsi[:-1]) & ((t0[nxt] - t1[:-1]) <= arr_cfg["max_gap_minutes"] * 60), False]
    next_long_stop = np.r_[s_stop[nxt] & ((t1[nxt] - t0[nxt]) >= arr_cfg["min_stop_minutes"] * 60), False]
    approach = ~s_stop & contig & next_long_stop          # moving stretch that ends in an arrival
    arrival_seg = np.flatnonzero(approach) + 1

    # per-row hours to arrival for rows in approach stretches that are moving at a valid speed
    seg_id = np.cumsum(new) - 1
    arrival_t = np.full(len(start), -1, np.int64)
    arrival_t[np.flatnonzero(approach)] = t0[arrival_seg]
    row_arr = arrival_t[seg_id]
    valid = (row_arr >= 0) & (a["sog"] >= arr_cfg["stop_sog_kn"]) & (a["sog"] <= sog_cfg["valid_range_kn"][1])
    hours = (row_arr[valid] - t[valid]) / 3600

    names = {v: k for k, v in vt_codes.items()}
    vt_mix = pd.Series(a["vt"][start[arrival_seg]]).map(names).value_counts(normalize=True).round(3)
    loc = pd.Series(np.round(a["lat"][start[arrival_seg]], 2).astype(str)) + "," + \
        pd.Series(np.round(a["lon"][start[arrival_seg]], 2).astype(str))
    option_a = {
        "arrival_events": int(len(arrival_seg)),
        "vessels": int(len(np.unique(s_mmsi[arrival_seg]))),
        "usable_rows": int(valid.sum()),
        "approach_length_hours": describe((t1[approach] - t0[approach]) / 3600),
        "hours_to_arrival": describe(hours),
        "vessel_type_mix": vt_mix.head(10).to_dict(),
        "top_arrival_locations": loc.value_counts().head(15).to_dict(),
    }
    result = {"days": len(files), "first_day": files[0].stem, "last_day": files[-1].stem,
              "option_a_observed_arrival": option_a, "option_b_crew_eta": option_b}
    out = ROOT / "reports" / "target_options.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    log.info("Wrote %s", out)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, help="first N days only")
    print(json.dumps(run(parser.parse_args().days), indent=2))


if __name__ == "__main__":
    main()
