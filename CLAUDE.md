# AIS ETA Regression

The full working spec is in [docs/SPEC.md](docs/SPEC.md). Read it before starting any work.

## Working rules

- Work milestone by milestone (SPEC "Repo structure and milestones"). Finish and verify one milestone before starting the next.
- Do not assume column names. Code reads the real names from `configs/columns.yaml`, which Milestone 1 fills after inspecting the data.
- Every threshold (filters, outlier limits, distance bands) lives in `configs/`, never hardcoded in `src/`.
- Every cleaning rule logs how many rows it dropped, both to the log and to the cleaning funnel in the report.
- Random seed is `42` everywhere (`configs/project.yaml`).
- Split by vessel (MMSI), never by row. The test set is touched only once, in Milestone 8.
- `eta` and anything derived from it (other than the target) and MMSI/IMO are never model features.

## Commands

```bash
make venv        # create .venv with Python 3.11 (via uv) and install requirements
make download    # fetch the Kaggle zip (needs `.venv/bin/kaggle auth login`), store days from configs/project.yaml as .csv.gz
make download-all  # same, all 181 days (~3.6 GB zip + ~3.6 GB gz)
make load        # join position + voyage messages -> data/processed/loaded/<day>.parquet
make target-options  # data volume per target definition -> reports/target_options.json
make colab-bundle    # zip code + configs for notebooks/colab_run.ipynb
make test        # run pytest
make all         # raw data -> report
```

## Milestone status

- [x] 1. Inspect the dataset (switched to Tallinn raw AIS, see docs/dataset_decision.md and findings in configs/columns.yaml)
- [ ] 2. Cleaning
- [ ] 3. Feature engineering
- [ ] 4. EDA
- [ ] 5. Split
- [ ] 6. Baseline
- [ ] 7. Advanced models
- [ ] 8. Final evaluation
- [ ] 9. Report
