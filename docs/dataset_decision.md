# Dataset decision (Milestone 1)

## 2026-11-06: SPEC dataset rejected

The SPEC's Kaggle dataset (`satyamrajput7913/ais-ship-tracking-vessel-dynamics-and-eta-data`,
kept in `data/raw/archive_noaa_kaggle/`) cannot support the business question:

- It has no crew-reported ETA. `ETA_hours` equals `min(dist_km / SOG_kmh, 72)` in 100% of rows,
  i.e. the SPEC's physics baseline itself, and 72.5% of rows sit at the 72 h cap.
- `dest_lat`/`dest_lon` are one of 8 k-means region centroids, assigned as the centroid nearest the vessel.
- It covers a single day (2022-03-31, US waters) and has no actual arrival times.

## 2026-11-07: switched to `gaborvisky/ais-dataset`

Raw decoded AIS messages from one receiver near Tallinn, Estonia, 2022-09-08 to 2023-03-07
(181 daily CSVs, 3.6 GB zipped). Voyage messages (type 5) carry the crew's destination and
ETA (month/day/hour/minute, no year), which is the case the SPEC was written for.
Actual arrivals at Tallinn ports can be derived from the tracks.

Alternatives considered: Danish Maritime Authority archive (full ETA dates, wider area, but
~577 MB zipped per day); other Kaggle AIS sets lacked ETA/destination or were the same NOAA day.

License: Apache 2.0 (from Kaggle metadata, checked 2026-11-09). Kaggle subtitle: "6-month long AIS
data recorded near by port of Tallinn"; published for AIS anomaly-detection research (maritime cybersecurity).

Download: Kaggle stopped serving anonymous downloads on 2026-11-09 (all dataset URLs return 404),
so `make download` needs a logged-in Kaggle CLI (`.venv/bin/kaggle auth login`). It fetches the
3.6 GB zip once into `data/raw/`, then writes each day listed in `configs/project.yaml` to
`data/raw/tallinn/<day>.csv.gz`; `make download-all` does every day. Days are stored gzipped
because the 20.4 GB of plain CSV does not fit on the dev machine's free disk.
