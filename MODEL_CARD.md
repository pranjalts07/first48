# Model card

## What it does
For a new English Wikipedia article, forecasts total views over its first 30 days from what is known by the end of its first full day, gives an 80% range, and flags the articles most likely to end up in the top 5% of their week.

## Model
- Point forecast: LightGBM with an L1 loss on log(1 + 30-day views), so it predicts the median. Average of 5 seeds.
- Range: LightGBM 10% and 90% quantile models, widened or narrowed by a conformal adjustment computed on the latest 14 days of labeled cohorts (conformalized quantile regression).
- Flag: the top 5% of each creation day's articles by forecast.

## Inputs
Views on day 0 and day 1, hours of day 0 after creation, weekday, whether the page was created directly or moved in from draft, article type from Wikidata, and edit activity from creation to the end of day 1 (number of edits, number of editors, page size). Nothing known after the end of day 1 is used, except the article type caveat below.

## Data
New articles created from 2025-01-01 to 2026-09-30, collected after the fact from the Wikimedia pageviews API and the MediaWiki logs. Live cohorts from 2026-10-31 on are collected daily and used for shadow mode only.

## Evaluation
Rolling-origin backtests and a final holdout of the last 6 weeks, scored once. All numbers, with the command behind each, are in RESULTS.md. On the holdout (23,199 articles, August 20 to September 30, 2026):
- Median absolute log error 0.392, a typical miss of a factor of 1.48. The best baseline, a Pinto-style model, scored 0.541.
- 80% ranges covered 83.6% overall, but only 75.5% of articles with 100 or more day-1 views.
- At the recall of ranking by day-1 views, 70.2% of flagged articles were in the top 5%, against 62.2% for that ranking.
- Error is highest for sports events (0.563) and film or TV (0.527), and lowest for places (0.290).

## Intended use
Planning and ranking: deciding which new articles deserve early attention, such as review, caching or promotion. Forecasts are for groups of articles and for ranking, not exact counts for a single article.

## Not intended for
- Judging an article's quality or importance. Views measure attention, not value.
- Other language editions or other kinds of pages, which were not tested.

## Known limitations
- Backfilled data only includes pages that still exist, and their Wikidata type was read in November 2026, not at day 1. Live data records both at day 1, so the gap can be measured as live outcomes arrive.
- About 7% of backfilled articles were renamed later. Their views were fetched under the current title, so views under the old title are missing.
- Bot traffic that the pageviews API does not label as automated is counted as human.
- Scheduled runs can start hours late, so "end of day 1" state is really a few hours after.
- Only one November and December (2025) is in the data, so holiday behavior rests on a single year.
- Ranges are too narrow for the busiest articles: treat the upper end of the range as soft for articles with 100 or more day-1 views.
- A Main Page feature after day 1 cannot be foreseen. The few articles featured that way (257 in the backtests) are missed by a factor of about 38 at the median.

## Monitoring
The daily job compares each new cohort's day-1 views and forecasts with the training distribution (population stability index) and, once outcomes arrive, checks how often the 80% range held. An alert on the newest cohort opens a GitHub issue: PSI above 0.25, or coverage outside 70% to 90%.

## Retraining
Retrain monthly on every cohort whose 30-day views are complete, and also after an alert that isn't explained by a data problem. A retrained model replaces the current one only if it is at least as good on the latest month of cohorts, scored the same way as the backtests. Monthly is a cautious choice: a model trained only on 2025 lost just 0.006 in median log error on 2026 articles against monthly retraining.
