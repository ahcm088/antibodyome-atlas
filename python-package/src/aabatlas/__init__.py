"""Client for the antibodyome-atlas."""
from ._source import raw_url
from .citation import get_citation
from .datasets import get_dataset, list_datasets, list_link_status, list_platforms, list_publications
from .download import download

__version__ = "0.1.0"

__all__ = [
    "list_datasets",
    "list_publications",
    "list_platforms",
    "list_link_status",
    "get_dataset",
    "get_citation",
    "download",
    "raw_url",
]
