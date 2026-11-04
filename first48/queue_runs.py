"""Start the next backfill, content and edits runs until every cohort is collected.

Run on a schedule by .github/workflows/queue.yml. Each call looks at the
release assets, and for each workflow that is idle starts the first piece of
work that is still missing:

- backfill: 2026 days in runs of at most 40 days, then each 2025 month as one bundle.
- content: 2026 days with a snapshot and views, at most 30 days per run.
- edits: one month at a time, once that month's backfill is complete.

    python -m first48.queue_runs
"""
import calendar
import datetime as dt
import json
import subprocess

DAYS_2026 = (dt.date(2026, 1, 1), dt.date(2026, 9, 30))
MONTHS_2025 = [f"2025-{m:02d}" for m in range(1, 13)]
MONTHS_2026 = [f"2026-{m:02d}" for m in range(1, 10)]


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def asset_names(release):
    try:
        return json.loads(gh("release", "view", release, "--json", "assets", "-q", "[.assets[].name]"))
    except subprocess.CalledProcessError as e:
        if "release not found" in e.stderr:
            return []
        raise


def dated(names, prefix):
    return {dt.date.fromisoformat(n[len(prefix):len(prefix) + 10]) for n in names if n.startswith(prefix)}


def days(start, end):
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]


def month_days(month):
    y, m = int(month[:4]), int(month[5:])
    return days(dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1]))


def first_gap(wanted, have, max_days):
    """The first run of consecutive missing days, at most max_days long."""
    missing = [d for d in wanted if d not in have]
    if not missing:
        return None
    start = end = missing[0]
    while end + dt.timedelta(days=1) in missing and (end - start).days + 1 < max_days:
        end += dt.timedelta(days=1)
    return start, end


def busy(workflow):
    runs = json.loads(gh("run", "list", "--workflow", workflow, "--limit", "5", "--json", "status"))
    return any(r["status"] != "completed" for r in runs)


def next_runs(views, snaps, bundles, content, edits):
    """(workflow, inputs) for each workflow that has work left, at most one each."""
    runs = []
    gap = first_gap(days(*DAYS_2026), views, 40)
    todo_2025 = [m for m in MONTHS_2025 if m not in bundles]
    if gap:
        runs.append(("backfill.yml", {"start": gap[0], "end": gap[1]}))
    elif todo_2025:
        d = month_days(todo_2025[0])
        runs.append(("backfill.yml", {"start": d[0], "end": d[-1], "bundle": "true"}))

    gap = first_gap([d for d in days(*DAYS_2026) if d in snaps and d in views], content, 30)
    if gap:
        runs.append(("content.yml", {"start": gap[0], "end": gap[1]}))

    complete = {m for m in MONTHS_2025 if m in bundles}
    complete |= {m for m in MONTHS_2026 if all(d in views and d in snaps for d in month_days(m))}
    todo_edits = [m for m in MONTHS_2026 + MONTHS_2025 if m in complete and m not in edits]
    if todo_edits:
        runs.append(("edits.yml", {"month": todo_edits[0]}))
    return runs


def main():
    backfill = asset_names("backfill")
    views, snaps = dated(backfill, "views_full_"), dated(backfill, "snapshot_")
    bundles = {n[9:16] for n in asset_names("backfill-2025") if n.startswith("backfill_")}
    content = dated(asset_names("content"), "content_")
    edits = {n[6:13] for n in asset_names("edits") if n.startswith("edits_")}
    print(f"2026 days {len(views)}, 2025 months {len(bundles)}/12, content days {len(content)}, "
          f"edits months {len(edits)}/21")

    for workflow, inputs in next_runs(views, snaps, bundles, content, edits):
        if busy(workflow):
            continue
        fields = [arg for k, v in inputs.items() for arg in ("-f", f"{k}={v}")]
        gh("workflow", "run", workflow, *fields)
        print("started", workflow, inputs)


if __name__ == "__main__":
    main()
