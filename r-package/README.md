# AAbAtlas

R client for the [antibodyome-atlas](https://github.com/ahcm088/antibodyome-atlas), a curated catalog of autoantibody profiling datasets and papers. See `schema/README.md` in the atlas repo for the data model.

## Install

Not yet on CRAN/r-universe. Until then, install from GitHub:

```r
# install.packages("pak")
pak::pak("ahcm088/antibodyome-atlas/r-package")
```

## Usage

```r
library(AAbAtlas)

# browse
ds <- aab_datasets()
ds[ds$record_type == "DATASET" & ds$total_sample_n > 100, c("atlas_id", "title", "total_sample_n")]

# one record, with its publication and platforms resolved
rec <- aab_dataset("AAB-000004")
rec$title
rec$publication$citation

# citation ready to paste into a manuscript
aab_citation("AAB-000004")

# download the underlying file
aab_download("AAB-000004")
```

By default every function reads the latest curated data (`ref = "main"`). Pin a release tag for reproducibility in a publication:

```r
aab_datasets(ref = "v1.0.0")
```
