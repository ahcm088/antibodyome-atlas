"""Shared helpers for id generation and value normalization, used by
convert_legacy_xlsx.py, add_candidate.py, and seeds_csv_to_json.py."""
import re

ROOT_ATLAS_PREFIX = "AAB-"


def is_na(v):
    if v is None:
        return True
    if isinstance(v, str) and v.strip().upper() in ("", "NA"):
        return True
    return False


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def extract_doi(citation):
    if not citation:
        return None
    m = re.search(r"https?://doi\.org/(\S+?)[.,]?$", citation.strip())
    return m.group(1) if m else None


def extract_pmid(pubmed_link):
    if is_na(pubmed_link):
        return None
    m = re.search(r"/(\d+)/?$", pubmed_link.strip())
    return m.group(1) if m else None


def make_publication_id(citation, doi=None, pubmed_link=None):
    """Same derivation rule used across the codebase: prefer DOI, then PMID,
    then a slug of the citation text — so independently-run enrichment always
    lands on the same publication_id as an existing record for the same paper."""
    doi = doi or extract_doi(citation)
    pmid = extract_pmid(pubmed_link)
    if doi:
        return f"doi-{slugify(doi)}"
    if pmid:
        return f"pmid-{pmid}"
    return f"cite-{slugify(citation[:60])}"


def make_platform_id(name):
    return slugify(name)


def next_atlas_id(existing_datasets):
    max_n = 0
    for d in existing_datasets:
        m = re.match(rf"^{ROOT_ATLAS_PREFIX}(\d{{6}})$", d["atlas_id"])
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"{ROOT_ATLAS_PREFIX}{max_n + 1:06d}"
