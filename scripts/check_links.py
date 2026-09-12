"""Checks reachability of every dataset_link in metadata/datasets.json and
appends one entry per dataset to metadata/link_status.json. Entries are
appended, never overwritten or deduplicated away — see
schema/link_status.schema.json for why the history is the point.

Meant to run on a schedule via .github/workflows/check_links.yml, but safe
to run locally too.

Usage: python scripts/check_links.py
"""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 15
MAX_WORKERS = 8
USER_AGENT = "antibodyome-atlas-link-checker/1.0 (+https://github.com/)"


def check_one(atlas_id, url):
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.head(url, timeout=TIMEOUT, allow_redirects=True, headers=headers)
        # Some hosts (e.g. certain journal publishers) don't support HEAD.
        if resp.status_code in (403, 405) or resp.status_code >= 500:
            resp = requests.get(url, timeout=TIMEOUT, allow_redirects=True, headers=headers, stream=True)
        return {
            "atlas_id": atlas_id,
            "checked_at": checked_at,
            "url_checked": url,
            "http_status": resp.status_code,
            "reachable": resp.status_code < 400,
            "likely_bot_blocked": resp.status_code in (403, 429),
            "notes": None,
            "checked_by": "github_action",
        }
    except requests.RequestException as e:
        return {
            "atlas_id": atlas_id,
            "checked_at": checked_at,
            "url_checked": url,
            "http_status": None,
            "reachable": False,
            "likely_bot_blocked": False,
            "notes": str(e)[:300],
            "checked_by": "github_action",
        }


def main():
    datasets = json.loads((ROOT / "metadata" / "datasets.json").read_text(encoding="utf-8"))
    targets = [(d["atlas_id"], d["dataset_link"]) for d in datasets if d.get("dataset_link")]

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(check_one, aid, url): aid for aid, url in targets}
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda r: r["atlas_id"])

    log_path = ROOT / "metadata" / "link_status.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    log.extend(results)
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")

    unreachable = [r for r in results if not r["reachable"]]
    blocked = [r for r in unreachable if r["likely_bot_blocked"]]
    truly_unreachable = [r for r in unreachable if not r["likely_bot_blocked"]]

    print(
        f"checked {len(results)} links: {len(unreachable)} unreachable "
        f"({len(blocked)} likely bot-blocked (403/429), {len(truly_unreachable)} worth investigating)"
    )
    for r in truly_unreachable:
        print(f"  UNREACHABLE {r['atlas_id']}: {r['url_checked']} (status={r['http_status']}, notes={r['notes']})")
    for r in blocked:
        print(f"  blocked (likely bot defense) {r['atlas_id']}: {r['url_checked']} (status={r['http_status']})")


if __name__ == "__main__":
    main()
