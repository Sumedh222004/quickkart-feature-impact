# Methodology — Difference-in-Differences, and why each check exists

Written so you can defend every choice. If an interviewer asks "why did you do
that?", the answer is here.

## 1. The problem

A feature shipped to 5 cities in week 14. We want its causal effect on orders.
Two tempting-but-wrong approaches:

| Wrong approach | Why it fails |
|---|---|
| Treated cities: before vs after | Everything else also changed — seasonality, growth, festive weeks. Gives +11.4% when the truth is +5.6%. |
| Treated vs control cities, after only | The cities differ in level to begin with (treated are the 5 largest). You'd measure "big cities order more", not the feature. |

Each approach controls for one thing and ignores the other. DiD controls for both.

## 2. The estimator

$$\text{DiD} = (\bar Y_{T,\text{post}} - \bar Y_{T,\text{pre}}) - (\bar Y_{C,\text{post}} - \bar Y_{C,\text{pre}})$$

- The **first bracket** is what happened to treated cities — feature *plus*
  everything else.
- The **second bracket** is what happened to control cities — everything else
  *only*.
- Subtracting leaves the feature.

City-level *levels* cancel out in the first difference; common time shocks
cancel in the second. That's the whole trick.

**Why logs.** We run DiD on `ln(metric)`, so the estimate is a difference of
logs = a percentage change, and `exp(x) − 1` converts it back. Two benefits:
the result reads as "+5.6%" rather than "+0.06 orders", and a city with 3× the
volume doesn't dominate the average just because its absolute numbers are bigger.

## 3. The assumption everything rests on: parallel trends

DiD does **not** assume the groups are alike. It assumes that *without the
feature*, the gap between them would have stayed constant.

That's untestable for the post period (we never observe the counterfactual), but
it leaves two testable footprints:

**(a) Pre-launch slopes.** Fit each city's pre-period trend, then compare the 5
treated slopes with the 7 control slopes (Welch t-test on 12 numbers).

| Metric | Treated slope | Control slope | p | Verdict |
|---|---|---|---|---|
| orders/active | +0.00792/wk | +0.00849/wk | 0.535 | pass |
| GMV/active | +0.00960/wk | +0.00971/wk | 0.931 | pass |
| conversion | −0.00017/wk | +0.00056/wk | 0.388 | pass |
| **cancel rate** | **+0.00020/wk** | **+0.00001/wk** | **<0.001** | **FAIL** |

**(b) The event study.** Plot the treated-minus-control gap week by week. Flat
bars before launch = parallel trends holding, one week at a time. This is
stronger evidence than the single t-test because it would expose a *non-linear*
divergence that a slope comparison could miss.

**What failure means.** Cancellation rate fails, so we do not report a causal
number for it. Reporting it anyway would blame the feature for a capacity
problem that started earlier. Knowing when to *refuse* to answer is part of the
job.

## 4. Inference with only 12 units

The treatment was assigned to **cities**, so cities are the independent units —
not the 312 city-weeks. Treating city-weeks as independent would produce
absurdly small standard errors (a classic mistake; see Bertrand, Duflo &
Mullainathan 2004 on serial correlation in DiD).

With 12 clusters, cluster-robust standard errors are unreliable — they're
asymptotic, and 12 is not asymptotic. So:

**Exact randomisation test.** There are only C(12,5) = 792 ways to choose 5
treated cities. Compute the DiD for every one. This is the distribution of
estimates under "the feature does nothing but the assignment was random". The
observed estimate is larger than all 792 → p = 0.0013. No distributional
assumption required at all.

**Cluster bootstrap.** Resample whole cities with replacement (stratified: 5
treated, 7 control), recompute the estimate 2,000 times, take the 2.5th and
97.5th percentiles → 95% CI of **+4.1% to +7.2%**. Resampling whole cities (not
rows) respects the fact that weeks within a city are correlated.

## 5. Which number to report

The effect is not constant over time:

| Window | Estimate | What it means |
|---|---|---|
| Weeks 1–2 post | +11.5% | novelty — people try the new button |
| Weeks 4+ post | **+5.6%** | the durable effect |
| Whole post period | +6.7% | a blend of the two |

**Report the steady state for planning.** The full-post average is defensible
for "what did we get this quarter", but forecasting off the launch spike
overstates the annual number roughly 2×.

## 6. Robustness

| Check | Result | Purpose |
|---|---|---|
| Placebo (fake launch at week 7, pre-data only) | +0.5% | Would the method invent an effect where none exists? No. |
| Adoption check | 27.7% of orders | A null result would be ambiguous if nobody used the feature. They did. |
| Guardrails | tickets flat; cancellations unattributable | A feature can lift its target metric and still hurt the business. |
| Heterogeneity | +9.5% power vs ~0 new | An average hides the decision. |

## 7. Honest limitations

1. **Assignment was not random.** Product picked the 5 largest cities. DiD
   handles their higher *levels*, but not a shock that hit only large metros in
   week 14. Recommendation: randomise the remaining rollout.
2. **12 clusters is few.** The randomisation test is exact, but power is limited
   — a 2% effect would not have been detectable here.
3. **13 weeks post-launch** measures a quarter, not a year. Reorder habits could
   decay further, or compound.
4. **Spillovers are assumed away.** If treated-city users talked about the
   feature to friends in control cities, the control group is contaminated and
   the estimate is conservative.
5. **Simulated data.** Real logs would have tracking gaps, redefined events, and
   users who move between cities.

## 8. If you prefer a regression

The same estimate comes from a two-way fixed-effects regression:

```python
import statsmodels.formula.api as smf
m = smf.ols("ln_orders_per_active ~ treated*post + C(city) + C(week)",
            data=panel).fit(cov_type="cluster",
                            cov_kwds={"groups": panel["city"]})
print(m.params["treated:post"])     # same number as the 2x2 DiD
```

On a balanced panel this is algebraically identical to the four-means
calculation. The 2×2 version is used in this project because it is transparent —
you can see every number that goes into it — and because with 12 clusters the
regression's standard errors are the least trustworthy part of its output, which
is exactly what the randomisation test replaces.

## References worth naming in an interview

- Card & Krueger (1994) — the minimum-wage study that made DiD famous.
- Bertrand, Duflo & Mullainathan (2004) — why DiD standard errors are usually wrong.
- Angrist & Pischke, *Mostly Harmless Econometrics* — the standard reference.
