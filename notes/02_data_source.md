# Data source and unit of analysis

Checked by calling the APIs directly on 2026-11-01.

## What the APIs give us

Pageviews (Wikimedia REST API)
- `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}`
- Per-article granularity is `daily` or `monthly` only. Hourly is rejected with a 400.
- Daily history goes back to 2015-07-01.
- Data for a day shows up the next day (2026-10-31 was available on 2026-11-01).
- `agent=user` drops traffic the platform identifies as spiders or automated, but some bot traffic will still get through.
- Views are keyed by title, so a page rename splits its history across two titles.
- Requests need a descriptive User-Agent with a contact.

New articles (MediaWiki Action API, en.wikipedia.org/w/api.php)
- `list=logevents&letype=create&lenamespace=0` lists every page created in article space, with page id and UTC timestamp. Most of these are redirects, not articles.
- Many real articles start as drafts and are moved into article space later. Those show up as `letype=move` events with `target_ns=0`, not as creations.
- `prop=info` on page ids tells us whether a page is currently a redirect or has been deleted.

## Decisions

1. Unit: a new English Wikipedia article. That means a page created in article space or moved there from draft or user space, and not a redirect.
2. Start time t0: the creation or move timestamp.
3. Early window: per-article views are daily only, so "first 48 hours" means the creation day (partial) plus the next full day. The creation hour goes in as a feature because an article created at 23:00 has one hour of exposure on day 0, while one created at 01:00 has 23.
4. Target: total views over days 0 to 29.
5. Backfill: the logs and pageviews both go back years, so we can build a historical set now instead of waiting six weeks. The daily collector still matters for live predictions and the dashboard.

## Known risks to handle later

- Survivorship: checking redirect or deleted status today, for an article created months ago, uses information we would not have had on day 2. The live collector records status as of day 2. For backfilled data we either accept and report this bias or estimate its size.
- Renames: we need to track pages by page id and record title changes.
- Late bloomers: some articles get almost no views in the first two days and then take off. These limit any model that uses early views alone.
