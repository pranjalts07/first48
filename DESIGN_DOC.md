# Design doc: early demand forecast for new content

Status: draft, 2026-11-02. Analysis details are in PLAN.md.

## Problem
A content platform publishes hundreds of new items a day. Promotion slots, cache space and moderation time are planned before anyone knows which items will be read. Today that is done by looking at what is getting views right now, which misses slow starters and overreacts to short spikes.

New English Wikipedia articles stand in for that platform: public creation times, public text and public daily views.

## Users and decision
- Editors choosing what to promote: a daily list of new items likely to be in the top 5% of 30-day views.
- Capacity planning: expected total views for the day's new items, with a range.
The forecast is produced once per item, after its first two days.

## Success metrics
- Primary: median absolute log error of the 30-day forecast, compared with three baselines: the current practice (rank by yesterday's views), flat-rate extrapolation and a published log-linear model.
- Ranges: share of items whose 30-day views fall inside the 80% range.
- Flag: precision and recall for the top-5% list.

## Guardrails
- 80% ranges cover 77 to 83% of items, overall and within each article type.
- No article type where the model is worse than the flat-rate baseline.
- The daily run finishes and passes its data checks; a broken run fails visibly.

## Launch criteria
1. Meets the PLAN.md success criteria on the final holdout.
2. Runs in shadow mode for at least 30 days: predictions are logged before outcomes exist and scored when they arrive. Shadow error must fall within the backtest confidence interval.
3. Monitoring and alerts are in place.

## Monitoring
- Accuracy and range coverage of shadow predictions, by week.
- Input drift: feature distributions of each new cohort compared with the training cohorts.
- Prediction drift: distribution of predicted 30-day views over time.
- An alert opens a GitHub issue when coverage or error crosses a set threshold.
- Retraining policy: RETRAINING.md.

## Risks
- Survivorship in backfilled data (page state read after the fact). Measured against live snapshots.
- Leakage through features or labels that are not available after day 1.
- Feedback loop: if promotion follows the flag, promoted items get more views, and future training data partly reflects the model's own choices. Hold out a random share of items from promotion if this were deployed.
- Bot traffic not caught by the pageviews filter.
- Wikipedia may not behave like a commercial platform; results are evidence, not proof, for other settings.
