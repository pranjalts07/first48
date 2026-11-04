# Pre-analysis plan

Status: fixed on 2026-11-01, before any modeling. Changes after modeling starts get logged in PROJECT_LOG.md with the reason.

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
- A label is only known 30 days after creation. At a forecast origin T, training may use only articles created on or before T minus 30 days. Example: for T = Oct 10, an article created Oct 5 has no label until Nov 3, so it can't be used; training stops at Sep 10.
- Rolling origin: one origin per month, at least 6 origins; test set is the articles created in the 7 days after T.
- Anything computed across articles (scalers, the top-5% cutoff, encodings) is fit on the training cohorts of that fold only.
- Model comparisons average over 5 random seeds.
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
3. Flag baseline: rank articles by day-1 views and flag the top 5% (current practice, see Amendment 2).

## Models
- Log-linear with a free slope and creation-hour adjustment.
- LightGBM on early-view and metadata features, point and quantile objectives.
- Conformal adjustment of the quantile model (conformalized quantile regression) using a calibration set of earlier cohorts.

## Article type
Grouped from the Wikidata "instance of" value as of the end of day 1: person, film or TV, sports event, place, organization, other. Articles with no Wikidata item yet are "other".

## Timing question (association only)
Mixed-effects model: log Y ~ log(day 0 + day 1 views) + creation hour + weekday + (1 | article type). Reports whether creation timing is associated with 30-day views after adjusting for early views. Not a causal claim: editors choose when to publish.

## Success criteria
- Point: LightGBM has lower median absolute log error than both the flat-rate and Szabo-Huberman baselines in most rolling folds, and the paired bootstrap 95% interval for the difference on the final holdout excludes zero. Reported overall and per article type.
- Intervals: 80% intervals cover between 77% and 83% of final holdout articles.
- Flag: higher precision at equal recall than the flag baseline on the final holdout.
- If a criterion is missed, the result is reported as is.

## Reporting rules
- Any correlation or summary statistic comes with a bootstrap confidence interval and is checked across several creation days, including weekdays and weekends.
- Every number in RESULTS.md comes with the command that reproduces it.

## Amendment 1 (2026-11-01, before any modeling)
Reason: early views alone answer "how big will this be", but not "how much do early views add over what we could know at creation". That second question is the cold-start question platforms actually face, and Shulman, Sharma & Cosley (2016) suggest early timing signals can dominate prediction without explaining it.

Added question: how much do the first two days of views add beyond content known at creation?
- (a) Content-only: text embedding of the article's opening text plus article type, from the revision current at the end of day 0. No view data.
- (b) Early-signal: the plan-v1 model.
- (c) Combined: (a) and (b) features together, content from the revision at the end of day 1.
- Same metrics, splits, seeds and final holdout as plan-v1. The added value of early views is the difference in median absolute log error between (c) and (a), with a paired bootstrap 95% interval.
- Embeddings come from a small open-source model run locally. The model name and version are fixed before the first fold is scored.

Leakage rule: content features use only the revision that existed at the end of day 0 (for a) or day 1 (for c), looked up by timestamp. Never the current text.

Out of scope until the core is done: repeating the analysis on new GitHub repositories (GH Archive) to test whether the result generalizes.

## Amendment 2 (2026-11-02, before any modeling)
Reason: compare against what a team would do without a model, track every backtest, and define how the model is checked and maintained after launch.

- Current-practice baseline for the flag: rank new articles by day-1 views alone (yesterday's trending list) and flag the top 5%. Replaces the day-0 plus day-1 flag baseline, which is close to it. For the point forecast, flat rate already plays this role.
- Every backtest run is logged in MLflow (local): parameters, metrics per fold and artifacts.
- The live system runs in shadow mode: predictions are written before outcomes exist and scored when they arrive.
- Monitoring adds input drift and prediction drift, with an alert rule that opens a GitHub issue.
- An online experiment for acting on the flag is designed (unit, metric, guardrails, power, duration) but not run. Power uses variance estimated from the backfill.

## Amendment 3 (2026-11-03, before any reported result)
Reason: a review of the collected data found three gaps. The training data has no November or December, so holiday behavior is untested. The model sees only views, timing and type, while edit activity in the first two days is already partly fetched and then thrown away. And the plan fixes a single forecast at day 2 without measuring what waiting longer would buy. A trial run on January and February cohorts, with an origin outside this plan, was used only to check that the code works; none of its numbers are reported.

Measured before deciding: the share of logged new pages that still exist today is 92.7% for January 2026 cohorts, 92.8% for February and 93.4% for July, and 93.7% and 89.5% on two sampled 2025 days. Most deletions happen in the first weeks, so older cohorts are not much more affected by survivorship than recent ones.

- Data: cohorts from 2025-01-01 to 2025-12-31 are added, collected the same way as the 2026 backfill. Text is not fetched for them; the content comparison (Amendment 1) stays on 2026 cohorts.
- Splits: rolling origins become monthly from 2025-03-01 to 2026-08-01. Same 30-day label lag, 7-day test windows and 5 seeds. The final holdout is unchanged and still unscored.
- Year-over-year check: models trained only on 2025 cohorts are scored on 2026 cohorts before the holdout, to measure how much accuracy drops a year later.
- Features: number of edits on day 0, number of edits and of distinct editors from t0 to the end of day 1, and page size in bytes at the end of day 0 and day 1. All come from the revision history, which is timestamped, so they are exactly what was known at the end of day 1. Edits made before t0 (in draft space) are not counted.
- The backtests also report LightGBM without the edit features, so the added value of edit activity is measured, not assumed.
- After the core results are in: forecasts updated at day 4 and day 8 with the same models and more days of views, to measure how much accuracy improves by waiting. The day-2 forecast remains the primary result.

## Amendment 4 (2026-11-04, before any reported result)
Reason: a check of the source papers found that the baselines are weaker than they should be for this metric. Szabo and Huberman (2010) recommend the variance correction for errors on the raw scale; it targets the mean on the raw scale, and on the log scale it moves every forecast up by the same amount, away from the fit that log error rewards. Pinto, Almeida and Goncalves (2013) improve on Szabo-Huberman by using the views of each early period separately rather than their total. Separately, new articles can be featured in "Did you know" on the Main Page after day 1 but within the 30 days, which no day-2 forecast can see.

- Baselines added: Szabo-Huberman without the variance correction (log Y = log(views on days 0 and 1) + b, prediction exp of the fitted log), and a Pinto-style linear model of log Y on log day-0 views and log day-1 views with free slopes. The planned Szabo-Huberman stays and is reported.
- Success criteria: the point criterion applies to every baseline, including the two added ones.
- Error analysis: articles featured in "Did you know" are labeled from the Did you know archive pages, which give the UTC time each set left the Main Page. An article counts as featured if its set started on day 2 to day 29 after creation. Errors are reported for featured and other articles separately. The label is never a model input.

## Known threats
- Survivorship in backfilled data: status (deleted, redirected) is checked after the fact. The live collector records status at the end of day 1; the size of the bias is estimated by comparing the two.
- Leakage: no feature may use information after the end of day 1. Training labels respect the 30-day lag above.
- Page renames split views across titles; pages are tracked by page id.
- Bot traffic not caught by the agent=user filter.
- Wikidata links and type in backfilled data are read today, not as of day 1. Same fix as survivorship: compare against the live collector.
