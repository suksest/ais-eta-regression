"""Download the Kaggle dataset and store each day as a gzip-compressed CSV.

Kaggle no longer serves anonymous downloads, so this needs a logged-in Kaggle CLI
(`.venv/bin/kaggle auth login`). The 3.6 GB archive is fetched once into
data/raw/<dataset>.zip; each requested day is then streamed out of it into
data/raw/tallinn/<day>.csv.gz (20 GB of CSV would not fit; gzip keeps ~3.6 GB and
pandas reads it directly). Days come from `download.days` in configs/project.yaml,
or --days, or --all. Days already present are skipped.
"""
from __future__ import annotations

import argparse
import gzip
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from src.config import get_logger, path, project

log = get_logger(__name__)
CHUNK = 8 * 1024 * 1024


def archive_path() -> Path:
    return path("raw_dir").parent / (project()["kaggle_dataset"].split("/")[-1] + ".zip")


def fetch_archive() -> Path:
    zip_path = archive_path()
    if zip_path.exists():
        return zip_path
    kaggle = Path(sys.executable).with_name("kaggle")  # the venv's CLI
    if not kaggle.exists():  # e.g. Colab, where pip installs to /usr/local/bin
        kaggle = Path(shutil.which("kaggle") or "kaggle")
    log.info("Downloading %s to %s (3.6 GB)", project()["kaggle_dataset"], zip_path.parent)
    subprocess.run(
        [str(kaggle), "datasets", "download", project()["kaggle_dataset"], "-p", str(zip_path.parent)],
        check=True,
    )
    if not zip_path.exists():
        raise FileNotFoundError(f"Kaggle download finished but {zip_path} is missing")
    return zip_path


def extract(days: list[str] | None) -> None:
    out = path("raw_dir")
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(fetch_archive()) as zf:
        members = sorted(n for n in zf.namelist() if n.endswith(".csv"))
        wanted = members if days is None else [f"{d}.csv" for d in days]
        missing = sorted(set(wanted) - set(members))
        if missing:
            raise FileNotFoundError(f"Not in archive: {missing}")
        for i, name in enumerate(wanted, 1):
            target = out / f"{name}.gz"
            if target.exists():
                continue
            plain = out / name
            if plain.exists():  # an earlier uncompressed download: compress it instead
                src_open = lambda: open(plain, "rb")  # noqa: E731
            else:
                src_open = lambda: zf.open(name)  # noqa: E731
            tmp = target.with_suffix(".gz.part")
            with src_open() as src, gzip.open(tmp, "wb", compresslevel=6) as dst:
                shutil.copyfileobj(src, dst, CHUNK)
            tmp.rename(target)
            plain.unlink(missing_ok=True)
            log.info("[%d/%d] %s (%.0f MB gz)", i, len(wanted), target.name, target.stat().st_size / 1e6)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", nargs="+", help="YYYY-MM-DD; default: download.days in project.yaml")
    parser.add_argument("--all", action="store_true", help="every day in the dataset")
    args = parser.parse_args()
    extract(None if args.all else (args.days or project()["download"]["days"]))


if __name__ == "__main__":
    main()
