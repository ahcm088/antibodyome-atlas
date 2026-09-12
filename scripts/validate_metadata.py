"""Validates metadata/*.json against schema/*.schema.json.

Usage: python scripts/validate_metadata.py
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent

PAIRS = [
    ("datasets.json", "dataset.schema.json"),
    ("publications.json", "publication.schema.json"),
    ("platforms.json", "platform.schema.json"),
    ("link_status.json", "link_status.schema.json"),
    ("seeds.json", "seed.schema.json"),
]


def check_references(datasets, publications, platforms):
    pub_ids = {p["publication_id"] for p in publications}
    plat_ids = {p["platform_id"] for p in platforms}
    atlas_ids = {d["atlas_id"] for d in datasets}
    errors = []
    for d in datasets:
        aid = d["atlas_id"]
        if d.get("publication_id") and d["publication_id"] not in pub_ids:
            errors.append(f"[{aid}] publication_id {d['publication_id']!r} not found in publications.json")
        for p in d.get("platforms", []):
            if p["platform_id"] not in plat_ids:
                errors.append(f"[{aid}] platforms references {p['platform_id']!r} not found in platforms.json")
        for rel in d.get("related_atlas_ids", []):
            if rel not in atlas_ids:
                errors.append(f"[{aid}] related_atlas_ids references unknown atlas_id {rel!r}")
    return errors


def main():
    total_errors = 0
    loaded = {}
    for data_file, schema_file in PAIRS:
        schema = json.loads((ROOT / "schema" / schema_file).read_text(encoding="utf-8"))
        data = json.loads((ROOT / "metadata" / data_file).read_text(encoding="utf-8"))
        loaded[data_file] = data
        validator = Draft202012Validator(schema)
        errors = []
        for i, item in enumerate(data):
            for err in validator.iter_errors(item):
                errors.append(f"[{data_file}#{i}] {err.json_path}: {err.message}")
        print(f"{data_file}: {len(data)} records, {len(errors)} errors")
        for e in errors[:20]:
            print("  " + e)
        total_errors += len(errors)

    ref_errors = check_references(loaded["datasets.json"], loaded["publications.json"], loaded["platforms.json"])
    print(f"\nreferential integrity: {len(ref_errors)} errors")
    for e in ref_errors[:20]:
        print("  " + e)
    total_errors += len(ref_errors)

    print(f"\nTOTAL ERRORS: {total_errors}")
    raise SystemExit(1 if total_errors else 0)


if __name__ == "__main__":
    main()
