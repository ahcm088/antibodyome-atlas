"""List and resolve atlas records."""
from __future__ import annotations

from typing import Any

import pandas as pd

from ._source import fetch


def list_datasets(ref: str = "main") -> pd.DataFrame:
    """List all datasets/papers in the atlas.

    Columns match ``schema/dataset.schema.json`` in the atlas repo
    (``atlas_id``, ``record_type``, ``title``, ``organism``, ``conditions``,
    ``total_sample_n``, ``platforms``, ``dataset_link``,
    ``curated_availability``, etc.). List/dict-valued fields come back as
    Python objects in object-dtype columns.
    """
    return fetch("datasets", ref=ref)


def list_publications(ref: str = "main") -> pd.DataFrame:
    """List all publications referenced by atlas datasets."""
    return fetch("publications", ref=ref)


def list_platforms(ref: str = "main") -> pd.DataFrame:
    """List all assay platforms referenced by atlas datasets.

    Per-study protein/feature counts live on the dataset record
    (``list_datasets()["platforms"]``), not here -- see ``schema/README.md``
    in the atlas repo for why.
    """
    return fetch("platforms", ref=ref)


def list_link_status(ref: str = "main") -> pd.DataFrame:
    """List the link-reachability check history.

    One row per automated check, appended over time by the atlas's
    scheduled link checker. ``reachable`` is the raw HTTP signal;
    ``likely_bot_blocked`` flags 403/429 responses from publisher anti-bot
    defenses, which are not necessarily dead links.
    """
    return fetch("link_status", ref=ref)


def get_dataset(atlas_id: str, ref: str = "main") -> dict[str, Any]:
    """Get a single dataset record, with its publication and platforms resolved.

    Returns a dict with the dataset's fields plus two resolved keys:
    ``publication`` (a dict, or ``None`` if the record has no associated
    publication) and ``platforms_detail`` (a list combining each
    ``platforms[].platform_id`` from the dataset with the matching row from
    ``list_platforms()``, keeping ``n_proteins_reported``).
    """
    ds = list_datasets(ref=ref)
    match = ds[ds["atlas_id"] == atlas_id]
    if match.empty:
        raise ValueError(f"No dataset found with atlas_id: {atlas_id}")
    record = match.iloc[0].to_dict()

    pub_id = record.get("publication_id")
    if pub_id:
        pubs = list_publications(ref=ref)
        pub_match = pubs[pubs["publication_id"] == pub_id]
        record["publication"] = pub_match.iloc[0].to_dict() if not pub_match.empty else None
    else:
        record["publication"] = None

    platforms = record.get("platforms") or []
    detail = []
    if platforms:
        all_platforms = list_platforms(ref=ref)
        for p in platforms:
            merged = dict(p)
            prow = all_platforms[all_platforms["platform_id"] == p["platform_id"]]
            if not prow.empty:
                merged.update({k: v for k, v in prow.iloc[0].to_dict().items() if k != "platform_id"})
            detail.append(merged)
    record["platforms_detail"] = detail

    return record
