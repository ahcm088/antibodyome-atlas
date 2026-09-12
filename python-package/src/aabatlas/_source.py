"""Internal: fetch and parse the atlas's GitHub-hosted JSON manifests."""
from __future__ import annotations

import pandas as pd
import requests

_FILES = ("datasets", "publications", "platforms", "link_status", "seeds")
_USER_AGENT = "aabatlas-python/0.1 (+https://github.com/ahcm088/antibodyome-atlas)"


def raw_url(file: str, ref: str = "main") -> str:
    """Build the raw GitHub URL for one of the atlas's metadata files.

    Parameters
    ----------
    file:
        One of "datasets", "publications", "platforms", "link_status", "seeds".
    ref:
        Git ref (branch, tag, or commit SHA) to read from. Defaults to
        "main" (the latest curated data). Pin to a release tag (e.g.
        "v1.0.0") for reproducible results in a publication.
    """
    if file not in _FILES:
        raise ValueError(f"file must be one of {_FILES}, got {file!r}")
    return f"https://raw.githubusercontent.com/ahcm088/antibodyome-atlas/{ref}/metadata/{file}.json"


def fetch(file: str, ref: str = "main") -> pd.DataFrame:
    """Fetch and parse one of the atlas's JSON manifests as a DataFrame.

    Nested fields (e.g. ``conditions``, ``platforms``, ``source_ids``) come
    back as object-dtype columns holding Python lists/dicts.
    """
    url = raw_url(file, ref=ref)
    resp = requests.get(url, timeout=30, headers={"User-Agent": _USER_AGENT})
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)
