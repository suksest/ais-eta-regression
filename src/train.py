"""Milestones 6-7: physics baseline, linear, regularized, and tree models.

Each model is trained on the raw and log1p targets, tuned with GroupKFold on
train and compared on validation. The best model is saved to models/.
The test split is NOT used here.
"""
from __future__ import annotations

import argparse

from src.config import SEED, get_logger, path, project

log = get_logger(__name__)

MODELS = ["naive", "linear", "ridge", "lasso", "random_forest", "xgboost"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=MODELS, choices=MODELS)
    parser.parse_args()
    raise NotImplementedError("Milestones 6-7")


if __name__ == "__main__":
    main()
