# Readout: forecasting demand for new articles

For: a content or product lead deciding whether to use the forecast. Every number below is in RESULTS.md with the command that produced it.

## Bottom line
Two days after an article goes up, the model predicts its first-month readership better than every baseline drawn from published research, and its top-5% list is right more often than today's practice of ranking by yesterday's views. I recommend using the list as a suggestion for early attention decisions while it finishes its shadow run. It is not ready to drive decisions on its own: two launch criteria are not met yet.

## What we found
Tested once on 23,199 articles created from August 20 to September 30, 2026, which the model never saw during development:

- **Accurate enough to plan with.** A typical forecast is off by a factor of 1.48. The strongest baseline, adapted from published work, is off by 1.72, and extending yesterday's views is off by 2.75. Summed over all holdout articles, the forecasts missed by 29.9 million views in total, against 32.7 million for the closest baseline on that measure.
- **A better daily list.** Of the articles it flags as likely top 5%, 70% get there, against 62% for ranking by yesterday's views at the same coverage. On a typical day of about 550 new articles and 27 flags, that is roughly 2 more correct picks.
- **Consistent.** It beat every baseline in all 18 monthly backtests from March 2025 to August 2026, and in every article type. It is least accurate for sports events and films or TV, and most accurate for places.
- **Stable over time.** A version trained only on 2025 was almost as accurate on 2026 articles as one retrained every month, so monthly retraining is a safety margin, not a necessity.
- **Early readership beats content.** The article text alone gives much weaker forecasts (off by a factor of 1.84) than the first two days of views. Text adds a little on top of views.

## Where it falls short
- **Ranges for the biggest articles are too narrow.** The 80% ranges held for 83.6% of articles overall, just outside the planned 77% to 83%, but for only 75.5% of articles with 100 or more views on day 1. Upper estimates for the most popular new articles should be treated as soft.
- **Main Page features cannot be predicted.** About 1 in 270 new articles is featured on Wikipedia's front page after day 1, and those are badly underpredicted. No day-2 forecast can see that coming.
- **Not yet proven live.** Live forecasting started this week. The design doc requires 30 days of shadow forecasts scored against real outcomes before launch; the first outcomes arrive around December 1.

## Recommendation
1. Keep the model in shadow mode until 30 days of live forecasts are scored, around early January. Launch only if live error stays within the backtest range.
2. Meanwhile, give editors the daily top-5% list as a suggestion, not an automatic rule, and show wider uncertainty for articles with 100 or more day-1 views.
3. Before promoting articles because of the list, run the experiment in EXPERIMENT.md. Four weeks of randomized promotion would detect a lift of about 21% in later views; eight weeks would detect about 14%.

## Risks
- **Feedback loop.** If promoted articles go back into training, the model learns partly from its own choices. The experiment keeps a control group for this.
- **Wikipedia is not every platform.** There is no personalized feed here. The method transfers; the exact numbers may not.
- **Data gaps.** Backfilled data only includes articles that still exist, and about 7% were renamed. Live collection records both at day 1, so the gap can be measured as it arrives.

## Next steps
- Score the first live cohorts around December 1 and compare shadow error with the backtests.
- Measure how much accuracy improves by waiting until day 4 or day 8 (planned in Amendment 3).
- Test a separate range adjustment for articles with high day-1 views on the backtests, before changing anything live.
