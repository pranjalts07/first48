"""Article text as it stood at the end of day 0 and day 1.

For each article, the revision current at the end of each day is looked up
by timestamp, never the current text, so content features cannot leak
later edits. Only the start of the plain text is kept.

    python -m first48.content 2026-01-01 2026-01-31 --snapshots data/backfill --out data/content
"""
import argparse
import datetime as dt
import re
from pathlib import Path

import mwparserfromhell

from first48.backfill import cohort_days
from first48.collect import is_article, read_jsonl, write_jsonl
from first48.wiki import API, chunks, get_json, make_session

TEXT_CHARS = 1500


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def day_ends(cohort):
    start = dt.datetime(cohort.year, cohort.month, cohort.day, tzinfo=dt.timezone.utc)
    return start + dt.timedelta(days=1, seconds=-1), start + dt.timedelta(days=2, seconds=-1)


def revisions_before(page_id, end_d0, end_d1, session):
    """Latest revision at or before the end of day 0 and of day 1."""
    params = {
        "action": "query",
        "prop": "revisions",
        "pageids": page_id,
        "rvprop": "ids|timestamp|size",
        "rvlimit": 50,
        "rvdir": "older",
        "rvstart": stamp(end_d1),
        "format": "json",
        "formatversion": 2,
    }
    revs = []
    while True:
        data = get_json(session, API, params)
        revs.extend(data["query"]["pages"][0].get("revisions", []))
        if any(r["timestamp"] <= stamp(end_d0) for r in revs) or "continue" not in data:
            break
        params.update(data["continue"])
    at_d1 = revs[0] if revs else None
    at_d0 = next((r for r in revs if r["timestamp"] <= stamp(end_d0)), None)
    return at_d0, at_d1


def fetch_texts(rev_ids, session):
    texts = {}
    for batch in chunks(sorted(set(rev_ids))):
        params = {
            "action": "query",
            "prop": "revisions",
            "revids": "|".join(str(r) for r in batch),
            "rvprop": "ids|content",
            "rvslots": "main",
            "format": "json",
            "formatversion": 2,
        }
        data = get_json(session, API, params)
        for page in data["query"].get("pages", []):
            for rev in page.get("revisions", []):
                texts[rev["revid"]] = rev["slots"]["main"].get("content", "")
    return texts


def plain_text(wikitext, limit=TEXT_CHARS):
    code = mwparserfromhell.parse(wikitext)
    for ref in code.filter_tags(matches=lambda node: node.tag == "ref"):
        try:
            code.remove(ref)
        except ValueError:
            pass  # already removed with an enclosing ref
    text = code.strip_code()
    return re.sub(r"\s+", " ", text).strip()[:limit]


def cohort_content(cohort, snapshots, session):
    end_d0, end_d1 = day_ends(cohort)
    articles = [s for s in read_jsonl(snapshots / f"snapshot_{cohort}.jsonl") if is_article(s)]
    found = {a["page_id"]: revisions_before(a["page_id"], end_d0, end_d1, session) for a in articles}
    rev_ids = [r["revid"] for pair in found.values() for r in pair if r]
    texts = fetch_texts(rev_ids, session)

    rows = []
    for page_id, (at_d0, at_d1) in found.items():
        row = {"page_id": page_id}
        for day, rev in (("d0", at_d0), ("d1", at_d1)):
            row[f"rev_{day}"] = rev["revid"] if rev else None
            row[f"size_{day}"] = rev["size"] if rev else None
            row[f"text_{day}"] = plain_text(texts.get(rev["revid"], "")) if rev else ""
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("start", type=dt.date.fromisoformat)
    parser.add_argument("end", type=dt.date.fromisoformat)
    parser.add_argument("--snapshots", type=Path, default=Path("data/backfill"))
    parser.add_argument("--out", type=Path, default=Path("data/content"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    session = make_session()
    for cohort in cohort_days(args.start, args.end):
        out = args.out / f"content_{cohort}.jsonl"
        if out.exists() or not (args.snapshots / f"snapshot_{cohort}.jsonl").exists():
            continue
        write_jsonl(out, cohort_content(cohort, args.snapshots, session))


if __name__ == "__main__":
    main()
