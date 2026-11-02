# first48

Can a new Wikipedia article's first two days of views predict its 30-day views, with honest uncertainty, and flag likely high-demand articles early?

Content teams plan promotion, caching and staffing around expected demand. This project builds that forecast on open data: daily pageviews for every new English Wikipedia article.

Status: research and planning. No results yet.

## Approach

- Data: Wikimedia pageviews API plus the MediaWiki creation and move logs (notes/02_data_source.md)
- Baselines: flat-rate extrapolation and the Szabo-Huberman log-linear model
- Models: LightGBM with early-view features, validated with rolling-origin backtests
- Uncertainty: quantile regression with conformal calibration, coverage measured on held-out articles
- Decision: a flag, raised after the first two days, for likely top-5% articles, with precision and recall against a simple rule

The analysis plan, metrics and success criteria are fixed in advance in PLAN.md.

## Repo

- `PLAN.md`: pre-analysis plan
- `notes/`: paper notes and data source notes
- `PROJECT_LOG.md`: progress and decisions
