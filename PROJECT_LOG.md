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

Next step
- Pinto, Almeida & Goncalves (2013), then the pre-analysis plan.
