# first48

From an article's first 48 hours of Wikipedia pageviews, can we predict its 30-day views with honest uncertainty, and flag likely high-demand articles early?

Status: Phase 0 (research and pre-analysis plan). No data or results yet.

## Data

Daily article pageviews from the Wikimedia pageviews REST API.

## Plan

0. Research and a pre-analysis plan written before any modeling
1. Daily data pipeline into DuckDB with SQL models and data tests
2. Baselines and models with rolling-origin backtests
3. Quantile and conformal prediction intervals with measured coverage
4. Early flag for likely top-5% articles and a Streamlit dashboard
5. Write-up of results vs baselines

See `PROJECT_LOG.md` for progress and decisions.
