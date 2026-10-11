# Code Walkthrough 

Read this next to `notebooks/feature_impact_analysis.ipynb`. The goal is that
you can rebuild the analysis from memory and defend any line of it.

None of this needs advanced Python. The hardest idea is `groupby` + subtraction.

---

## Setup

```python
LAUNCH_WEEK = 14
STEADY_FROM = 18
```
Two constants, so no "magic numbers" are buried in the code later. `STEADY_FROM`
is week 18 because that's 4 weeks after launch — by then the novelty spike has
faded (section 6 proves it rather than assuming it).

## Loading, and the log transform

```python
for col in [...]:
    panel["ln_" + col] = np.log(panel[col])
```
Creates a log version of each metric. **Why:** subtracting two logs gives a
percentage change. `ln(1.06) − ln(1.00) ≈ 0.058`, and `exp(0.058) − 1 = 6%`.
So the DiD result reads directly as a percentage, and big cities don't dominate
the average through sheer size.

*Interview line:* "I estimate in logs so the coefficient is a relative effect
and the metric's scale doesn't drive the weighting."

## 1 — Adoption

```python
panel[(panel.treated == 1) & (panel.post == 1)].groupby("week").reorder_order_share.mean()
```
Filters to treated cities after launch and averages the share of orders using
the reorder flow, per week.

**Why first:** if the effect came out zero, you must know whether that means
"the feature doesn't help" or "nobody found it". Those need different responses.

## 2 — The naive comparison

```python
t_pre  = panel[(panel.treated == 1) & (panel.post == 0)].orders_per_active.mean()
t_post = panel[(panel.treated == 1) & (panel.post == 1)].orders_per_active.mean()
naive  = t_post / t_pre - 1
```
Four filters and a ratio: the before/after change in treated cities. Then the
same for control cities, which never got the feature — yet still grew. That gap
is what the naive analysis wrongly credits to the feature.

**Why include a wrong answer on purpose:** it quantifies the bias (+11.4% vs
+5.6%) and it's the single clearest way to explain to a PM why you didn't just
"look at the before and after".

## 3 — Parallel trends

```python
np.polyfit(g.week, g[ycol], 1)[0]
```
Fits a straight line through one city's pre-launch weeks and takes the slope
(`[0]` = the gradient; `[1]` would be the intercept). Run per city, you get 12
slopes.

```python
stats.ttest_ind(a, b, equal_var=False)
```
Welch's t-test: were the 5 treated slopes systematically different from the 7
control slopes *before* anything happened? `equal_var=False` because the two
groups have different sizes and no reason to share a variance.

**How to read it:** a high p-value is *good news* here — it means we cannot
detect a pre-existing divergence, so DiD is defensible. This is the one place
where failing to reject is what you want.

**The catch to point out:** cancel rate returns p < 0.001. The treated cities
were already drifting. So we refuse to report a causal number for it.

## 4 — The estimate

```python
def did_log(df, ycol, weeks=None):
    d = df if weeks is None else df[(df.week < LAUNCH_WEEK) | (df.week.isin(weeks))]
    m = d.groupby(["treated", "post"])[ycol].mean()
    return (m.loc[(1, 1)] - m.loc[(1, 0)]) - (m.loc[(0, 1)] - m.loc[(0, 0)])
```

Line by line:
- `groupby(["treated","post"]).mean()` produces exactly **four numbers**:
  treated-before, treated-after, control-before, control-after.
- `m.loc[(1, 1)]` reads "treated = 1, post = 1" → treated after.
- The return line is the DiD formula, literally.
- `weeks=` lets you restrict which post weeks count (used for steady state). The
  pre-period is always kept — it's the baseline for both groups.

That function is the entire method. Everything else validates it.

## 5a — Exact randomisation test

```python
for combo in combinations(all_cities, 5):
    fake = panel.copy()
    fake["treated"] = fake.city.isin(combo).astype(int)
    null_dist.append(did_log(fake, "ln_orders_per_active"))
```
`combinations(all_cities, 5)` enumerates every way to choose 5 cities out of 12
— 792 of them. For each, pretend *those* were treated and recompute the DiD.
Because the feature only really launched in one specific set, the other 791 are
placebos.

```python
p_exact = (np.abs(null_dist) >= abs(observed)).mean()
```
The fraction of placebo estimates at least as extreme as the real one. That
fraction *is* the p-value — no normal distribution assumed anywhere.

**Why this instead of a regression p-value:** standard errors rely on having
many independent units. We have 12. With 792 possible assignments we can test
all of them exactly, so we do.

## 5b — Cluster bootstrap

```python
pick = (list(rng.choice(treated_pool, len(treated_pool), replace=True)) +
        list(rng.choice(control_pool, len(control_pool), replace=True)))
```
Draw 5 treated cities (with replacement, so a city can appear twice) and 7
control cities. Stratifying keeps the 5/7 design intact.

```python
g["city"] = f"{c}__{i}"
```
Renames duplicate draws so pandas treats two copies of Mumbai as two separate
cities. Without this the duplicate silently collapses and the CI comes out too
narrow.

```python
np.exp(np.percentile(out, [2.5, 97.5])) - 1
```
The middle 95% of the 2,000 re-estimates, converted from logs to percentages.

**Why resample cities, not rows:** the feature was given to a city. Weeks inside
a city are correlated with each other, so they aren't 2,000 independent
observations — they're 12.

## 6 — Event study

```python
gap = panel.groupby(["week","treated"]).ln_orders_per_active.mean().unstack()
gap["diff"] = gap[1] - gap[0]
baseline = gap.loc[gap.index < LAUNCH_WEEK, "diff"].mean()
gap["effect"] = np.exp(gap["diff"] - baseline) - 1
```
- `unstack()` turns the treated flag into columns, so each row is a week with a
  treated mean and a control mean side by side.
- `diff` is the weekly gap between the groups.
- `baseline` is the average gap *before* launch — the groups start at different
  levels, and that's fine; we subtract it so the pre-period sits at zero.
- Result: the effect, week by week.

**What it shows:** pre-launch bars near zero (parallel trends, visually), a
+11–12% spike at launch, decaying to ~+5.6%. That decay is why you never
promise the launch number.

## 7 — Guardrails

Same `did_log` for money metrics; for rates (cancellations, tickets) the DiD is
computed in **levels**, giving percentage *points*, because a percentage change
of a percentage is confusing to read.

**The insight to lead with:** orders +5.6% but AOV −2.1%, so GMV per active is
only +3.4%. A feature can lift the metric you were watching while delivering
less than half the value you announced.

## 8 — Heterogeneity

```python
cs = users.groupby(["city","treated","segment","period"]).agg(tot=..., n=...)
```
Pre-aggregates to city × segment × period, so the bootstrap can be rerun 300
times without touching 48,000 raw rows each time — a small optimisation that
keeps the notebook fast in Colab.

```python
m = d.groupby(["treated","period"])[["tot","n"]].sum().assign(mean=lambda x: x.tot / x.n)
```
Sums first, then divides — so the mean is properly weighted by how many users
each city contributes, instead of averaging city averages.

**The finding that matters:** the new-user confidence interval spans zero.
Don't say "the feature hurts new users" (the point estimate is negative but the
interval includes zero); say "no measurable effect for new users".

## 9 — Placebo

```python
pre_only = panel[panel.week < LAUNCH_WEEK].copy()
pre_only["post"] = (pre_only.week >= 7).astype(int)
```
Throws away all post-launch data and invents a launch at week 7. Nothing
happened then, so the estimate should be ~0. It returns +0.5%.

**Why it matters:** it proves the pipeline doesn't produce effects from noise.
If the placebo had come back at +4%, the real estimate would be worthless.

---

## The five questions this code answers, in order

1. Did anyone use it? → adoption
2. What's the naive answer, and how wrong is it? → section 2
3. Am I allowed to use this method? → parallel trends
4. What's the effect? → DiD
5. Could it be chance / is it durable / does it harm anything / who does it
   help? → sections 5–8

If you can recite that list, you can rebuild the project.
