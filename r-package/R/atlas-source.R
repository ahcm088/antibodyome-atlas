#' Base URL for the atlas's GitHub-hosted metadata
#'
#' @param ref Git ref (branch, tag, or commit SHA) to read from. Defaults to
#'   `"main"` (the latest curated data). Pin to a release tag (e.g.
#'   `"v1.0.0"`) for reproducible results in a publication.
#' @param file One of `"datasets"`, `"publications"`, `"platforms"`,
#'   `"link_status"`.
#' @return A single URL string.
#' @keywords internal
aab_raw_url <- function(file, ref = "main") {
  file <- match.arg(file, c("datasets", "publications", "platforms", "link_status"))
  sprintf(
    "https://raw.githubusercontent.com/ahcm088/antibodyome-atlas/%s/metadata/%s.json",
    ref, file
  )
}

#' Fetch and parse one of the atlas's JSON manifests
#'
#' @inheritParams aab_raw_url
#' @return A [tibble::tibble()], one row per record. Nested fields (e.g.
#'   `conditions`, `platforms`, `source_ids`) come back as list-columns.
#' @keywords internal
aab_fetch <- function(file, ref = "main") {
  url <- aab_raw_url(file, ref = ref)
  resp <- httr2::req_perform(httr2::request(url))
  httr2::resp_check_status(resp)
  parsed <- jsonlite::fromJSON(httr2::resp_body_string(resp), simplifyDataFrame = TRUE, flatten = FALSE)
  if (length(parsed) == 0) {
    return(tibble::tibble())
  }
  tibble::as_tibble(parsed)
}
