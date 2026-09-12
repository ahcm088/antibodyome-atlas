"""Citation helper."""
from __future__ import annotations

from typing import Any

from .datasets import get_dataset


def get_citation(atlas_id: str, ref: str = "main") -> dict[str, Any]:
    """Get the citation for a dataset, ready to paste into a manuscript.

    Returns a dict with ``atlas_id``, ``dataset_link``, ``citation``,
    ``doi``, ``pubmed_link``, ``publisher_link``. Publication fields are
    ``None`` if the record has no associated publication.
    """
    record = get_dataset(atlas_id, ref=ref)
    pub = record.get("publication") or {}
    return {
        "atlas_id": record["atlas_id"],
        "dataset_link": record["dataset_link"],
        "citation": pub.get("citation"),
        "doi": pub.get("doi"),
        "pubmed_link": pub.get("pubmed_link"),
        "publisher_link": pub.get("publisher_link"),
    }
