"""Sanity checks for the project skeleton. Feature and split tests arrive in
Milestones 3 and 5 (test_features.py, test_split.py)."""
import importlib

import pytest

from src.config import SEED, load_config


@pytest.mark.parametrize("name", ["project", "columns", "cleaning"])
def test_configs_parse(name):
    assert isinstance(load_config(name), dict)


def test_seed_is_42():
    assert SEED == 42


def test_split_fractions_sum_to_one():
    s = load_config("project")["split"]
    assert abs(s["train"] + s["val"] + s["test"] - 1.0) < 1e-9


@pytest.mark.parametrize(
    "module", ["download", "load", "clean", "features", "split", "train", "evaluate", "report"]
)
def test_modules_import(module):
    importlib.import_module(f"src.{module}")
