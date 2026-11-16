#!/usr/bin/env python3
"""Archive every source URL in the Under Our Boots dataset with the Wayback Machine.

Reads the ``sources`` column of the dataset CSV, deduplicates the http(s) URLs,
checks the Wayback availability API for an existing snapshot, and submits a
Save Page Now request for URLs that have none.

The run is resumable: results are appended (and flushed) one row at a time to
``data/source_snapshots.csv``, and URLs already present in that file are
skipped on later runs.

Per-run limits, by design:
  * at most 120 Wayback save submissions (availability checks are uncapped);
  * ~2 seconds of pacing between save submissions;
  * a save that returns HTTP 429 is retried once; a second 429 stops all
    further submissions for the run (remaining URLs are still checked and
    recorded).

Usage:
  python3 tools/archive_sources.py [--dataset PATH] [--output PATH]
                                   [--max-saves 120] [--pace 2.0]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATASET = os.path.expanduser(
    "~/workspace/research_notes/military-bases-indigenous-sites/installations.csv"
)
DEFAULT_OUTPUT = os.path.join(ROOT, "data", "source_snapshots.csv")

AVAILABILITY_API = "https://archive.org/wayback/available?url="
SAVE_BASE = "https://web.archive.org/save/"
USER_AGENT = "UnderOurBootsSourceArchiver/1.0 (source preservation for a history series)"
URL_RE = re.compile(r"https?://[^\s;|<>\"']+")
FIELDNAMES = ["url", "installation_ids", "status", "snapshot_url", "checked_date"]


def clean_url(raw: str) -> str:
    """Trim punctuation that belongs to the surrounding text, not the URL."""
    url = raw.strip()
    while url and url[-1] in ".,]>":
        url = url[:-1]
    # A trailing ')' is prose punctuation unless the URL has balanced parens.
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    return url


def extract_urls(dataset_path: str) -> "dict[str, list[str]]":
    """Return {url: [installation_id, ...]} in first-appearance order."""
    found: dict[str, list[str]] = {}
    with open(dataset_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            inst_id = (row.get("id") or "").strip()
            for match in URL_RE.findall(row.get("sources") or ""):
                url = clean_url(match)
                if not url:
                    continue
                ids = found.setdefault(url, [])
                if inst_id and inst_id not in ids:
                    ids.append(inst_id)
    return found


def load_done(output_path: str) -> set[str]:
    if not os.path.exists(output_path):
        return set()
    with open(output_path, newline="", encoding="utf-8-sig") as f:
        return {(row.get("url") or "").strip() for row in csv.DictReader(f) if row.get("url")}


def http_get(url: str, timeout: float) -> tuple[int, str, str]:
    """Return (status, final_url, body_text). Raises HTTPError/URLError through."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, resp.geturl(), body


def check_available(url: str) -> str | None:
    """Return the closest snapshot URL, or None if there is no snapshot."""
    api = AVAILABILITY_API + urllib.parse.quote(url, safe="")
    _, _, body = http_get(api, timeout=30)
    data = json.loads(body)
    closest = (data.get("archived_snapshots") or {}).get("closest") or {}
    if closest.get("available") and closest.get("url"):
        return closest["url"]
    return None


def save_url(url: str) -> str:
    quoted = urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%-._~")
    return SAVE_BASE + quoted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--max-saves", type=int, default=120)
    parser.add_argument("--pace", type=float, default=2.0, help="seconds between save submissions")
    args = parser.parse_args()

    urls = extract_urls(args.dataset)
    done = load_done(args.output)
    todo = [(u, ids) for u, ids in urls.items() if u not in done]
    checked_date = datetime.now(ZoneInfo("America/Denver")).date().isoformat()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    need_header = not os.path.exists(args.output) or os.path.getsize(args.output) == 0

    counts = {"existing": 0, "submitted": 0, "failed": 0, "no-snapshot": 0}
    save_submissions = 0
    stop_submitting = False

    print(f"dataset URLs: {len(urls)} unique; already recorded: {len(done)}; "
          f"to check this run: {len(todo)}", flush=True)

    with open(args.output, "a", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
        if need_header:
            writer.writeheader()
            out.flush()

        for i, (url, ids) in enumerate(todo, 1):
            status, snapshot_url = "failed", ""
            try:
                snapshot = check_available(url)
            except Exception as exc:  # availability API error / bad JSON
                print(f"[{i}/{len(todo)}] availability error for {url}: {exc}", flush=True)
                snapshot = None
                status = "failed"
            else:
                if snapshot:
                    status, snapshot_url = "existing", snapshot
                elif stop_submitting or save_submissions >= args.max_saves:
                    status = "no-snapshot"
                else:
                    # Submit a Save Page Now request; retry once on HTTP 429.
                    attempts = 0
                    while True:
                        if save_submissions >= args.max_saves:
                            status = "no-snapshot"
                            break
                        if save_submissions > 0:
                            time.sleep(5.0 if attempts else args.pace)
                        save_submissions += 1
                        attempts += 1
                        try:
                            code, final_url, _ = http_get(save_url(url), timeout=120)
                            if code and 200 <= code < 400:
                                status = "submitted"
                                if re.search(r"/web/\d{4,}", final_url):
                                    snapshot_url = final_url
                            else:
                                status = "failed"
                            break
                        except urllib.error.HTTPError as exc:
                            if exc.code == 429 and attempts == 1 and save_submissions < args.max_saves:
                                print(f"[{i}/{len(todo)}] 429 on save, retrying once: {url}",
                                      flush=True)
                                continue
                            if exc.code == 429:
                                print(f"[{i}/{len(todo)}] 429 on save retry; "
                                      f"stopping submissions for this run: {url}", flush=True)
                                stop_submitting = True
                            status = "failed"
                            break
                        except Exception as exc:
                            print(f"[{i}/{len(todo)}] save error for {url}: {exc}", flush=True)
                            status = "failed"
                            break

            counts[status] = counts.get(status, 0) + 1
            writer.writerow({
                "url": url,
                "installation_ids": ";".join(ids),
                "status": status,
                "snapshot_url": snapshot_url,
                "checked_date": checked_date,
            })
            out.flush()
            if i % 25 == 0 or i == len(todo):
                print(f"[{i}/{len(todo)}] counts={counts} saves={save_submissions}", flush=True)

    total_rows = 0
    if os.path.exists(args.output):
        with open(args.output, newline="", encoding="utf-8-sig") as f:
            total_rows = sum(1 for _ in csv.DictReader(f))

    print(json.dumps({
        "unique_urls_in_dataset": len(urls),
        "skipped_already_recorded": len(done),
        "checked_this_run": len(todo),
        "existing_snapshots": counts["existing"],
        "submitted": counts["submitted"],
        "failed": counts["failed"],
        "no_snapshot_recorded": counts["no-snapshot"],
        "save_submissions": save_submissions,
        "output_rows_total": total_rows,
        "output": args.output,
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
