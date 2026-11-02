"""Collect past cohorts after the fact.

Writes the same files as the daily run, with two differences: the snapshot
shows page state at collection time rather than just after day 1, and only
the 30-day views are fetched (days 0 and 1 are part of them).

Cohorts that already have a 30-day views file in the output folder are
skipped, so an interrupted run can be restarted.
"""
import argparse
import datetime as dt
from pathlib import Path

from first48.collect import FULL_LAG, fetch_views, take_snapshot
from first48.wiki import make_session


def cohort_days(start, end):
    day = start
    while day <= end:
        yield day
        day += dt.timedelta(days=1)


def todo(start, end, out):
    return [d for d in cohort_days(start, end) if not (out / f"views_full_{d}.jsonl").exists()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("start", type=dt.date.fromisoformat, help="first cohort day")
    parser.add_argument("end", type=dt.date.fromisoformat, help="last cohort day")
    parser.add_argument("--out", type=Path, default=Path("data/backfill"))
    args = parser.parse_args()

    latest = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=FULL_LAG)
    if args.end > latest:
        parser.error(f"cohorts after {latest} do not have 30 days of views yet")
    args.out.mkdir(parents=True, exist_ok=True)

    session = make_session()
    for cohort in todo(args.start, args.end, args.out):
        take_snapshot(cohort, args.out, session)
        fetch_views(cohort, 30, "full", args.out, session)


if __name__ == "__main__":
    main()
