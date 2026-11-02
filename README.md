# first48

Cold-start demand forecasting: how well can we predict demand for brand new content, and how much do the first two days of traffic add beyond what we know at launch?

Content teams plan promotion, caching and staffing around expected demand, often before there is any history. New English Wikipedia articles are the open testbed: every one has a public creation time, public text and public daily pageviews.

Status: research and planning. No results yet.

## Approach

- Data: Wikimedia pageviews API plus the MediaWiki creation and move logs (notes/02_data_source.md)
- Baselines: flat-rate extrapolation and the Szabo-Huberman log-linear model
- Models: content-only (text at creation), early-signal and combined LightGBM models, validated with rolling-origin backtests
- Uncertainty: quantile regression with conformal calibration, coverage measured on held-out articles
- Decision: a flag, raised after the first two days, for likely top-5% articles, with precision and recall against a simple rule

The analysis plan, metrics and success criteria are fixed in advance in PLAN.md.

## Repo

- `PLAN.md`: pre-analysis plan
- `notes/`: paper notes and data source notes
- `PROJECT_LOG.md`: progress and decisions
