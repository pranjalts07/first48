# Project log

## 2026-11-01

What we did
- Created the repo and folder structure.
- Started Phase 0 with Szabo & Huberman (2010). Checked the citation against the arXiv full text (arXiv:0811.0405).

Decisions and why
- Repo name `first48`: names the question directly (what the first 48 hours tell us).
- Wikipedia pageviews instead of YouTube: the Wikimedia data can be stored and reused for research, while YouTube's API policies restrict storing and aggregating statistics.

- Probed the pageviews API and the MediaWiki logs to see what data actually exists (notes/02_data_source.md).

More decisions
- Unit is a new English Wikipedia article (created in or moved into article space, not a redirect), since that gives a clean start time.
- "First 48 hours" means creation day plus the next day, because per-article views are daily only. Creation hour becomes a feature.
- Backfill history from the logs instead of only waiting for the live collector.

Later the same day
- Notes on Pinto, Almeida & Goncalves (2013) (notes/03). Model forms taken from a secondary source; original still to read.
- First draft of the pre-analysis plan (PLAN.md).
- Citations checked: Szabo & Huberman (arXiv full text), Romano, Patterson & Candes (arXiv 1905.03222), both M5 papers (IJF 38(4), pages 1346 to 1364 and 1365 to 1385). FPP3 chapter 5 covers intervals, evaluation and time series cross-validation; chapter 9 is ARIMA, so chapter 5 is the one we need.

More decisions
- Primary metric is median absolute log error, not MAPE, because the target is heavy-tailed and MAPE treats over- and underprediction unequally.
- Seasonal naive and ETS do not apply to a series that is two days long. Replaced by a flat-rate baseline.
- The 0.76 correlation from the one-day probe will only be reported with a bootstrap interval and after checking several days, weekdays and weekends.

Next step
- Read the original Pinto paper through the library and fill in the unverified claims.
- Study the 2017 Kaggle winner and write the "why it won" note.
- Sign off PLAN.md, then start Phase 1 (collector and backfill).
