"""Daily collection run.

For a run on day R (UTC):
- snapshot the pages that entered article space on R-2, just after their day 1 ended
- fetch day 0 and day 1 views for the R-3 cohort
- fetch day 0 to day 29 views for the R-32 cohort

Pageviews for a day are published the next day, so the view fetches lag the
snapshot by one extra day. Snapshots only reflect day-1 state when the run
happens on schedule; a late run records a later state.

Each file written is printed on its own line so the caller can upload it.
With --summary, one row per run is appended to a CSV file.
"""
import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from first48.checks import check_snapshot, check_views
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
    return len(rows)


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
    return new_pages, states


def is_article(state):
    # Pages moved back to draft after promotion still exist but are no
    # longer articles.
    return state["exists"] and state["namespace"] == 0 and not state["is_redirect"]


def fetch_views(cohort, n_days, kind, out, session):
    snapshot = out / f"snapshot_{cohort}.jsonl"
    if not snapshot.exists():
        print(f"no snapshot for {cohort}, skipping {kind} views", file=sys.stderr)
        return None, 0

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
    return rows, len(articles)


def append_summary(path, row):
    new_file = not path.exists()
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    parser.add_argument("--date", type=dt.date.fromisoformat,
                        default=dt.datetime.now(dt.timezone.utc).date(),
                        help="run date in UTC, defaults to today")
    parser.add_argument("--summary", type=Path, help="CSV file to append a run summary to")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    session = make_session()
    run = args.date
    new_pages, states = take_snapshot(run - dt.timedelta(days=SNAPSHOT_LAG), args.out, session)
    problems = check_snapshot(new_pages, states, is_article)

    view_rows = {}
    for kind, lag, n_days in [("early", EARLY_LAG, 2), ("full", FULL_LAG, 30)]:
        cohort = run - dt.timedelta(days=lag)
        rows, n_articles = fetch_views(cohort, n_days, kind, args.out, session)
        view_rows[kind] = len(rows) if rows is not None else 0
        if rows is not None:
            problems += check_views(rows, n_articles, cohort, n_days)

    # Files are already written, so the caller can still upload them.
    if problems:
        sys.exit("data checks failed:\n" + "\n".join(problems))

    if args.summary:
        append_summary(args.summary, {
            "run_date": run.isoformat(),
            "finished_at": now_utc(),
            "new_pages": len(new_pages),
            "snapshots": len(states),
            "early_view_rows": view_rows["early"],
            "full_view_rows": view_rows["full"],
        })


if __name__ == "__main__":
    main()
