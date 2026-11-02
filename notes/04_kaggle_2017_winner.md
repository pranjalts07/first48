# Why the 2017 Kaggle Web Traffic winner won

Source: github.com/Arturus/kaggle-web-traffic (MIT), mainly how_it_works.md. Read, not run (TensorFlow 1, needs cuDNN).

## Their task vs ours
They forecast the next ~2 months for ~145K existing pages with up to ~2 years of history each. We forecast brand new pages with 2 days of history. So the parts of their model built for long history (year-ago and quarter-ago lags, the RNN encoder) don't carry over.

## What won
- Seq2seq GRU on log1p(views), each series normalized on its own.
- Page popularity (median views) added back as a feature, since normalizing removes scale.
- Lagged values from a year, half-year and quarter ago as features. This beat their own complex attention mechanism and allowed a much shorter encoder.
- Variance reduction: 3 seeds x 10 checkpoints, averaged, plus averaged weights (ASGD). Their single models were very noisy.
- Smoothed SMAPE as the loss, because plain SMAPE is unstable near zero. They note MAE on log1p is close enough for training.

## Validation lesson
A random (side-by-side) split gave validation scores that tracked training scores and said almost nothing about future performance. Only a walk-forward split was useful. This is why our splits are by creation date.

## Dead ends they reported
- Complex learned attention: replaced by plain lag features, which did slightly better.
- Activation stability regularization: no effect.
- Hyperparameter search: no clear best setting. Many configs scored about the same, so the limit was the noise in the data, not the model.

## What I take from it
1. Work on log1p scale; MAE on log1p is a reasonable loss and matches our primary metric.
2. Simple, well-chosen features beat clever architecture.
3. Time-based validation only.
4. Average over seeds before claiming one model beats another.
5. Keep page scale as a feature (for us: day-0 and day-1 views themselves, not just their ratio).
