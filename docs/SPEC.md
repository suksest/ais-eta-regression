# Case Study Design: Predicting Vessel Time-to-Arrival with Regression (AIS Dataset)

Nov 6, 2026 · @Sukma

## Summary

This project builds a regression model that predicts a vessel's remaining time to arrival (hours) from AIS position data, using the physics baseline `distance / speed` as the benchmark. This document is the working spec for Claude Code: export it to Markdown, save it as `docs/SPEC.md` at the repo root, and reference it from `CLAUDE.md`.

Rules for Claude Code:

- Work milestone by milestone (see Repo structure and milestones). Finish and verify one milestone before starting the next.
- Do not assume column names. Milestone 1 must inspect the dataset and write the actual column mapping to `configs/columns.yaml`.
- Put every threshold (filters, outlier limits) in `configs/`, never hardcoded.
- Log the number of rows dropped by every cleaning decision, both to the log and to the report.
- Use a fixed random seed (`42`) so results are reproducible.

## Background and business question

Main question: how many hours until a vessel reaches its destination, given its current position, speed, and characteristics?

Accurate ETA prediction helps ports schedule berths, reduce queues, and avoid costly rescheduling ([vessel ETA study, VU Amsterdam](https://www.math.vu.nl/~sbhulai/publications/mlwa2025b.pdf)). The catch: AIS ETAs are entered manually by the crew, so they are often inaccurate or not updated.

Sub-questions answered in the report:

1. How well does the simple `distance / speed` baseline predict remaining time to arrival?
2. How much do linear regression, regularized regression, and tree-based models improve on it?
3. Which features matter most, and do patterns differ across vessel types?
4. Under which conditions (long distances, slow vessels, specific types) does the model fail most often?

## Dataset

Source: [AIS Ship Tracking: Vessel Dynamics & ETA Data](https://www.kaggle.com/datasets/satyamrajput7913/ais-ship-tracking-vessel-dynamics-and-eta-data) on Kaggle, with 245k+ AIS records for destination and ETA prediction.

| Column (names to verify) | Status | Use |
| --- | --- | --- |
| `dest_lat`, `dest_lon` | Present, mostly filled | Destination coordinates for distance |
| `eta` | Present, mostly filled | Basis for the target |
| Position timestamp | To verify | Start point of the target |
| Vessel `lat`, `lon` | To verify | Current position |
| SOG, COG, heading | To verify | Motion dynamics |
| MMSI / IMO | To verify | Vessel ID for group split |
| Type, length, width, draught | To verify | Vessel characteristics |
| Navigational status | To verify | Filter anchored or moored vessels |

Open questions answered in Milestone 1:

- Is `eta` a full datetime, or only month-day-hour-minute without a year?
- Time zone of the timestamp and `eta` (assume UTC until proven otherwise).
- Is there an actual arrival time? If so, use it as the target instead of `eta`.
- Missing-value percentage per column and number of unique vessels.

## Target and features

The target is remaining time to arrival in hours, computed from the difference between `eta` and the position timestamp:

```latex
\text{time\_to\_arrival\_h} = \frac{\text{eta} - \text{timestamp}}{3600\ \text{s}}
```

Also keep `log1p(time_to_arrival_h)` as an alternative target, since the distribution is likely heavily right-skewed.

| Feature | How to build | Notes |
| --- | --- | --- |
| `distance_nm` | Haversine from (`lat`, `lon`) to (`dest_lat`, `dest_lon`), in nautical miles | Strongest feature |
| `sog_kn` | Speed as reported (knots) | Drop invalid values |
| `naive_eta_h` | `distance_nm / sog_kn` when SOG > 0.5 kn | Used as baseline and feature |
| `bearing_to_dest` | Bearing from position to destination (degrees) |  |
| `heading_offset` | Absolute difference of COG and `bearing_to_dest`, normalized to 0–180 | Is the vessel actually heading there |
| `cog_sin`, `cog_cos` | Cyclic encoding of COG | Avoids the 359° to 0° jump |
| `hour_sin`, `hour_cos`, `dayofweek` | From timestamp |  |
| Vessel type | One-hot, rare categories merged into "Other" |  |
| Length, width, draught | Numeric, median imputation per type | If available |

Forbidden as features: `eta` itself and anything derived from it other than the target, plus MMSI/IMO (used only for grouping).

## Data cleaning and validation

All thresholds below are starting values in `configs/cleaning.yaml`; adjust them after EDA and record why.

| Rule | Starting value | Reason |
| --- | --- | --- |
| Lat in \[-90, 90\], lon in \[-180, 180\] | — | Invalid coordinates |
| Drop `(0, 0)` coordinates for position and destination | — | Common AIS placeholder |
| Valid SOG | 0–40 kn | 102.3 kn in AIS means not available |
| Vessel moving | SOG ≥ 0.5 kn | Stationary vessels make the target meaningless |
| Navigational status | Drop "at anchor" and "moored" | Not underway |
| Positive target | `time_to_arrival_h` > 0 | ETA already passed |
| Maximum target | ≤ 720 hours (30 days) | ETA not updated or mis-entered |
| Implied speed | 0.5–40 kn from `distance_nm / time_to_arrival_h` | ETA inconsistent with distance |
| Duplicates | Identical MMSI + timestamp | Repeated messages |

If `eta` has no year, take the year from the timestamp. If the result is earlier than the timestamp, add one year (year rollover case).

This milestone outputs a "cleaning funnel" table: row counts before and after each rule.

## Splitting and leakage prevention

Split by vessel, not by row: each vessel has many near-identical records, so a random split would make test scores overly optimistic.

- Train 70%, validation 15%, test 15%, using `GroupShuffleSplit` with MMSI as the group.
- Cross-validation on train uses `GroupKFold` (k = 5).
- Optional robustness check: a time-based split (most recent data as test), if the date range is long enough.
- Fit all transforms (imputer, scaler, encoder) on train only, wrapped in `sklearn.Pipeline` + `ColumnTransformer`.
- Touch the test set only once, in the final evaluation milestone.
- Automated test: no MMSI appears in more than one split.

## Models and evaluation

Models are compared in tiers, from the physics baseline up to tree-based models, with MAE (hours) as the primary metric.

| # | Model | Purpose | Tuning |
| --- | --- | --- | --- |
| 0 | `naive_eta_h = distance_nm / sog_kn` | Physics baseline, no training | — |
| 1 | Linear Regression | Statistical baseline, coefficient interpretation | — |
| 2 | Ridge, Lasso | Regularization and feature selection | `alpha` via GroupKFold |
| 3 | Random Forest | Capture non-linearity | `max_depth`, `min_samples_leaf` |
| 4 | XGBoost or LightGBM | Expected strongest model | Randomized search, early stopping on validation |

Train each model twice: on the raw target and on the `log1p` target (predictions are converted back with `expm1` before computing metrics).

Metrics on the test set:

- MAE (hours), the primary metric because it is easy to explain to port stakeholders.
- RMSE (hours) and R².
- MAE by distance band: < 50 nm, 50–200 nm, 200–1000 nm, > 1000 nm.
- MAE by vessel type.

Required analysis:

- Residuals vs predictions and vs distance plots.
- Linear/Ridge coefficients (standardized features) and permutation importance for tree models.
- The five largest errors with their likely causes.

## Repo structure and milestones

Stack: Python 3.11, pandas, numpy, scikit-learn, xgboost (or lightgbm), matplotlib, seaborn, pyyaml, pytest. Dependencies in `requirements.txt` with pinned versions.

```text
ais-eta-regression/
├── CLAUDE.md              # points to docs/SPEC.md, working rules
├── docs/SPEC.md           # this document
├── configs/
│   ├── columns.yaml       # actual column name mapping
│   └── cleaning.yaml      # filter thresholds
├── data/
│   ├── raw/               # Kaggle CSV, not committed
│   └── processed/         # cleaned & featurized parquet
├── notebooks/
│   ├── 01_eda.ipynb
│   └── 02_results.ipynb
├── src/
│   ├── load.py            # read raw + rename via columns.yaml
│   ├── clean.py           # cleaning rules + funnel
│   ├── features.py        # haversine, bearing, encoding
│   ├── split.py           # GroupShuffleSplit by MMSI
│   ├── train.py           # all models + tuning
│   └── evaluate.py        # metrics, plots, tables
├── tests/                 # pytest for features & split
├── reports/figures/
└── Makefile               # make data / features / train / evaluate
```

Milestones (complete in order):

1. **Inspect the dataset.** Download via the Kaggle API to `data/raw/`; print `dtypes`, sample rows, missing-value percentages, unique MMSI count, and the `eta` format. Write `configs/columns.yaml` and answer the open questions in the Dataset section.
2. **Cleaning.** Implement `clean.py` per the rules table and produce the cleaning funnel.
3. **Feature engineering.** Implement `features.py` plus unit tests for haversine (e.g. one degree of latitude ≈ 60 nm) and `heading_offset`.
4. **EDA.** `01_eda.ipynb`: target distribution (raw and log), distance vs target scatter, feature correlations, patterns by vessel type.
5. **Split.** `split.py` plus a test that no MMSI leaks across splits.
6. **Baseline.** Models 0 and 1; report validation MAE.
7. **Advanced models.** Models 2–4 tuned on validation; save the best model to `models/`.
8. **Final evaluation.** Run once on the test set; produce the metrics table, residual plots, importance, and error analysis.
9. **Report.** Summarize in `reports/report.md` (see Deliverables).

## Deliverables, limitations, and acceptance criteria

Final deliverables:

- `reports/report.md` covering the business question, dataset, cleaning funnel, EDA, model comparison, error analysis, limitations, and recommendations.
- `reports/figures/` with every plot the report references.
- A repo that reruns from scratch with `make all`.

Limitations the report must state:

- The target comes from crew-reported ETAs, not actual arrival times. The model learns the *reported ETA*.
- Distance is great-circle, not the actual sailing route (straits, channels, routing around land).
- External factors such as weather and port congestion are not in the dataset.

Acceptance criteria:

- [ ] `columns.yaml` is filled and the open questions in the Dataset section are answered
- [ ] The cleaning funnel prints row counts per rule
- [ ] `pytest` passes, including the haversine test and the no-MMSI-leakage test
- [ ] Models 0–4 are reported with MAE, RMSE, and R² on the test set
- [ ] The best model beats the physics baseline on MAE, or the report explains why not
- [ ] MAE by distance band and by vessel type is available
- [ ] The report includes a limitations section
- [ ] `make all` runs from raw data to report with no manual steps
