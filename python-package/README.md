# aabatlas

Python client for the [antibodyome-atlas](https://github.com/ahcm088/antibodyome-atlas), a curated catalog of autoantibody profiling datasets and papers. See `schema/README.md` in the atlas repo for the data model. Mirrors the R client, [AAbAtlas](../r-package).

## Install

```bash
pip install aabatlas
```

## Usage

```python
import aabatlas

# browse
ds = aabatlas.list_datasets()
ds[(ds["record_type"] == "DATASET") & (ds["total_sample_n"] > 100)][["atlas_id", "title", "total_sample_n"]]

# one record, with its publication and platforms resolved
rec = aabatlas.get_dataset("AAB-000004")
rec["title"]
rec["publication"]["citation"]

# citation ready to paste into a manuscript
aabatlas.get_citation("AAB-000004")

# download the underlying file
aabatlas.download("AAB-000004")
```

By default every function reads the latest curated data (`ref="main"`). Pin a release tag for reproducibility in a publication:

```python
aabatlas.list_datasets(ref="v1.0.0")
```
