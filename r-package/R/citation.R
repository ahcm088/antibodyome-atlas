#' Get the citation for a dataset, ready to paste into a manuscript
#'
#' @inheritParams aab_dataset
#' @return A one-row [tibble::tibble()] with columns `atlas_id`,
#'   `dataset_link`, `citation`, `doi`, `pubmed_link`, `publisher_link`. Any
#'   publication field is `NA` if the record has no associated publication.
#' @examples
#' \dontrun{
#' aab_citation("AAB-000004")
#' }
#' @export
aab_citation <- function(atlas_id, ref = "main") {
  record <- aab_dataset(atlas_id, ref = ref)
  pub <- record$publication
  tibble::tibble(
    atlas_id = record$atlas_id,
    dataset_link = record$dataset_link,
    citation = if (!is.null(pub) && nrow(pub) > 0) pub$citation[[1]] else NA_character_,
    doi = if (!is.null(pub) && nrow(pub) > 0) pub$doi[[1]] else NA_character_,
    pubmed_link = if (!is.null(pub) && nrow(pub) > 0) pub$pubmed_link[[1]] else NA_character_,
    publisher_link = if (!is.null(pub) && nrow(pub) > 0) pub$publisher_link[[1]] else NA_character_
  )
}
