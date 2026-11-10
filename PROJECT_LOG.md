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

- Collector merged to main and live. First run triggered by hand on 2026-11-02: snapshot of the Oct 31 cohort uploaded to the `data` release. Scheduled runs at 09:00 UTC from 2026-11-03. Early views start with the Nov 4 run, 30-day views with the Dec 3 run.

Later
- Collector writes a one-row summary per run (`collector_runs.csv`) and commits it to main. GitHub disables scheduled workflows in public repos after 60 days without repository activity, and release uploads may not count. The docs don't define activity; a commit to the default branch is the safest signal.
- Planned monthly compaction of release assets (#18). Releases allow 1,000 assets, each under 2 GiB. Daily files would fill the data release in about 8 months.
- `first48/backfill.py` and a manual `backfill` workflow: collect past cohorts one month per run, into a separate `backfill` release.
- Data checks (`first48/checks.py`) run on every daily collection: page counts in a sane range, one snapshot per new page, required fields present, article share between 10% and 80%, view rows match articles, no negative views, no dates outside the window. Any failure exits non-zero after files are written, so the workflow fails and GitHub sends a failure email, but the raw files still upload.
- DESIGN_DOC.md: one-page design doc (problem, users, decision, metrics, guardrails, launch criteria, monitoring, risks).
- Amendment 2 to the plan: current-practice baseline for the flag (rank by day-1 views), MLflow tracking for backtests, shadow mode for the live system, drift monitoring with an alert issue, and a proposed (not run) online experiment.

More decisions
- Backfilled and live data are kept in separate releases. Backfilled snapshots show page state at collection time, not after day 1, so they must never be mixed up with live snapshots.
- Backfill fetches only the 30-day views; days 0 and 1 are part of them.
- Backfill cohorts: 2026-01-01 to 2026-09-30. Every cohort has its full 30 days, and the range ends before the live collector starts, so there is no overlap.
- The backfill skips cohorts that already have a views file, so a run that times out can be restarted.
- The backfill and the daily run share a concurrency group so they never call the API at the same time.
- About 3 files per cohort day means 9 months is about 820 assets, close to the 1,000 limit. Compaction (#18) applies to the backfill release too.
- The current-practice flag baseline replaces "rank by day 0 plus day 1", which was nearly the same rule. For the point forecast, flat rate already is current practice, so no extra baseline was added.

Results
- Backfill test for the 2026-09-01 cohort: 2,378 new pages (2,242 created plus 136 moved in, matching the earlier counts), 570 articles with 30-day views, 3 min 50 s. A rerun skipped the finished cohort. At this speed one month takes about 2 hours.
- Daily run with checks, simulated for 2026-11-03: 1,694 new pages, 1,693 snapshots, early views for 514 articles. All checks passed.

Next step
- Run the backfill month by month, then load raw files into DuckDB with staging models.

## 2026-11-03

What I did
- Backfill for Jan and Feb 2026 finished (177 files, 3 h 43 min). Mar and Apr running on Actions, Jul to Sep running locally, May and Jun next.
- First scheduled daily run: snapshot for Nov 1, early views for Oct 31, run summary committed to main. It started at 16:40 UTC, not 09:00; scheduled runs can be delayed by hours, so the "day-1 snapshot" is really a snapshot some hours after day 1.
- DuckDB warehouse (`first48/warehouse.py`, `sql/`): raw tables, staging models for new pages, snapshots and daily views, article types, `fct_articles` (one row per article with complete 30-day views), `fct_early_views` (live), `cohort_summary`. Nine SQL data tests; the build fails if any returns rows.
- Article types from the 120 most common Wikidata "instance of" values in Jan and Feb (`sql/seeds/article_types.csv`), labels checked against Wikidata.
- Metrics, baselines (flat rate, Szabo-Huberman, log-linear) and LightGBM, rolling-origin backtest with MLflow tracking.
- 80% intervals: LightGBM quantiles with a conformal adjustment from the most recent 14 days of training cohorts.
- Day-2 flag: top 5% of each creation day by forecast, against top 5% by day-1 views.
- Content comparison (Amendment 1): text at the end of day 0 and day 1 fetched by revision timestamp, sentence embeddings, three models.
- Mixed-effects timing model in R.
- Shadow mode and drift monitoring in the daily job, waiting for a model trained on the full backfill.

Decisions and why
- Plain SQL files run in order by a short Python script instead of dbt: same idea (models plus data tests), nothing extra to install.
- t0 is the first time a page entered article space; the snapshot and views used are the ones from that cohort.
- Log errors use log(1 + views): about 2% of articles have zero views in 30 days.
- Point model is LightGBM with an L1 loss on log views, so it predicts the median, which matches the primary metric.
- Szabo-Huberman keeps the lognormal mean correction, as written in the plan, even though it raises the median error.
- The flag ranks articles within their creation day, so it can be acted on at the end of day 1 without waiting for the week.
- Text encoder fixed before any fold is scored: sentence-transformers/all-MiniLM-L6-v2, revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41.
- Renamed (title at snapshot differs from title at t0) and number of entries are not model features: both are only known later.
- Disambiguation pages (about 3% of articles) stay in the population, as the plan defines it, under "other".
- Collection and analysis requirements split so the daily job does not install torch.

Dead ends
- The local Jul to Sep backfill stopped at Jul 13 when the network dropped (connection reset, then failed DNS lookups). It now runs in a retry loop; days already written are skipped, and a half-written day is redone because a day only counts as done once its views file exists.
- The "no articles dropped" data test first matched any view on the cohort date, so a cohort still being collected looked broken (430 rows flagged). It now checks day 0 only.

Notes for later
- 7% of backfilled articles were renamed after creation; their views are fetched under the current title, so views under the old title are missed. Part of the known rename threat.

Also
- README rewritten: method, reproduce steps and FAQ. The results table and chart are added after the holdout is scored. The chart comes from `python -m first48.chart`, which reads the backtest results file.

Data review and Amendment 3
- Backfill and text runs over two months hit the 6-hour job limit and were cancelled. Files written before the cancel were uploaded, so Jan 1 to Apr 15 (views) and Jan 1 to Feb 17 (text) are in. Runs are now at most 30 to 40 days.
- Share of logged new pages that still exist: 92.7% (Jan 2026), 92.8% (Feb), 93.4% (Jul), and 93.7% and 89.5% on two 2025 days. Deletions happen early, so older cohorts are not much more affected.
- Only about a third of logged creations are articles; the rest are redirects.
- Median 30-day views per article is 74; the top 10% get 1,195 or more (Jan and Feb cohorts).
- Raw files are about 0.95 MB a day, 8 times smaller compressed. Download time is the limit, not space.
- A release holds at most 1,000 files, so 2025 goes on its own release with one compressed file per month.
- The content fetch already read revision history up to the end of day 1 but kept only the last revision. Edit activity is now fetched on its own, for every backfilled month and daily for live cohorts.

Next step
- Finish the backfill, text and edits runs, train the shadow-mode model, then run every backtest on the full data.

## 2026-11-07: results

- Collection finished: 353,386 articles from 2025-01-01 to 2026-09-30, all with edit activity, all data tests passing.
- Each collection run now starts the queue itself; runs started by the workflow token never fired the workflow_run trigger, so the queue had only woken on the schedule, every few hours.
- The content comparison had picked up the 2025 origins and a few hundred 2025 page ids that also have 2026 text. Fixed to 2026 cohorts and the plan-v1 origins, as Amendment 3 says. Found before the holdout wrote anything; the holdout was then scored once.
- Holdout: point and flag criteria met. Interval coverage 83.6% against the planned 77% to 83%, reported as missed; the ranges are too wide for small articles and too narrow for the busiest ones.
- The local data folder moved out of the synced Desktop to `~/first48-data`, with `data` as a link, after file sync created duplicate copies of raw files. The warehouse tests would have caught the duplicates.

Next step
- Score the live shadow-mode cohorts once their 30 days are complete (first ones around December 1).
- Day-4 and day-8 updated forecasts (Amendment 3).

## 2026-11-09: later forecasts and the daily job

- Forecasts at the end of day 3 and day 7 (Amendment 3) are in RESULTS.md: median log error 0.278 and 0.183, against 0.402 at the end of day 1, better in all 18 backtest months. The holdout was not used.
- The daily shadow step failed on Nov 8 and 9 because it imported MLflow, which the job does not install. MLflow now loads only when logging, with a test that blocks it.

## 2026-11-10: live forecasts

- The Nov 10 daily run passed with the MLflow fix and wrote shadow forecasts for the Oct 31 to Nov 7 cohorts. These are the first live forecasts; their 30-day outcomes arrive from early December.
- The daily workflow is now three jobs: collect, then forecast, then report. The report job runs even when an earlier job fails and opens an issue saying which one broke.
- Collection is finished, so the queue workflow no longer runs on a schedule. It can still be started by hand.
