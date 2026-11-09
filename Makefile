PYTHON_VERSION ?= 3.11
VENV       := .venv
PY         := $(VENV)/bin/python

.PHONY: all venv download download-all load inspect data features split train evaluate report test notebooks clean-data colab-bundle target-options

all: load data features split train evaluate report

venv: $(VENV)/.installed

$(VENV)/.installed: requirements.txt
	[ -x $(PY) ] || uv venv --python $(PYTHON_VERSION) $(VENV)
	uv pip install --python $(PY) -r requirements.txt
	touch $@

# Days come from download.days in configs/project.yaml; `make download-all` fetches all 181.
download: venv
	$(PY) -m src.download

download-all: venv
	$(PY) -m src.download --all

load: venv
	$(PY) -m src.load

inspect: venv
	$(PY) -m src.load --inspect

data: venv
	$(PY) -m src.clean

features: venv
	$(PY) -m src.features

split: venv
	$(PY) -m src.split

train: venv
	$(PY) -m src.train

evaluate: venv
	$(PY) -m src.evaluate

report: venv
	$(PY) -m src.report

notebooks: venv
	$(VENV)/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

test: venv
	$(PY) -m pytest

clean-data:
	rm -f data/processed/*.parquet

# Code + configs (no data) for running on Google Colab: see notebooks/colab_run.ipynb
colab-bundle:
	mkdir -p dist
	rm -f dist/ais-eta-regression-src.zip
	zip -qr dist/ais-eta-regression-src.zip src configs tests docs notebooks requirements.txt Makefile pytest.ini CLAUDE.md -x '*__pycache__*' '*.ipynb_checkpoints*'
	@ls -la dist/ais-eta-regression-src.zip

target-options: venv
	$(PY) -m src.target_options
