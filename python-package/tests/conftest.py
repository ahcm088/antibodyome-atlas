import pytest
import requests

from aabatlas._source import raw_url


@pytest.fixture
def atlas_or_skip():
    try:
        resp = requests.get(raw_url("datasets"), timeout=10)
        ok = resp.status_code == 200
    except requests.RequestException:
        ok = False
    if not ok:
        pytest.skip("metadata/datasets.json not reachable at ref 'main' (repo not pushed yet, or offline)")
