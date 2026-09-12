# Atlas schema

Five entities, each a JSON Schema (draft 2020-12) file in this folder:

- **seed** — minimal fields a human curator fills in by hand (an id, source type, a search batch label, and an identifier or link). This is the input to LLM-assisted enrichment, not a finished atlas record.
- **dataset** — the canonical enriched record (one per dataset or paper). Produced from a seed entry by research (LLM-assisted or manual), then validated against this schema before merge.
- **publication** — a paper, normalized out of `dataset` so the same citation isn't repeated across every dataset row that cites it.
- **platform** — an assay platform (protein/antigen array), normalized out of `dataset` for the same reason.
- **link_status** — one append-only log entry per automated reachability check of a dataset's link. Never overwritten, so availability history over time lives directly in git.

## Design decisions worth knowing

- **`atlas_id` is separate from external accessions.** GEO IDs, DOIs, etc. are recorded under `source_ids` / `publication.doi`, but the atlas's own id (`AAB-000123`) is what's stable and what `related_atlas_ids` and `publication_id` reference. External accessions can be missing, wrong, or shared across sub-series; the atlas id never changes once assigned.
- **`conditions` is an array of `{name, n}` objects, not two semicolon-joined strings.** The source spreadsheet stored condition names and sample counts as parallel `;`-separated strings (e.g. `"RA; healthy control"` / `"279;280"`). That's fragile — nothing enforces the two stay aligned, and in at least one source row the counts didn't cleanly add up to the stated total (multi-cohort papers). Pairing them explicitly removes that failure mode.
- **`curated_availability` and `link_status` are deliberately separate.** `curated_availability` is what a curator/LLM determined *when the record was written* (does this data exist at all, in what form). `link_status` is what an automated job observes *now* (is the URL still reachable). Conflating them would silently overwrite curation judgment with a bot's HTTP status, and lose history of when something went offline.
- **Controlled vocabulary for `data_status` / `data_content`** replaces the 29 distinct free-text values found in the source spreadsheet's `Available data` column (e.g. `"raw; normalized"`, `"Available upon request"`, `"processed (Z-score); significant"`). `data_status` answers "can I get data beyond metadata, and how", `data_content` (only meaningful when `data_status: available`) tags its form.
- **`platforms[].platform_id` and `publication_id` are references, not embedded objects**, so editing a citation is a one-line diff in `publications.json` instead of a repeated edit across every dataset that cites it.
- **Protein/feature count lives on `dataset.platforms[].n_proteins_reported`, not on the shared `platform` entity.** Converting the legacy spreadsheet surfaced ~65 cases where the same named platform (e.g. "HuProt Human Proteome Microarray") reported a different protein count per paper (17000 to 23059 for nominally the same array) — it reflects what that study analyzed/QC'd, not a fixed spec of the platform. Storing it per-dataset avoids fabricating a single "correct" number.
- **Everything nullable is explicit** (`["string", "null"]` etc.) rather than just omitting the property, so a JSON Schema validator can still catch typos in optional field names (`additionalProperties: false` throughout).

## Not yet decided

- Where `datasets.json` / `publications.json` / `platforms.json` / `link_status.json` actually live in the repo, and the id-assignment/slugging rules for `atlas_id` and `platform_id`/`publication_id`.
- The conversion script from the existing `data/AAb_Atlas_10Sep26.xlsx` into this schema (next step).
- The enrichment prompt/checklist an LLM follows to go from a `seed` entry to a validated `dataset` record.
