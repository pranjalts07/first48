"""Edit activity in an article's first two days.

The revision history from t0 to the end of day 1 is read by timestamp, so
these features are exactly what was known at the end of day 1, whenever
they are fetched. Edits made before t0, in draft or user space, are not
counted.

    python -m first48.edits 2026-01-01 2026-01-31 --pages data/backfill --out data/edits
"""
import argparse
import datetime as dt
from pathlib import Path

from first48.backfill import cohort_days
from first48.collect import is_article, read_jsonl, write_jsonl
from first48.content import day_ends, stamp
from first48.wiki import API, get_json, make_session


def revisions_between(page_id, start, end, session):
    """Revisions from start to end inclusive, newest first."""
    params = {
        "action": "query",
        "prop": "revisions",
        "pageids": page_id,
        "rvprop": "timestamp|user|size",
        "rvlimit": 500,
        "rvdir": "older",
        "rvstart": stamp(end),
        "rvend": stamp(start),
        "format": "json",
        "formatversion": 2,
    }
    revs = []
    while True:
        data = get_json(session, API, params)
        revs.extend(data["query"]["pages"][0].get("revisions", []))
        if "continue" not in data:
            return revs
        params.update(data["continue"])


def edit_features(revs, end_d0):
    on_d0 = [r for r in revs if r["timestamp"] <= stamp(end_d0)]
    # Hidden usernames count as one editor.
    editors = {r.get("user", "(hidden)") for r in revs}
    return {
        "edits_d0": len(on_d0),
        "edits_48h": len(revs),
        "editors_48h": len(editors),
        "size_d0": on_d0[0]["size"] if on_d0 else None,
        "size_d1": revs[0]["size"] if revs else None,
    }


def first_entries(new_pages):
    t0 = {}
    for page in new_pages:
        t0[page["page_id"]] = min(t0.get(page["page_id"], page["t0"]), page["t0"])
    return t0


def cohort_edits(cohort, pages, session):
    t0 = first_entries(read_jsonl(pages / f"new_pages_{cohort}.jsonl"))
    articles = [s["page_id"] for s in read_jsonl(pages / f"snapshot_{cohort}.jsonl") if is_article(s)]
    end_d0, end_d1 = day_ends(cohort)
    rows = []
    for page_id in articles:
        start = dt.datetime.strptime(t0[page_id], "%Y-%m-%dT%H:%M:%SZ")
        revs = revisions_between(page_id, start, end_d1, session)
        rows.append({"page_id": page_id, **edit_features(revs, end_d0)})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("start", type=dt.date.fromisoformat)
    parser.add_argument("end", type=dt.date.fromisoformat)
    parser.add_argument("--pages", type=Path, default=Path("data/backfill"))
    parser.add_argument("--out", type=Path, default=Path("data/edits"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    session = make_session()
    for cohort in cohort_days(args.start, args.end):
        out = args.out / f"edits_{cohort}.jsonl"
        if out.exists() or not (args.pages / f"snapshot_{cohort}.jsonl").exists():
            continue
        write_jsonl(out, cohort_edits(cohort, args.pages, session))


if __name__ == "__main__":
    main()
