---
name: enrich-dataset
description: Research a seed entry or dataset/paper link and prepare a validated antibodyome-atlas candidate with Codex. Use when adding or curating a new dataset or paper into the atlas; merge through scripts/add_candidate.py after curator review.
---

# Enrich a dataset into the atlas

Turns one minimal seed entry into a full record conforming to
`schema/dataset.schema.json`, then merges it safely. This is a
human-in-the-loop step, not a fully automated pipeline: LLM research can get
citations, sample counts, or accessions wrong, so nothing gets merged without
the curator seeing the candidate first. See `schema/README.md` for the data
model this produces.

## Codex setup

Run commands from the repository root. Read `schema/README.md` and the
relevant schemas in `schema/` before building the candidate. The existing
Python helpers require `python -m pip install -r requirements.txt`.

Use the web search and page-reading tools available in the Codex session
to inspect primary repository records, publications, and supplementary
files. Cite the URLs supporting the extracted fields in the review. If
web access or a source is unavailable, report the limitation and use only
verified material supplied by the curator; do not fill gaps from memory.

## Input

Either:
- a `seed_id` to look up in `metadata/seeds.json` (added there via
  `metadata/seeds_template.csv` + `scripts/seeds_csv_to_json.py`), or
- an identifier/link given directly by the user in chat, if they haven't
  gone through the seed CSV step.

For an existing seed, preserve its `seed_id` and `search_batch`; if a
`seed_id` occurs in multiple batches, resolve which batch the user means.
For a direct link, use a reproducible `seed_id` such as
`direct-<slugified-verified-identifier>` and `search_batch: "direct-input"`
unless the curator supplies another label. Explain this origin in the
review rather than implying that the seed exists in `metadata/seeds.json`.

## Steps

1. **Resolve identity.** Follow the link / look up the identifier (GEO,
   ArrayExpress, HuProt DB, a DOI/PMID, etc.) and confirm what it actually
   is before extracting anything. Check existing datasets by accession,
   dataset link, and associated publication to avoid adding the same
   record twice; distinct datasets can legitimately share a publication.

2. **Research the fields**, per `schema/dataset.schema.json`:
   - `title`, `summary`, `organism`, `sample_tissue`, `ig_type`, `country`,
     `available_metadata` — as reported by the source.
   - `conditions`: array of `{name, n}`. Only pair a name with a count you
     can actually justify from the source — if group labels and per-group
     counts can't be reconciled (multi-cohort papers are common here), set
     `n: null` for the affected entries and say why in
     `curated_availability.notes`. Do not guess a plausible-looking split.
   - `total_sample_n`: an integer, or `null` if unconfirmed. If the source reports it per-cohort
     instead of overall, sum only if that's an honest reconstruction, and
     note it.
   - `platforms`: array of `{platform_id, n_proteins_reported}`.
     `n_proteins_reported` is what THIS study reports (post-QC, subset
     analyzed, etc.) — it varies paper to paper even for the same named
     platform, so never look up "the" spec of a platform and reuse it.
     Check `metadata/platforms.json` for an existing `platform_id` matching
     the platform name (use `scripts/atlas_common.make_platform_id`)
     before treating it as new.
   - `source_ids`: `geo_id` / `arrayexpress_id` / `other_accessions` as
     applicable.
   - `dataset_link`: prefer the actual data/dataset landing page; fall back
     to the publisher link, then the PubMed link, only if no dataset page
     exists (this matches `record_type: PAPER` entries with no independent
     accession).
   - `curated_availability`: `data_status` (`available` / `upon_request` /
     `unavailable` / `unknown`) plus `data_content` tags from the controlled
     vocabulary in `schema/dataset.schema.json`
     (raw/processed/normalized/median/mean/significant/counts/
     differential_expression/z_score) — verify data is actually obtainable,
     don't infer availability from a paper claiming it "will be deposited".
   - Publication: full `citation`, `doi`, `pubmed_link`, `publisher_link`.
     Check `metadata/publications.json` for an existing match (by DOI, PMID,
     or citation) before treating it as new — use the same id scheme as
     `scripts/atlas_common.make_publication_id` so ids stay consistent.
   - `related_atlas_ids`: search `metadata/datasets.json` `source_ids` for
     accessions this record references (e.g. superseries/subseries) and use
     their `atlas_id`. Only include a match you're confident about.

3. **Never fabricate.** If a field can't be confirmed, leave it `null` /
   empty / `unknown` and say why in `curated_availability.notes` rather than
   producing a plausible-sounding value — this data ends up cited in
   publications.

4. **Assemble the candidate file** as UTF-8 JSON at a curator-specified
   path or `data/candidates/<seed_id>.json` (create the directory if needed;
   `data/` is git-ignored). Use the shape `scripts/add_candidate.py`
   expects; the following is schematic, not literal JSON:
   ```json
   {
     "dataset": { "atlas_id": "AUTO", ...all dataset.schema.json fields..., "provenance": { "seed_id": "<the seed_id used>", "search_batch": "<...>", "enrichment_method": "llm_assisted", "curated_at": "<today, YYYY-MM-DD>" } },
     "new_publication": { ...only if not already in publications.json... },
     "new_platforms": [ ...only entries not already in platforms.json... ]
   }
   ```

   Set `record_type` to `DATASET` or `PAPER` based on the verified source.
   Include all dataset fields with schema-compatible empty values where
   appropriate. Omit `new_publication` and `new_platforms` when not needed.
   For new publications/platforms, generate their IDs with the helpers in
   `scripts/atlas_common.py` and use those same IDs in dataset references;
   the merge script does not fill in those references for you.

5. **Dry-run it**: `python scripts/add_candidate.py <candidate.json> --dry-run`.
   Fix any schema/referential errors it reports.

6. **Show the curator the candidate record** (especially `conditions`,
   `total_sample_n`, `curated_availability`, and the publication/platform
   match), its file path, supporting source URLs, uncertainties, and the
   dry-run result. Obtain confirmation of this candidate before merging;
   honor confirmation already given for that same candidate.

7. **Merge** only after confirmation:
   `python scripts/add_candidate.py <candidate.json>` (no `--dry-run`).
   Then run `python scripts/validate_metadata.py` and inspect the metadata
   diff. Report the assigned `atlas_id` and validation result back to the
   user. Leave committing and publishing to the user's requested scope.
