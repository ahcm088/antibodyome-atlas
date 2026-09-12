skip_if_atlas_unreachable <- function() {
  ok <- tryCatch(
    {
      resp <- httr2::req_perform(httr2::request(aab_raw_url("datasets")))
      httr2::resp_status(resp) == 200
    },
    error = function(e) FALSE
  )
  if (!ok) {
    testthat::skip("metadata/datasets.json not reachable at ref 'main' (repo not pushed yet, or offline)")
  }
}
