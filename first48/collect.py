"""Daily collection run.

For a run on day R (UTC):
- snapshot the pages that entered article space on R-2, just after their day 1 ended
- fetch day 0 and day 1 views for the R-3 cohort
- fetch day 0 to day 29 views for the R-32 cohort

Pageviews for a day are published the next day, so the view fetches lag the
snapshot by one extra day. Snapshots only reflect day-1 state when the run
happens on schedule; a late run records a later state.

Each file written is printed on its own line so the caller can upload it.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from first48.wiki import (
    fetch_daily_views,
    fetch_instance_of,
    fetch_new_articles,
    make_session,
    snapshot_pages,
)

SNAPSHOT_LAG = 2
EARLY_LAG = 3
FULL_LAG = 32


def now_utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_jsonl(path, rows):
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(path, flush=True)


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def take_snapshot(cohort, out, session):
    new_pages = fetch_new_articles(cohort, session)
    fetched_at = now_utc()
    for page in new_pages:
        page["fetched_at"] = fetched_at
    write_jsonl(out / f"new_pages_{cohort}.jsonl", new_pages)

    states = snapshot_pages([p["page_id"] for p in new_pages], session)
    items = [s["wikidata_item"] for s in states if s["wikidata_item"]]
    types = fetch_instance_of(items, session)
    for state in states:
        state["instance_of"] = types.get(state["wikidata_item"], [])
    write_jsonl(out / f"snapshot_{cohort}.jsonl", states)


def is_article(state):
    # Pages moved back to draft after promotion still exist but are no
    # longer articles.
    return state["exists"] and state["namespace"] == 0 and not state["is_redirect"]


def fetch_views(cohort, n_days, kind, out, session):
    snapshot = out / f"snapshot_{cohort}.jsonl"
    if not snapshot.exists():
        print(f"no snapshot for {cohort}, skipping {kind} views", file=sys.stderr)
        return

    articles = [s for s in read_jsonl(snapshot) if is_article(s)]
    end = cohort + dt.timedelta(days=n_days - 1)
    rows = []
    for article in articles:
        views = fetch_daily_views(article["title"], cohort, end, session)
        rows.append({
            "page_id": article["page_id"],
            "title": article["title"],
            "fetched_at": now_utc(),
            "views": views,
        })
    write_jsonl(out / f"views_{kind}_{cohort}.jsonl", rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    parser.add_argument("--date", type=dt.date.fromisoformat,
                        default=dt.datetime.now(dt.timezone.utc).date(),
                        help="run date in UTC, defaults to today")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    session = make_session()
    run = args.date
    take_snapshot(run - dt.timedelta(days=SNAPSHOT_LAG), args.out, session)
    fetch_views(run - dt.timedelta(days=EARLY_LAG), 2, "early", args.out, session)
    fetch_views(run - dt.timedelta(days=FULL_LAG), 30, "full", args.out, session)


if __name__ == "__main__":
    main()
