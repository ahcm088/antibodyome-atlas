"""Validates and merges one new dataset record (plus any new publication/
platform it introduces) into metadata/*.json. This is the only supported way
to add a record after enrichment — it never writes anything unless every
check below passes, so a bad LLM-produced record can't corrupt the atlas.

Candidate file shape (see schema/README.md for the enrichment pipeline this
feeds):
{
  "dataset": { ...dataset.schema.json fields, "atlas_id" may be omitted or "AUTO"... },
  "new_publication": { ...publication.schema.json fields, "publication_id" may be omitted... },
  "new_platforms": [ { ...platform.schema.json fields, "platform_id" may be omitted... } ]
}

Usage: python scripts/add_candidate.py path/to/candidate.json [--dry-run]
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from atlas_common import make_publication_id, make_platform_id, next_atlas_id

ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = ROOT / "metadata"
SCHEMA_DIR = ROOT / "schema"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/add_candidate.py path/to/candidate.json [--dry-run]")
        raise SystemExit(2)
    candidate_path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv[2:]

    candidate = load_json(candidate_path)
    dataset = candidate["dataset"]
    new_publication = candidate.get("new_publication")
    new_platforms = candidate.get("new_platforms", [])

    datasets = load_json(METADATA_DIR / "datasets.json")
    publications = load_json(METADATA_DIR / "publications.json")
    platforms = load_json(METADATA_DIR / "platforms.json")

    errors = []

    existing_atlas_ids = {d["atlas_id"] for d in datasets}
    if not dataset.get("atlas_id") or dataset["atlas_id"] == "AUTO":
        dataset["atlas_id"] = next_atlas_id(datasets)
    elif dataset["atlas_id"] in existing_atlas_ids:
        errors.append(f"atlas_id {dataset['atlas_id']} already exists in datasets.json")

    existing_publication_ids = {p["publication_id"] for p in publications}
    if new_publication:
        if not new_publication.get("publication_id"):
            new_publication["publication_id"] = make_publication_id(
                new_publication["citation"],
                doi=new_publication.get("doi"),
                pubmed_link=new_publication.get("pubmed_link"),
            )
        if new_publication["publication_id"] in existing_publication_ids:
            errors.append(
                f"new_publication.publication_id {new_publication['publication_id']!r} already exists — "
                "reference it via dataset.publication_id instead of resubmitting it as new_publication"
            )
        else:
            existing_publication_ids.add(new_publication["publication_id"])

    existing_platform_ids = {p["platform_id"] for p in platforms}
    for np in new_platforms:
        if not np.get("platform_id"):
            np["platform_id"] = make_platform_id(np["name"])
        if np["platform_id"] in existing_platform_ids:
            errors.append(
                f"new_platforms entry {np['platform_id']!r} already exists — "
                "reference it from dataset.platforms instead of resubmitting it as new_platforms"
            )
        else:
            existing_platform_ids.add(np["platform_id"])

    # Schema validation
    dataset_schema = load_json(SCHEMA_DIR / "dataset.schema.json")
    for err in Draft202012Validator(dataset_schema).iter_errors(dataset):
        errors.append(f"dataset schema: {err.json_path}: {err.message}")
    if new_publication:
        pub_schema = load_json(SCHEMA_DIR / "publication.schema.json")
        for err in Draft202012Validator(pub_schema).iter_errors(new_publication):
            errors.append(f"new_publication schema: {err.json_path}: {err.message}")
    if new_platforms:
        plat_schema = load_json(SCHEMA_DIR / "platform.schema.json")
        for np in new_platforms:
            for err in Draft202012Validator(plat_schema).iter_errors(np):
                errors.append(f"new_platforms schema ({np.get('platform_id')}): {err.json_path}: {err.message}")

    # Referential integrity
    if dataset.get("publication_id") and dataset["publication_id"] not in existing_publication_ids:
        errors.append(
            f"dataset.publication_id {dataset['publication_id']!r} does not exist in publications.json "
            "and was not supplied via new_publication"
        )
    for p in dataset.get("platforms", []):
        if p["platform_id"] not in existing_platform_ids:
            errors.append(
                f"dataset.platforms references platform_id {p['platform_id']!r} which does not exist "
                "in platforms.json and was not supplied via new_platforms"
            )
    for rel in dataset.get("related_atlas_ids", []):
        if rel not in existing_atlas_ids and rel != dataset["atlas_id"]:
            errors.append(f"dataset.related_atlas_ids references unknown atlas_id {rel!r}")

    if errors:
        print(f"REJECTED — {len(errors)} error(s), nothing was written:")
        for e in errors:
            print("  - " + e)
        raise SystemExit(1)

    print(f"OK — candidate valid, assigned atlas_id {dataset['atlas_id']}")
    if dry_run:
        print("(--dry-run: not writing)")
        return

    datasets.append(dataset)
    if new_publication:
        publications.append(new_publication)
        publications.sort(key=lambda p: p["publication_id"])
    for np in new_platforms:
        platforms.append(np)
    platforms.sort(key=lambda p: p["platform_id"])

    save_json(METADATA_DIR / "datasets.json", datasets)
    save_json(METADATA_DIR / "publications.json", publications)
    save_json(METADATA_DIR / "platforms.json", platforms)
    print(f"Merged into metadata/. New atlas_id: {dataset['atlas_id']}")


if __name__ == "__main__":
    main()
