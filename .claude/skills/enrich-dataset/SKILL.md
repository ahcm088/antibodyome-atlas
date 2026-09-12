---
name: enrich-dataset
description: Research a seed entry from metadata/seeds.json (or a dataset/paper link given directly) and turn it into a validated antibodyome-atlas record, merged via scripts/add_candidate.py after human confirmation. Use when the user asks to enrich, add, or curate a new dataset/paper into the atlas.
---

# Enrich a dataset into the atlas

Turns one minimal seed entry into a full record conforming to
`schema/dataset.schema.json`, then merges it safely. This is a
human-in-the-loop step, not a fully automated pipeline: LLM research can get
citations, sample counts, or accessions wrong, so nothing gets merged without
the curator seeing the candidate first. See `schema/README.md` for the data
model this produces.

## Input

Either:
- a `seed_id` to look up in `metadata/seeds.json` (added there via
  `metadata/seeds_template.csv` + `scripts/seeds_csv_to_json.py`), or
- an identifier/link given directly by the user in chat, if they haven't
  gone through the seed CSV step.

## Steps

1. **Resolve identity.** Follow the link / look up the identifier (GEO,
   ArrayExpress, HuProt DB, a DOI/PMID, etc.) and confirm what it actually
   is before extracting anything.

2. **Research the fields**, per `schema/dataset.schema.json`:
   - `title`, `summary`, `organism`, `sample_tissue`, `ig_type`, `country`,
     `available_metadata` — as reported by the source.
   - `conditions`: array of `{name, n}`. Only pair a name with a count you
     can actually justify from the source — if group labels and per-group
     counts can't be reconciled (multi-cohort papers are common here), set
     `n: null` for the affected entries and say why in
     `curated_availability.notes`. Do not guess a plausible-looking split.
   - `total_sample_n`: a single integer. If the source reports it per-cohort
     instead of overall, sum only if that's an honest reconstruction, and
     note it.
   - `platforms`: array of `{platform_id, n_proteins_reported}`.
     `n_proteins_reported` is what THIS study reports (post-QC, subset
     analyzed, etc.) — it varies paper to paper even for the same named
     platform, so never look up "the" spec of a platform and reuse it.
     Check `metadata/platforms.json` for an existing `platform_id` matching
     the platform name (same slugification as `scripts/atlas_common.slugify`)
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

4. **Assemble the candidate file** in the shape `scripts/add_candidate.py`
   expects:
   ```json
   {
     "dataset": { "atlas_id": "AUTO", ...all dataset.schema.json fields..., "provenance": { "seed_id": "<the seed_id used>", "search_batch": "<...>", "enrichment_method": "llm_assisted", "curated_at": "<today, YYYY-MM-DD>" } },
     "new_publication": { ...only if not already in publications.json... },
     "new_platforms": [ ...only entries not already in platforms.json... ]
   }
   ```

5. **Dry-run it**: `python scripts/add_candidate.py <candidate.json> --dry-run`.
   Fix any schema/referential errors it reports.

6. **Show the curator the candidate record** (especially `conditions`,
   `total_sample_n`, `curated_availability`, and the publication/platform
   match) and ask for confirmation before merging.

7. **Merge** only after confirmation:
   `python scripts/add_candidate.py <candidate.json>` (no `--dry-run`).
   Report the assigned `atlas_id` back to the user.
