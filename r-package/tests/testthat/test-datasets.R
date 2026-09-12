test_that("aab_raw_url builds the expected URL", {
  expect_equal(
    aab_raw_url("datasets", ref = "v1.0.0"),
    "https://raw.githubusercontent.com/ahcm088/antibodyome-atlas/v1.0.0/metadata/datasets.json"
  )
  expect_error(aab_raw_url("nope"))
})

test_that("aab_datasets returns a tibble with expected columns", {
  skip_if_atlas_unreachable()
  ds <- aab_datasets()
  expect_s3_class(ds, "tbl_df")
  expect_true(all(c("atlas_id", "record_type", "title", "dataset_link") %in% names(ds)))
  expect_true(nrow(ds) > 0)
})

test_that("aab_dataset resolves publication and platforms", {
  skip_if_atlas_unreachable()
  ds <- aab_datasets()
  target <- ds$atlas_id[!is.na(ds$publication_id)][1]
  record <- aab_dataset(target)
  expect_equal(record$atlas_id, target)
  expect_true(is.data.frame(record$publication))
})

test_that("aab_dataset errors on an unknown atlas_id", {
  skip_if_atlas_unreachable()
  expect_error(aab_dataset("AAB-999999"), "No dataset found")
})

test_that("aab_citation returns the expected columns", {
  skip_if_atlas_unreachable()
  ds <- aab_datasets()
  target <- ds$atlas_id[!is.na(ds$publication_id)][1]
  cite <- aab_citation(target)
  expect_true(all(c("atlas_id", "citation", "doi") %in% names(cite)))
  expect_equal(nrow(cite), 1)
})
