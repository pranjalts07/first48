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

Next step
- Read the original Pinto et al. paper and fill in the unverified claims.
- Study the 2017 Kaggle Web Traffic winner and write up why it won.
- Finalize PLAN.md, then start Phase 1 (collector and backfill).
