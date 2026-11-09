# Pinto, Almeida & Goncalves (2013): Using Early View Patterns to Predict the Popularity of YouTube Videos

Citation: H. Pinto, J. M. Almeida and M. A. Goncalves, WSDM 2013, pages 365-374. DOI 10.1145/2433396.2433443 (confirmed on Crossref).
Status: bibliographic details confirmed. The model forms below follow the restatement in Trzcinski & Rokita (arXiv:1510.06223); the original full text is still to be read.

## The idea
Szabo & Huberman use one number, the cumulative views at t_i. Pinto et al. use the whole early trajectory: the views gained in each sampling interval up to t_i.

## Models
- ML (multivariate linear): N(t_r) is predicted as a weighted sum of the view increments in each early interval, with one learned weight per interval. Two items with the same total but a different shape (rising vs fading) get different forecasts.
- MRBF: ML plus Gaussian radial basis function terms that measure how similar an item's early trajectory is to a set of example trajectories from the training data. Fitted with ridge regression.

## Claims to verify in the original
- Error metric (believed to be mean relative squared error).
- Size of the improvement over Szabo & Huberman. A secondary source reports roughly 20% lower error for MRBF; not confirmed.

## How our baseline differs
Trzcinski & Rokita write the ML model as N(t_r) = sum over i of a_i * (N(t_i) - N(t_(i-1))): raw view increments, no intercept. Our `pinto_style` baseline (Amendment 4) regresses log(1 + Y) on log(1 + day-0 views) and log(1 + day-1 views), with an intercept. It keeps the idea of one weight per early period and moves it to the log scale, which is the scale our metric uses. It is an adaptation, not a reimplementation, and is described that way in the README and readout. The MRBF variant was not built.

## What it means for us
- With daily data and a two-day window we only have two increments (day 0 partial, day 1). The ratio of day 1 to day 0, adjusted for creation hour, is our version of "shape".
- That is thin. Other early signals (edits, links in from other pages, whether the topic is in the news, Wikidata type) will probably matter more than shape alone.
