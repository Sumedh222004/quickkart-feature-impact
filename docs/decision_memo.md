# Decision Memo — "Reorder in 1 Tap"

**To:** Product & Growth · **From:** Analytics · **Date:** Week 27
**Decision requested:** roll out to remaining 7 cities — yes or no?

---

## Recommendation

**Roll it out** — but plan against **+5.6% orders per active user**, not the
+11% the launch dashboards showed, and track **GMV per active (+3.4%)** as the
success metric rather than orders, because the basket shrinks.

## What we measured

The feature went live in 5 cities in week 14; 7 cities did not get it. There was
no randomised test, so impact is measured by **difference-in-differences**: the
change in treated cities minus the change in control cities over the same weeks.
The control group answers "what would have happened anyway".

| | Result |
|---|---|
| **Primary — orders per active user** | **+5.6%** (95% CI +4.1% to +7.2%), p = 0.001 |
| Naive before/after (treated cities only) | +11.4% — **inflated**, about 38% of it is seasonality and growth |
| GMV per active user | **+3.4%** |
| Average order value | **−2.1%** |
| Session → order conversion | +4.9% |
| Adoption | 27.7% of orders in treated cities now use the reorder flow |

## Three things that change the decision

**1. The launch number is not the real number.**
The effect was +11.5% in the first two weeks and settled at +5.6% from week 4
onward. That is novelty, not habit. Forecasting off the launch fortnight would
overstate the annual impact by roughly 2×.

**2. Orders go up, baskets get smaller.**
Reorder baskets repeat staples and skip the browse-driven add-ons, so AOV falls
about 2%. Net effect on GMV per active is **+3.4%**, not +5.6%. The orders
headline oversells the feature by ~40%.
*Action:* add a "frequently added with this" strip to the reorder confirmation
screen and re-measure AOV in four weeks.

**3. It rewards habit; it does nothing for new users.**

| Segment | Effect | 95% CI |
|---|---|---|
| Power | +9.5% | +7.7% to +11.6% |
| Regular | +7.7% | +6.2% to +9.1% |
| Occasional | +4.3% | +1.2% to +7.6% |
| New | −1.9% | −6.0% to +2.8% — **indistinguishable from zero** |

A new user has no "last order" worth repeating. This feature is a retention
lever, not an activation lever; do not put it in the new-user onboarding OKR.

## What we deliberately did not conclude

Cancellation rate rose in the treated cities, and a naive reading blames the
feature. It does not hold up: those cities were **already** drifting upward
before launch (p < 0.001 on the pre-trend test), which points to capacity strain
in the large metros. **This needs its own investigation** — it is not a feature
effect, and it should not block the rollout.

## Confidence

- Treated and control cities moved in parallel before launch (p = 0.54) — the
  assumption DiD depends on holds for the primary metric.
- With only 12 cities, an exact randomisation test was used across all 792
  possible 5-city assignments: the observed effect is larger than every one of
  them (p = 0.001).
- A placebo test on pre-launch data only (fake launch, week 7) returns +0.5%,
  so the method is not manufacturing effects.

**Residual risk:** treated cities were the 5 largest, chosen by product. If
something specific to large metros coincided with week 14, DiD would absorb it.
The remaining rollout should be **randomised across the 7 control cities** so
the next readout doesn't depend on this assumption.

---
*Data is simulated; method and reasoning are real. Numbers reproduce from
`analysis/run_analysis.py`.*
