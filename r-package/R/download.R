#' Download a dataset's data file
#'
#' Downloads whatever is at the record's `dataset_link`. For records with
#' `record_type == "DATASET"` this is usually a repository landing page (e.g.
#' a GEO accession page) rather than a direct file: check
#' `curated_availability` first, and note that some repositories require
#' navigating from that page to the actual supplementary files by hand.
#'
#' @inheritParams aab_dataset
#' @param destdir Directory to save the file into. Defaults to a temp dir.
#' @param destfile File name to save as. Defaults to the last path segment
#'   of `dataset_link`.
#' @return The local file path, invisibly.
#' @examples
#' \dontrun{
#' aab_download("AAB-000004")
#' }
#' @export
aab_download <- function(atlas_id, destdir = tempdir(), destfile = NULL, ref = "main") {
  record <- aab_dataset(atlas_id, ref = ref)

  status <- record$curated_availability[["data_status"]]
  if (!is.null(status) && status %in% c("unavailable", "upon_request")) {
    message(
      "curated_availability$data_status for ", atlas_id, " is '", status, "' -- ",
      "the data itself may not be directly downloadable. Proceeding to fetch dataset_link anyway."
    )
  }

  url <- record$dataset_link
  if (is.null(destfile)) {
    destfile <- basename(sub("\\?.*$", "", url))
    if (destfile == "" || destfile == "/") destfile <- paste0(atlas_id, ".html")
  }
  path <- file.path(destdir, destfile)

  resp <- httr2::req_perform(httr2::request(url), path = path)
  httr2::resp_check_status(resp)
  invisible(path)
}
