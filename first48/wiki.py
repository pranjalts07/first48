import datetime as dt
import sys
import time
from urllib.parse import quote

import requests

API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
PAGEVIEWS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"
USER_AGENT = f"first48/0.1 (https://github.com/pranjalts07/first48) requests/{requests.__version__}"

# Wikimedia allows identified bots about 200 requests a minute. Staying
# under 3 a second leaves some room.
MIN_INTERVAL = 0.35
_last_request = 0.0


def make_session():
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def wait_turn():
    global _last_request
    pause = _last_request + MIN_INTERVAL - time.monotonic()
    if pause > 0:
        time.sleep(pause)
    _last_request = time.monotonic()


def get_json(session, url, params, tries=6):
    for attempt in range(tries):
        wait_turn()
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code == 429 or resp.status_code >= 500:
            retry_after = resp.headers.get("Retry-After", "")
            time.sleep(int(retry_after) if retry_after.isdigit() else max(5, 2 ** attempt))
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()


def log_events(session, letype, start, end, namespace=None):
    params = {
        "action": "query",
        "list": "logevents",
        "letype": letype,
        "lestart": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "leend": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ledir": "newer",
        "lelimit": 500,
        "format": "json",
        "formatversion": 2,
    }
    if namespace is not None:
        params["lenamespace"] = namespace

    while True:
        data = get_json(session, API, params)
        yield from data["query"]["logevents"]
        if "continue" not in data:
            break
        params.update(data["continue"])


def is_promotion(event):
    # A draft or user page moved into article space. Renames within
    # article space are not new articles.
    return event.get("ns") != 0 and event.get("params", {}).get("target_ns") == 0


def to_record(event, title, source):
    # logpage is the page id at the time of the event. For moves, pageid
    # points at whatever now sits at the old title, often a redirect.
    return {
        "page_id": event["logpage"],
        "title": title,
        "t0": event["timestamp"],
        "source": source,
    }


def fetch_new_articles(day, session=None):
    """Pages created in or moved into article space on a UTC day.

    Redirects are still included here; they are filtered in a later step.
    """
    session = session or make_session()
    start = dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1, seconds=-1)

    records = []
    for event in log_events(session, "create", start, end, namespace=0):
        if "logpage" in event and "title" in event:
            records.append(to_record(event, event["title"], "create"))
    for event in log_events(session, "move", start, end):
        if "logpage" in event and is_promotion(event):
            records.append(to_record(event, event["params"]["target_title"], "move"))
    return records


def chunks(items, size=50):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def page_state(page, taken_at):
    return {
        "page_id": page["pageid"],
        "taken_at": taken_at,
        "exists": not page.get("missing", False),
        "namespace": page.get("ns"),
        "is_redirect": page.get("redirect", False),
        "title": page.get("title"),
        "last_rev_id": page.get("lastrevid"),
        "wikidata_item": page.get("pageprops", {}).get("wikibase_item"),
    }


def snapshot_pages(page_ids, session=None):
    """State of each page right now: exists, redirect, title, latest revision, Wikidata item."""
    session = session or make_session()
    taken_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # The same page can enter article space twice in a day (moved back to
    # draft and promoted again), so ask about each id once.
    unique_ids = list(dict.fromkeys(page_ids))
    rows = []
    for batch in chunks(unique_ids):
        params = {
            "action": "query",
            "prop": "info|pageprops",
            "ppprop": "wikibase_item",
            "pageids": "|".join(str(p) for p in batch),
            "format": "json",
            "formatversion": 2,
        }
        data = get_json(session, API, params)
        rows.extend(page_state(page, taken_at) for page in data["query"]["pages"])
    return rows


def instance_of(entity):
    claims = entity.get("claims", {}).get("P31", [])
    return [c["mainsnak"]["datavalue"]["value"]["id"] for c in claims if "datavalue" in c["mainsnak"]]


def fetch_instance_of(items, session=None):
    """Wikidata "instance of" values for each item, e.g. {"Q937": ["Q5"]}."""
    session = session or make_session()
    result = {}
    for batch in chunks(sorted(set(items))):
        params = {"action": "wbgetentities", "ids": "|".join(batch), "props": "claims", "format": "json"}
        data = get_json(session, WIKIDATA_API, params)
        for item, entity in data.get("entities", {}).items():
            result[item] = instance_of(entity)
    return result


def fetch_daily_views(title, start, end, session=None):
    """Daily user views for a title between two dates, inclusive, as {"2026-09-01": 29, ...}.

    The API leaves out some days with no views, so a missing day means zero
    views once the page exists.
    """
    session = session or make_session()
    article = quote(title.replace(" ", "_"), safe="")
    url = f"{PAGEVIEWS}/{article}/daily/{start:%Y%m%d}00/{end:%Y%m%d}00"
    try:
        data = get_json(session, url, params=None)
    except requests.HTTPError as err:
        # The API answers 404 when a title has no views at all in the range.
        if err.response is not None and err.response.status_code == 404:
            return {}
        raise
    return {iso_day(item["timestamp"]): item["views"] for item in data["items"]}


def iso_day(timestamp):
    return f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"


if __name__ == "__main__":
    day = dt.date.fromisoformat(sys.argv[1])
    records = fetch_new_articles(day)
    creates = sum(r["source"] == "create" for r in records)
    print(f"{day}: {creates} created, {len(records) - creates} moved in")
