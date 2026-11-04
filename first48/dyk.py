"""Which articles were featured in "Did you know" on the Main Page, and when.

The monthly archive pages list each set of hooks under the UTC time it left
the Main Page. A set was shown from the time the set before it left until
its own time. The bold links in a hook are the featured articles. This is
used for error analysis only, never as a model input.

    python -m first48.dyk fetch 2025-01 2026-10
    python -m first48.dyk errors
"""
import argparse
import datetime as dt
import re
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from first48.collect import read_jsonl, write_jsonl
from first48.metrics import log_error
from first48.wiki import API, get_json, make_session

ARCHIVE = "Wikipedia:Did you know archive/{:%Y/%B}"
SET_TIME = re.compile(r"^\*\s*'''''(\d{1,2}:\d{2}, \d{1,2} \w+ \d{4}) \(UTC\)'''''")
BOLD_LINK = re.compile(r"'{3,}\[\[([^\]|#]+)")
FIRST_DAY, LAST_DAY = 2, 29


def parse_archive(wikitext):
    """(time the set left the Main Page, featured titles) for each set, newest first."""
    sets = []
    for line in wikitext.splitlines():
        found = SET_TIME.match(line)
        if found:
            sets.append((dt.datetime.strptime(found.group(1), "%H:%M, %d %B %Y"), []))
        elif sets and line.startswith("* ..."):
            sets[-1][1].extend(t.strip().replace("_", " ") for t in BOLD_LINK.findall(line))
    return sets


def shown_windows(sets):
    """One row per featured title with the window its set was on the Main Page."""
    sets = sorted(sets)
    rows = []
    for (start, _), (end, titles) in zip(sets, sets[1:]):
        rows += [{"title": t, "shown_from": start, "shown_until": end} for t in titles]
    return rows


def page_ids(titles, session):
    """Current page id for each title, following redirects left by later renames."""
    ids = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        data = get_json(session, API, {"action": "query", "titles": "|".join(batch), "redirects": 1,
                                       "format": "json", "formatversion": 2})["query"]
        target = {t: t for t in batch}
        for hop in data.get("normalized", []) + data.get("redirects", []):
            for t, current in target.items():
                if current == hop["from"]:
                    target[t] = hop["to"]
        found = {p["title"]: p["pageid"] for p in data["pages"] if "pageid" in p}
        ids.update({t: found[current] for t, current in target.items() if current in found})
    return ids


def fetch(first_month, last_month, session):
    sets, month = [], first_month
    while month <= last_month:
        data = get_json(session, API, {"action": "parse", "page": ARCHIVE.format(month), "prop": "wikitext",
                                       "format": "json", "formatversion": 2})
        sets += parse_archive(data["parse"]["wikitext"])
        month = dt.date(month.year + month.month // 12, month.month % 12 + 1, 1)
    rows = shown_windows(sets)
    ids = page_ids(sorted({r["title"] for r in rows}), session)
    return [{"page_id": ids[r["title"]], **r, "shown_from": f"{r['shown_from']:%Y-%m-%dT%H:%M:%SZ}",
             "shown_until": f"{r['shown_until']:%Y-%m-%dT%H:%M:%SZ}"} for r in rows if r["title"] in ids]


def featured_after_day_1(articles, dyk):
    """True for articles whose set started on day 2 to day 29 after creation."""
    shown = pd.DataFrame(dyk, columns=["page_id", "shown_from"])
    df = articles[["page_id", "cohort_date"]].merge(shown, on="page_id", how="left")
    shown_day = pd.to_datetime(df["shown_from"], format="%Y-%m-%dT%H:%M:%SZ").dt.normalize()
    day = (shown_day - pd.to_datetime(df["cohort_date"])).dt.days
    df["featured"] = day.between(FIRST_DAY, LAST_DAY)
    return df.groupby("page_id")["featured"].any()


def errors_by_group(preds, featured):
    preds = preds.assign(featured=preds["page_id"].map(featured).fillna(False).astype(bool))
    rows = []
    for col in [c for c in preds.columns if c not in ("origin", "page_id", "views_30d", "featured")]:
        for is_featured, group in preds.groupby("featured"):
            rows.append({"model": col.partition("_seed")[0], "featured": is_featured, "n": len(group),
                         "median_abs_log_error": float(np.median(log_error(group[col], group["views_30d"])))})
    # Seeded models are averaged over seeds.
    return pd.DataFrame(rows).groupby(["model", "featured"], as_index=False).mean()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("first", type=lambda s: dt.date.fromisoformat(s + "-01"))
    f.add_argument("last", type=lambda s: dt.date.fromisoformat(s + "-01"))
    f.add_argument("--out", type=Path, default=Path("data/dyk.jsonl"))
    e = sub.add_parser("errors")
    e.add_argument("--dyk", type=Path, default=Path("data/dyk.jsonl"))
    e.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    e.add_argument("--preds", type=Path, default=Path("data/backtest_point_predictions.parquet"))
    e.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    if args.command == "fetch":
        rows = fetch(args.first, args.last, make_session())
        write_jsonl(args.out, rows)
        print(f"{len(rows):,} featured articles")
        return
    con = duckdb.connect(str(args.db), read_only=True)
    articles = con.execute("select page_id, cohort_date from fct_articles where dataset = 'backfill'").df()
    featured = featured_after_day_1(articles, read_jsonl(args.dyk))
    out = errors_by_group(pd.read_parquet(args.preds), featured)
    args.out.mkdir(exist_ok=True)
    out.to_csv(args.out / "dyk_errors.csv", index=False)
    print(f"{int(featured.sum()):,} of {len(featured):,} articles featured on day {FIRST_DAY} to {LAST_DAY}")
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
