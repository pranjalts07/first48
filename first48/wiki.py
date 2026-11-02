import datetime as dt
import sys
import time

import requests

API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "first48/0.1 (https://github.com/pranjalts07/first48)"


def make_session():
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def get_json(session, url, params, tries=5):
    for attempt in range(tries):
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code == 429 or resp.status_code >= 500:
            time.sleep(2 ** attempt)
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


if __name__ == "__main__":
    day = dt.date.fromisoformat(sys.argv[1])
    records = fetch_new_articles(day)
    creates = sum(r["source"] == "create" for r in records)
    print(f"{day}: {creates} created, {len(records) - creates} moved in")
