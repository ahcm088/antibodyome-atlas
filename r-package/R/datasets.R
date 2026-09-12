#' List all datasets/papers in the atlas
#'
#' @inheritParams aab_raw_url
#' @return A [tibble::tibble()], one row per record, with columns matching
#'   `schema/dataset.schema.json` (`atlas_id`, `record_type`, `title`,
#'   `organism`, `conditions`, `total_sample_n`, `platforms`, `dataset_link`,
#'   `curated_availability`, etc.). List-valued fields come back as
#'   list-columns.
#' @examples
#' \dontrun{
#' ds <- aab_datasets()
#' ds[ds$record_type == "DATASET", c("atlas_id", "title")]
#' }
#' @export
aab_datasets <- function(ref = "main") {
  aab_fetch("datasets", ref = ref)
}

#' List all publications referenced by atlas datasets
#'
#' @inheritParams aab_raw_url
#' @return A [tibble::tibble()] with columns `publication_id`, `citation`,
#'   `doi`, `pubmed_link`, `publisher_link`.
#' @export
aab_publications <- function(ref = "main") {
  aab_fetch("publications", ref = ref)
}

#' List all assay platforms referenced by atlas datasets
#'
#' @inheritParams aab_raw_url
#' @return A [tibble::tibble()] with columns `platform_id`, `name`,
#'   `technology`. Per-study protein/feature counts live on
#'   the dataset record (`aab_datasets()$platforms`), not here — see
#'   `schema/README.md` in the atlas repo for why.
#' @export
aab_platforms <- function(ref = "main") {
  aab_fetch("platforms", ref = ref)
}

#' List the link-reachability check history
#'
#' @inheritParams aab_raw_url
#' @return A [tibble::tibble()] with one row per automated check, appended
#'   over time by the atlas's scheduled link checker — see
#'   `checked_at`/`reachable` to see whether a given dataset's link has gone
#'   stale.
#' @export
aab_link_status <- function(ref = "main") {
  aab_fetch("link_status", ref = ref)
}

#' Get a single dataset record, with its publication and platforms resolved
#'
#' @param atlas_id An atlas id, e.g. `"AAB-000004"`.
#' @inheritParams aab_raw_url
#' @return A list with the dataset's fields plus two resolved fields:
#'   `publication` (a one-row tibble, or `NULL` if none) and
#'   `platforms_detail` (a tibble joining `platforms[].platform_id` from the
#'   dataset onto `aab_platforms()`, keeping `n_proteins_reported`).
#' @examples
#' \dontrun{
#' aab_dataset("AAB-000004")
#' }
#' @export
aab_dataset <- function(atlas_id, ref = "main") {
  datasets <- aab_datasets(ref = ref)
  row <- datasets[datasets$atlas_id == atlas_id, ]
  if (nrow(row) == 0) {
    stop("No dataset found with atlas_id: ", atlas_id, call. = FALSE)
  }
  record <- as.list(row[1, ])

  if (!is.null(record$publication_id) && !is.na(record$publication_id)) {
    pubs <- aab_publications(ref = ref)
    record$publication <- pubs[pubs$publication_id == record$publication_id, ]
  } else {
    record$publication <- NULL
  }

  plats <- record$platforms[[1]]
  if (!is.null(plats) && nrow(plats) > 0) {
    all_platforms <- aab_platforms(ref = ref)
    record$platforms_detail <- merge(plats, all_platforms, by = "platform_id", all.x = TRUE)
  } else {
    record$platforms_detail <- NULL
  }

  record
}
