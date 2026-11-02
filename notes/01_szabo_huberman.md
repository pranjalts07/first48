# Szabo & Huberman (2010): Predicting the Popularity of Online Content

Citation: G. Szabo and B. A. Huberman, "Predicting the Popularity of Online Content", Communications of the ACM 53(8), 2010. Preprint: arXiv:0811.0405 (Nov 2008).
Checked against the arXiv full text on 2026-11-01. Journal volume and issue still to confirm on the ACM page.

## Problem
Predict an item's popularity at a later reference time t_r (30 days) from its popularity at an early indicator time t_i.

## Data
- Digg: front-page stories, Jul to Dec 2007. Train 10,825, test 6,272 stories.
- YouTube: 7,146 videos from "recently added", daily view counts from Apr 2008. Split 50/50 at random.
- Digg age measured in "digg hours" (volume of site activity) instead of clock hours, to remove the day/night cycle.

## Key finding
log N(t_r) is close to linear in log N(t_i) with slope 1.
- Digg: correlation about 0.98 by digg hour 5.
- YouTube: correlation about 0.92 at day 5 on the log scale, about 0.70 without the log.

## Models
- LN: ln N(t_r) = ln N(t_i) + b0 + noise. Back-transform with exp(ln N(t_i) + b0 + s^2 / 2).
- CS (constant scaling): N(t_r) = a * N(t_i), with a chosen to minimize relative squared error.
- GP (growth profile): divide N(t_i) by the average fraction of final views reached by t_i.

## Assumptions
- Noise is additive on the log scale, roughly normal, roughly constant variance.
- Every item shares the same growth shape; only the scale differs.

## Limitations (stated or worth noting)
- Residuals are right-skewed; normality is rejected by formal tests.
- A slow-growing Digg cluster (about 11%) was removed before modeling.
- Slower-decaying content (YouTube) needs a much longer indicator window.

## How we use it
Baseline: log-linear model with slope 1, using total views over days 0 and 1 to predict total views over days 0 to 29.
