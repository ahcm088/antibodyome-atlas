import pytest

import aabatlas


def test_raw_url_builds_the_expected_url():
    assert aabatlas.raw_url("datasets", ref="v1.0.0") == (
        "https://raw.githubusercontent.com/ahcm088/antibodyome-atlas/v1.0.0/metadata/datasets.json"
    )
    with pytest.raises(ValueError):
        aabatlas.raw_url("nope")


def test_list_datasets_returns_expected_columns(atlas_or_skip):
    ds = aabatlas.list_datasets()
    assert len(ds) > 0
    for col in ("atlas_id", "record_type", "title", "dataset_link"):
        assert col in ds.columns


def test_get_dataset_resolves_publication_and_platforms(atlas_or_skip):
    ds = aabatlas.list_datasets()
    target = ds[ds["publication_id"].notna()]["atlas_id"].iloc[0]
    record = aabatlas.get_dataset(target)
    assert record["atlas_id"] == target
    assert record["publication"] is not None


def test_get_dataset_raises_on_unknown_atlas_id(atlas_or_skip):
    with pytest.raises(ValueError, match="No dataset found"):
        aabatlas.get_dataset("AAB-999999")


def test_get_citation_returns_expected_keys(atlas_or_skip):
    ds = aabatlas.list_datasets()
    target = ds[ds["publication_id"].notna()]["atlas_id"].iloc[0]
    cite = aabatlas.get_citation(target)
    for key in ("atlas_id", "citation", "doi"):
        assert key in cite
