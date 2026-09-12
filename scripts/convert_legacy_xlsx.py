"""One-time migration of data/AAb_Atlas_10Sep26.xlsx into schema/*.json format.

This is a bulk import of already-curated legacy data, not a run through the
seed -> LLM-enrichment pipeline. provenance.seed_id here is set to
"xlsx-row-<n>" (the original spreadsheet row) purely as a migration marker,
and provenance.enrichment_method is "manual" since the source rows were
already fully curated by hand.

Usage: python scripts/convert_legacy_xlsx.py
"""
import json
import re
from pathlib import Path

import openpyxl

from atlas_common import is_na, slugify, extract_doi, extract_pmid, make_publication_id

ROOT = Path(__file__).resolve().parent.parent
XLSX_PATH = ROOT / "data" / "AAb_Atlas_10Sep26.xlsx"
OUT_DIR = ROOT / "metadata"

HEADERS = [
    "data_type", "search", "GEO_ID", "Related to", "Acession number",
    "Dataset link", "Available data", "Title", "Summary", "Organism",
    "Sample tissue", "Conditions", "sample n by condition",
    "total sample n", "available metadata", "Ig type", "Platform",
    "Platform n proteins", "Country", "citation", "pubmed link",
    "publisher link", "extra",
]

# Maps the 29 distinct free-text values observed in "Available data" to
# (data_status, data_content tags, optional note). See schema/README.md.
AVAILABILITY_MAP = {
    "raw; normalized": ("available", ["raw", "normalized"], None),
    "raw; processed": ("available", ["raw", "processed"], None),
    "raw; median": ("available", ["raw", "median"], None),
    "raw": ("available", ["raw"], None),
    "raw; mean": ("available", ["raw", "mean"], None),
    "raw; processed; significant": ("available", ["raw", "processed", "significant"], None),
    "raw; normalized; significant": ("available", ["raw", "normalized", "significant"], None),
    "count": ("available", ["counts"], None),
    "raw; significant": ("available", ["raw", "significant"], None),
    "data not available": ("unavailable", [], None),
    "available upon request": ("upon_request", [], None),
    "significant": ("available", ["significant"], None),
    "quantile normalized, processed": ("available", ["normalized", "processed"], None),
    "data not available; publication not available": ("unavailable", [], "publication also not available"),
    "normalized": ("available", ["normalized"], None),
    "processed (z-score)": ("available", ["processed", "z_score"], None),
    "raw (z-score); significant": ("available", ["raw", "z_score", "significant"], None),
    "raw (ms); significant": ("available", ["raw", "significant"], "raw data is mass spectrometry (MS)"),
    "processed (z-score); significant": ("available", ["processed", "z_score", "significant"], None),
    "significant; ms counts": ("available", ["significant", "counts"], "counts are mass spectrometry (MS) counts"),
    "no": ("unavailable", [], None),
    "differential expression results": ("available", ["differential_expression"], None),
    "raw; counts": ("available", ["raw", "counts"], None),
    "na": ("unknown", [], None),
    "counts": ("available", ["counts"], None),
    "counts; differential expression results": ("available", ["counts", "differential_expression"], None),
}


def split_multi(v):
    if is_na(v):
        return []
    if isinstance(v, (int, float)):
        return [str(v)]
    return [p.strip() for p in str(v).split(";") if p.strip()]


def split_flexible(v, target_len):
    """Split on ';' (the sheet's convention), but fall back to ',' when that
    matches target_len and ';' doesn't — 23 rows in 'Conditions' and 3 in
    'Platform' were curated with commas instead of semicolons."""
    if is_na(v):
        return []
    by_semi = split_multi(v)
    if len(by_semi) == target_len:
        return by_semi
    by_comma = [p.strip() for p in str(v).split(",") if p.strip()]
    if len(by_comma) == target_len:
        return by_comma
    return by_semi


def parse_availability(raw, review_notes):
    if is_na(raw):
        return {"data_status": "unknown", "data_content": []}
    key = str(raw).strip().lower()
    mapped = AVAILABILITY_MAP.get(key)
    if mapped is None:
        review_notes.append(f"unmapped Available data value: {raw!r}")
        return {"data_status": "unknown", "data_content": [], "notes": f"unparsed source value: {raw}"}
    status, content, note = mapped
    out = {"data_status": status, "data_content": content}
    if note:
        out["notes"] = note
    return out


def parse_conditions(conditions_raw, n_raw, total_raw, review_notes):
    ns = split_multi(n_raw)
    conditions = split_flexible(conditions_raw, len(ns))
    note = None
    if conditions and len(conditions) == len(ns):
        parsed = []
        for name, n in zip(conditions, ns):
            try:
                parsed.append({"name": name, "n": int(n)})
            except ValueError:
                parsed.append({"name": name, "n": None})
        return parsed, None
    if conditions and not ns:
        return [{"name": name, "n": None} for name in conditions], None
    if conditions:
        note = f"could not align conditions ({conditions_raw!r}) with sample n by condition ({n_raw!r})"
        review_notes.append(note)
        return [{"name": name, "n": None} for name in conditions], note
    return [], None


def parse_total_sample_n(raw, review_notes):
    if is_na(raw):
        return None, None
    if isinstance(raw, (int, float)):
        return int(raw), None
    parts = split_multi(raw)
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            pass
    if len(parts) == 1 and nums:
        return nums[0], None
    if nums:
        note = f"total_sample_n reconstructed as sum of reported values (raw: {raw!r})"
        review_notes.append(note)
        return sum(nums), note
    review_notes.append(f"unparseable total sample n: {raw!r}")
    return None, None


def split_urls(raw):
    """A handful of rows curated more than one URL into a single link field,
    joined by ';' or even a literal newline. Splitting on both keeps the
    dataset_link picker from swallowing two URLs as one malformed string."""
    if is_na(raw):
        return []
    parts = [p.strip() for p in re.split(r"[;\n]+", str(raw)) if p.strip()]
    out = []
    for p in parts:
        if not re.match(r"^https?://", p, re.IGNORECASE):
            p = "https://" + p
        out.append(p)
    return out


def pick_dataset_link(row, review_notes):
    for field in ("Dataset link", "publisher link", "pubmed link"):
        urls = split_urls(row[field])
        if len(urls) > 1:
            review_notes.append(f"{field} had multiple URLs ({row[field]!r}); used the first: {urls[0]!r}")
        if urls:
            return urls[0]
    review_notes.append("no usable link found in Dataset link / publisher link / pubmed link")
    return None


def main():
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(min_row=2, values_only=True))

    publications = {}  # publication_id -> record
    platforms = {}  # platform_id -> record
    datasets = []
    all_review_notes = []  # (atlas_id, [notes])

    # First pass: index accessions -> atlas_id for related_atlas_ids resolution.
    accession_to_atlas_id = {}
    for i, row in enumerate(rows, start=1):
        d = dict(zip(HEADERS, row))
        atlas_id = f"AAB-{i:06d}"
        accs = split_multi(d["Acession number"])
        if not is_na(d["GEO_ID"]):
            accs.append(str(d["GEO_ID"]).strip())
        for acc in accs:
            accession_to_atlas_id[acc] = atlas_id

    for i, row in enumerate(rows, start=1):
        d = dict(zip(HEADERS, row))
        atlas_id = f"AAB-{i:06d}"
        review_notes = []

        record_type = "DATASET" if d["data_type"] == "DATASET" else "PAPER"

        # --- publication ---
        publication_id = None
        citation = d["citation"] if not is_na(d["citation"]) else None
        if citation:
            doi = extract_doi(citation)
            publication_id = make_publication_id(citation, doi=doi, pubmed_link=d["pubmed link"])
            if publication_id not in publications:
                publications[publication_id] = {
                    "publication_id": publication_id,
                    "citation": citation,
                    "doi": doi,
                    "pubmed_link": None if is_na(d["pubmed link"]) else str(d["pubmed link"]).strip(),
                    "publisher_link": None if is_na(d["publisher link"]) else str(d["publisher link"]).strip(),
                }

        # --- platforms ---
        # n_proteins_reported is per-dataset (see schema/README.md): the same
        # named platform reports different counts across studies, so it is
        # not stored as a fixed attribute of the shared platform entity.
        platform_n_raw = split_multi(d["Platform n proteins"])
        platform_names = split_flexible(d["Platform"], len(platform_n_raw))
        if platform_names and platform_n_raw and len(platform_names) != len(platform_n_raw):
            review_notes.append(
                f"could not align Platform ({d['Platform']!r}) with Platform n proteins ({d['Platform n proteins']!r})"
            )
            pairs = [(name, None) for name in platform_names]
        else:
            pairs = list(zip(platform_names, platform_n_raw)) if platform_names else []
            if not platform_n_raw:
                pairs = [(name, None) for name in platform_names]
        dataset_platforms = []
        for name, n in pairs:
            pid = slugify(name)
            n_int = None
            if n is not None:
                try:
                    n_int = int(n)
                except ValueError:
                    n_int = None
            dataset_platforms.append({"platform_id": pid, "n_proteins_reported": n_int})
            if pid not in platforms:
                platforms[pid] = {"platform_id": pid, "name": name, "technology": None}

        # --- conditions / sample sizes ---
        conditions, _ = parse_conditions(d["Conditions"], d["sample n by condition"], d["total sample n"], review_notes)
        total_sample_n, _ = parse_total_sample_n(d["total sample n"], review_notes)

        # --- availability ---
        curated_availability = parse_availability(d["Available data"], review_notes)

        # --- related atlas ids ---
        related_raw = split_multi(d["Related to"])
        related_atlas_ids = sorted({
            accession_to_atlas_id[acc] for acc in related_raw
            if acc in accession_to_atlas_id and accession_to_atlas_id[acc] != atlas_id
        })

        # --- dataset link ---
        dataset_link = pick_dataset_link(d, review_notes)

        record = {
            "atlas_id": atlas_id,
            "record_type": record_type,
            "title": (d["Title"] or "").strip(),
            "summary": None if is_na(d["Summary"]) else str(d["Summary"]),
            "organism": split_multi(d["Organism"]),
            "sample_tissue": split_multi(d["Sample tissue"]),
            "conditions": conditions,
            "total_sample_n": total_sample_n,
            "available_metadata": split_multi(d["available metadata"]),
            "ig_type": split_multi(d["Ig type"]),
            "platforms": dataset_platforms,
            "source_ids": {
                "geo_id": None if is_na(d["GEO_ID"]) else str(d["GEO_ID"]).strip(),
                "arrayexpress_id": None,
                "other_accessions": split_multi(d["Acession number"]),
            },
            "dataset_link": dataset_link,
            "related_atlas_ids": related_atlas_ids,
            "country": split_multi(d["Country"]),
            "publication_id": publication_id,
            "curated_availability": curated_availability,
            "provenance": {
                "seed_id": f"xlsx-row-{i + 1}",  # +1 to match the 1-indexed Excel row incl. header
                "search_batch": d["search"] or "unknown",
                "enrichment_method": "manual",
                "curated_at": "2026-09-10",
            },
        }
        datasets.append(record)
        if review_notes:
            all_review_notes.append((atlas_id, review_notes))

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "datasets.json").write_text(json.dumps(datasets, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "publications.json").write_text(
        json.dumps(sorted(publications.values(), key=lambda p: p["publication_id"]), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUT_DIR / "platforms.json").write_text(
        json.dumps(sorted(platforms.values(), key=lambda p: p["platform_id"]), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    # link_status.json is an append-only log maintained by check_links.py,
    # not by this migration script -- never overwrite real check history.
    link_status_path = OUT_DIR / "link_status.json"
    if not link_status_path.exists():
        link_status_path.write_text("[]\n", encoding="utf-8")

    report = {
        "total_rows": len(rows),
        "datasets_written": len(datasets),
        "publications_written": len(publications),
        "platforms_written": len(platforms),
        "rows_missing_dataset_link": sum(1 for r in datasets if r["dataset_link"] is None),
        "rows_with_review_notes": len(all_review_notes),
        "review_notes": all_review_notes,
    }
    (ROOT / "scripts" / "convert_legacy_xlsx.report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("done, see scripts/convert_legacy_xlsx.report.json")


if __name__ == "__main__":
    main()
