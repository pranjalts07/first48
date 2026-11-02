"""Checks on each day's raw data. Each function returns a list of problems."""
import datetime as dt

# A normal day has roughly 1,200 to 2,500 new pages, about a third of them
# articles. These bounds only catch a broken run, not a quiet day.
MIN_NEW_PAGES = 300
MAX_NEW_PAGES = 10_000
MIN_ARTICLE_SHARE = 0.10
MAX_ARTICLE_SHARE = 0.80


def check_snapshot(new_pages, states, is_article):
    problems = []
    if not MIN_NEW_PAGES <= len(new_pages) <= MAX_NEW_PAGES:
        problems.append(f"{len(new_pages)} new pages, expected {MIN_NEW_PAGES} to {MAX_NEW_PAGES}")

    for page in new_pages:
        if not (page.get("page_id") and page.get("title") and page.get("t0")):
            problems.append(f"new page record missing a field: {page}")
            break

    expected = {p["page_id"] for p in new_pages}
    seen = [s["page_id"] for s in states]
    if len(seen) != len(set(seen)):
        problems.append("duplicate page ids in snapshot")
    if set(seen) != expected:
        problems.append(f"snapshot covers {len(set(seen))} pages, log has {len(expected)}")

    if states:
        share = sum(is_article(s) for s in states) / len(states)
        if not MIN_ARTICLE_SHARE <= share <= MAX_ARTICLE_SHARE:
            problems.append(f"article share {share:.2f}, expected {MIN_ARTICLE_SHARE} to {MAX_ARTICLE_SHARE}")
    return problems


def check_views(rows, n_articles, cohort, n_days):
    problems = []
    if len(rows) != n_articles:
        problems.append(f"{len(rows)} view rows for {n_articles} articles")

    first = cohort.isoformat()
    last = (cohort + dt.timedelta(days=n_days - 1)).isoformat()
    for row in rows:
        days = row["views"]
        if any(v < 0 for v in days.values()):
            problems.append(f"negative views for page {row['page_id']}")
            break
        if days and not (first <= min(days) and max(days) <= last):
            problems.append(f"views outside {first} to {last} for page {row['page_id']}")
            break
    return problems
