# Proposed experiment: acting on the flag

Designed, not run. I can't change what Wikipedia readers see, so this is the test I would run if the flag fed a real product surface, for example a "new and rising" list.

## Question
Does promoting a flagged new article raise its views over the rest of its first month, and what does it cost the articles that aren't promoted?

## Design
- Unit: a flagged article. At the end of its day 1, each flagged article is randomly assigned to promoted or not promoted, 50/50, stratified by article type.
- Primary metric: log(1 + views on days 2 to 29). Days 0 and 1 happen before assignment, so they are left out of the outcome.
- Variance reduction: the forecast is made before assignment, so it is used as a covariate (regression adjustment, the idea behind CUPED). This shrinks the spread of the outcome a lot, see the sample size section.
- Guardrails:
  - views of unflagged new articles created the same days (promotion could just move attention around)
  - reverted edits and protection requests on promoted articles (more readers can mean more vandalism)
  - share of promoted articles later deleted or turned into redirects
- Decision rule: promote flagged articles by default if the 95% interval for the primary metric is above zero and no guardrail moves past its preset limit.

## Sample size
About 5% of new articles are flagged each day. With the spread of the outcome among flagged articles in the backtests, `python -m first48.power` gives the smallest effect the test could detect at a 5% significance level and 80% power, for 2, 4 and 8 weeks of flags. The numbers are in RESULTS.md.

## Duration
Four weeks of assignment, then 28 more days until the last outcome is complete, so about eight weeks from start to readout.

## Risks
- Interference: if the list has a fixed number of slots, promoted articles take attention from each other and from control articles, which breaks the independence the analysis assumes. With a small list, randomizing by day (all flagged articles of a day promoted or not) avoids this at the cost of fewer units.
- Feedback loop: promoted articles get more views, and if they go back into training, later models learn that flagged-looking articles do well partly because they were promoted. Training on control articles only, or adjusting for treatment, keeps the model honest.
- Novelty: readers may click a new list more in its first weeks than later.
