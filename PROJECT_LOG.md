# Project log

## 2026-11-01

What I did
- Set up the repo.
- Read Szabo & Huberman (2010) and wrote notes (notes/01). Checked details against the arXiv full text.
- Queried the pageviews API and the MediaWiki creation and move logs to see what data actually exists (notes/02).
- Notes on Pinto, Almeida & Goncalves (2013) (notes/03). Model forms are from a secondary source until I read the original.
- First draft of the pre-analysis plan (PLAN.md).
- Checked the remaining citations: Romano, Patterson & Candes (arXiv 1905.03222) and both M5 papers (IJF 38(4), pages 1346 to 1364 and 1365 to 1385). In FPP3, chapter 5 covers prediction intervals, accuracy and time series cross-validation; chapter 9 is ARIMA and is not needed here.

Decisions and why
- Wikipedia pageviews instead of YouTube: Wikimedia data can be stored and reused for research, while YouTube's API policies restrict storing and aggregating statistics.
- Unit is a new English Wikipedia article (created in or moved into article space, not a redirect), because it gives a clean start time.
- "First 48 hours" means the creation day plus the next day, because per-article views are only available daily. Creation hour becomes a feature.
- Backfill historical cohorts from the logs rather than relying only on the live collector.
- Primary metric is median absolute log error, not MAPE: the target is heavy-tailed and MAPE treats over- and underprediction unequally.
- Seasonal naive and ETS need more than two days of history, so the baselines are flat rate and Szabo-Huberman.
- A quick one-day sample of 200 articles suggested a log-scale correlation around 0.76 between early and 30-day views. Not reported anywhere until it is reproduced by the pipeline with a bootstrap interval and checked across several days, weekdays and weekends.

Later
- Confirmed citation details on Crossref (#2). CQR is NeurIPS 2019.
- Read the 2017 Kaggle winner's write-up (#3). Main takeaways: log1p scale, simple lag features beat their fancy attention, random splits were useless for them, average over seeds.
- Finalized PLAN.md (#5): worked example of the 30-day label lag, at least 6 rolling origins, 5 seeds per comparison, article types from Wikidata, and the mixed-effects timing model.
- Tasks now tracked in GitHub issues.

- Tagged the plan as plan-v1.
- Amendment 1 to the plan: compare a content-only model (text at creation) against the early-signal and combined models, to measure what the first two days add. Reason and leakage rule are in PLAN.md. README now framed as cold-start demand forecasting.

## 2026-11-02

What I did
- `first48/wiki.py`: `fetch_new_articles(day)` pulls one UTC day of page creations in article space and moves into article space (drafts promoted to articles) from the MediaWiki logs. Retries with backoff on 429 and 5xx.
- Tests for the move filter and page id handling.

Decisions and why
- Page id comes from `logpage`, not `pageid`. For a move, `pageid` refers to whatever now sits at the old title (usually a redirect). Spot-checked 8 moved pages: all `logpage` ids resolve to the moved article.
- Moves within article space are renames, not new articles, so they are dropped.
- The day window ends one second before midnight so an event at exactly 00:00:00 is not counted in two days.
- Redirects are kept at this step and filtered in the snapshot step, so the raw data shows what the log actually contained.

Results
- `python -m first48.wiki 2026-09-01` gives 2242 created and 136 moved in, the same counts as the first API probe.

Later
- `snapshot_pages`: for each new page, whether it still exists, is a redirect, its current title, latest revision id and Wikidata item. `fetch_instance_of` adds the Wikidata "instance of" values.
- `fetch_daily_views` and `first48/collect.py`: the daily run. For run date R it snapshots the R-2 cohort, fetches day 0 and 1 views for R-3, and day 0 to 29 views for R-32. Output is one JSONL file per cohort and kind.
- `.github/workflows/collect.yml`: runs every day at 09:00 UTC, reads earlier snapshots from the `data` release and uploads the new files there.

Decisions and why
- Two view fetches per article (after day 1 and after day 29) instead of polling every day: about 1,100 requests a day instead of about 18,000.
- View fetches lag the snapshot by a day because pageviews are published the day after.
- Raw files go to a GitHub release, not a branch, so the repo history stays code only.
- The snapshot is written and uploaded before any view fetch, so a failure later in the run cannot lose it.
- The same page can enter article space twice in one day (moved back to draft, then promoted again). Raw records keep both; the snapshot asks about each page once. Which entry counts as t0 is a staging decision.

Dead ends
- First full test run failed with 429 Too Many Requests partway through the first batch of pageview calls. Wikimedia allows identified bots about 200 requests a minute. Fixed by spacing requests at least 0.35 s apart, honoring Retry-After, and adding the library to the User-Agent as their policy asks. The paced run took about 7 minutes.
- In the test run, pages that had been moved back to draft (and 2 that became templates) still counted as articles because they existed and were not redirects. On the Oct 31 cohort that was 23 of 537. The article filter now also requires the page to be in article space at snapshot time.
- Assumed missing days in the pageviews response meant "before the page existed". Wrong: in the Oct 1 cohort, 324 of 550 articles had days missing in the middle of the window. The API leaves out some zero-view days, so staging treats a missing day as zero.

Results (test run, not the live schedule)
- Simulated runs for 2026-10-03, 11-01 and 11-02 wrote: 1,447 snapshots for the Oct 31 cohort, early views for 595 pages of the Oct 30 cohort, and 30-day views for 550 pages of the Oct 1 cohort. The early and 30-day counts came from before the draft filter fix.

Next step
- Merge, then trigger the first scheduled run. Backfill (#7) and DuckDB staging models after that.
