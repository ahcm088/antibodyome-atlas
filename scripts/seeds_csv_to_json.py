"""Converts a curator-filled seed CSV (see metadata/seeds_template.csv) into
seed.schema.json entries and merges them into metadata/seeds.json. New
seed_ids are appended; a seed_id that already exists is skipped (edit
metadata/seeds.json directly to change an existing seed).

Usage: python scripts/seeds_csv_to_json.py path/to/filled_seeds.csv
"""
import csv
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SEEDS_JSON = ROOT / "metadata" / "seeds.json"
SEED_SCHEMA = ROOT / "schema" / "seed.schema.json"


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/seeds_csv_to_json.py path/to/filled_seeds.csv")
        raise SystemExit(2)
    csv_path = Path(sys.argv[1])

    existing = json.loads(SEEDS_JSON.read_text(encoding="utf-8")) if SEEDS_JSON.exists() else []
    existing_ids = {s["seed_id"] for s in existing}
    schema = json.loads(SEED_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    added, skipped, rejected = [], [], []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            entry = {k: v.strip() for k, v in row.items() if v and v.strip()}
            if not entry.get("seed_id"):
                continue
            if entry["seed_id"] in existing_ids:
                skipped.append(entry["seed_id"])
                continue
            errors = list(validator.iter_errors(entry))
            if errors:
                rejected.append((entry["seed_id"], [e.message for e in errors]))
                continue
            existing.append(entry)
            existing_ids.add(entry["seed_id"])
            added.append(entry["seed_id"])

    SEEDS_JSON.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"added: {added}")
    print(f"skipped (already exist): {skipped}")
    if rejected:
        print("rejected (invalid, not added):")
        for seed_id, errs in rejected:
            print(f"  {seed_id}: {errs}")


if __name__ == "__main__":
    main()
