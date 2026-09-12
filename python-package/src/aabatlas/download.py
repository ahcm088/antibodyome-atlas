"""Download a dataset's data file."""
from __future__ import annotations

import warnings
from pathlib import Path
from urllib.parse import urlsplit

import requests

from .datasets import get_dataset

_USER_AGENT = "aabatlas-python/0.1 (+https://github.com/ahcm088/antibodyome-atlas)"


def download(atlas_id: str, destdir: str = ".", destfile: str | None = None, ref: str = "main") -> Path:
    """Download whatever is at the record's ``dataset_link``.

    For records with ``record_type == "DATASET"`` this is usually a
    repository landing page (e.g. a GEO accession page) rather than a
    direct file: check ``curated_availability`` first, and note that some
    repositories require navigating from that page to the actual
    supplementary files by hand.

    Returns the local file path.
    """
    record = get_dataset(atlas_id, ref=ref)

    status = (record.get("curated_availability") or {}).get("data_status")
    if status in ("unavailable", "upon_request"):
        warnings.warn(
            f"curated_availability.data_status for {atlas_id} is {status!r} -- "
            "the data itself may not be directly downloadable. Proceeding to fetch dataset_link anyway."
        )

    url = record["dataset_link"]
    if destfile is None:
        destfile = Path(urlsplit(url).path).name or f"{atlas_id}.html"

    path = Path(destdir) / destfile
    path.parent.mkdir(parents=True, exist_ok=True)

    resp = requests.get(url, timeout=60, headers={"User-Agent": _USER_AGENT}, stream=True)
    resp.raise_for_status()
    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return path
