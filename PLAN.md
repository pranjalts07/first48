# Pre-analysis plan

Status: draft, 2026-11-01. Fixed before any modeling. Changes after modeling starts get logged in PROJECT_LOG.md with the reason.

## Question
From a new English Wikipedia article's first two days of views, predict its total views over its first 30 days, with an 80% prediction interval, and flag likely top-5% articles by the end of day 1.

## Population and data
- Unit: a new article in English Wikipedia article space (created there or moved in from draft or user space), not a redirect. See notes/02_data_source.md.
- t0: creation or move timestamp, UTC. Day 0 is the calendar day of t0 (partial); day 1 is the next day.
- Inputs: views on day 0 and day 1, creation hour, weekday, and page metadata known by the end of day 1.
- Target: Y = total views on days 0 to 29.
- Sources: Wikimedia pageviews API (agent=user) and the MediaWiki creation and move logs. Historical cohorts are backfilled; new cohorts come from the daily collector.

## Splits
- Cohorts are defined by creation date.
- A label is only known 30 days after creation. At a forecast origin T, training may use only articles created on or before T minus 30 days.
- Rolling origin: one origin per month; test set is the articles created in the 7 days after T.
- The most recent 6 weeks of complete cohorts are a final holdout, used once at the end.

## Metrics
- Primary: median absolute log error, |log(prediction / Y)|. It reads as "typically off by a factor of x" and is not dominated by a few huge articles.
- Secondary: mean absolute log error; SMAPE (comparable with the 2017 Kaggle competition); absolute error in raw views, summed over a cohort (the quantity a caching or staffing decision depends on).
- MAPE is reported but not used to pick models: it punishes overprediction more than underprediction and is unstable for small counts.
- Intervals: empirical coverage of the 80% interval, mean interval width on the log scale, and pinball loss at the 0.1, 0.5 and 0.9 quantiles. Coverage is also reported within bins of day-1 views, since overall coverage can hide undercoverage for large articles.
- Flag: precision and recall for "top 5% of Y within the creation week", plus precision-recall AUC.

## Baselines
1. Flat rate: Y = views on days 0 and 1 + 28 x day-1 views. Used instead of seasonal naive and ETS, which need more history than two days.
2. Szabo-Huberman: log Y = log(views on days 0 and 1) + b, slope fixed at 1, with the variance correction when converting back.
3. Flag baseline: rank articles by day-0 plus day-1 views and flag the top 5%.

## Models
- Log-linear with a free slope and creation-hour adjustment.
- LightGBM on early-view and metadata features, point and quantile objectives.
- Conformal adjustment of the quantile model (conformalized quantile regression) using a calibration set of earlier cohorts.

## Success criteria
- Point: LightGBM has lower median absolute log error than both the flat-rate and Szabo-Huberman baselines in most rolling folds, and the paired bootstrap 95% interval for the difference on the final holdout excludes zero. Reported overall and per article type.
- Intervals: 80% intervals cover between 77% and 83% of final holdout articles.
- Flag: higher precision at equal recall than the flag baseline on the final holdout.
- If a criterion is missed, the result is reported as is.

## Reporting rules
- Any correlation or summary statistic comes with a bootstrap confidence interval and is checked across several creation days, including weekdays and weekends.
- Every number in RESULTS.md comes with the command that reproduces it.

## Known threats
- Survivorship in backfilled data: status (deleted, redirected) is checked after the fact. The live collector records status at the end of day 1; the size of the bias is estimated by comparing the two.
- Leakage: no feature may use information after the end of day 1. Training labels respect the 30-day lag above.
- Page renames split views across titles; pages are tracked by page id.
- Bot traffic not caught by the agent=user filter.
