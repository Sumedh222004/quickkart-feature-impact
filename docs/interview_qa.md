# Interview Q&A — causal inference & feature impact

20 questions with strong answers. Lead with the number, then the reasoning.

---

### Walkthrough

**1. Walk me through this project.**
"Product shipped a one-tap reorder feature to 5 of 12 cities with no A/B test,
and leadership wanted to know if it worked. A before/after comparison said
+11%, but control cities that never got the feature also grew — so most of that
was seasonality. I used difference-in-differences and got **+5.6% orders per
active user**, with a 95% CI of +4.1% to +7.2%. Two findings changed the
recommendation: the effect starts at +11% and decays to +6% within a month, so
the launch number is novelty; and AOV falls 2%, so GMV per active only rises
3.4% — the orders headline oversells it by about 40%."

**2. Why difference-in-differences and not just an A/B test?**
"An A/B test would have been better and I'd have asked for one. But the feature
was already shipped city by city — that's the reality of most feature launches.
DiD lets you recover a credible estimate from a staggered rollout by using the
untreated cities as the counterfactual. My recommendation explicitly asks that
the *remaining* rollout be randomised, so the next readout doesn't depend on an
assumption."

**3. Explain DiD to a PM with no stats background.**
"Treated cities went up 11%. Cities that didn't get the feature went up 4% over
the same weeks — that's seasonality, festivals, general growth. So the feature
is worth roughly the difference: about 6%. The control group is my estimate of
what would have happened anyway."

### The assumption

**4. What assumption does DiD rely on, and how did you test it?**
"Parallel trends: without the feature, the gap between the groups would have
stayed constant. Levels can differ — treated cities are the five largest — only
the slopes need to match. I tested it two ways: compared each city's pre-launch
trend (treated +0.0079/week vs control +0.0085/week, p = 0.54), and plotted the
week-by-week gap in an event study, which is flat before launch. The event study
is the stronger evidence because it would catch a non-linear divergence the
slope test could miss."

**5. What if parallel trends had failed?**
"It did fail — for cancellation rate, p < 0.001. The treated cities were
already drifting upward before launch. So I refused to report a causal number
for it and flagged it as a separate capacity investigation. If it had failed for
the *primary* metric I'd have had options: synthetic control to build a weighted
comparison group, matching cities on pre-trends, or reporting a bounded range
instead of a point estimate — but I'd rather say 'I can't answer this with this
design' than hand over a number I don't believe."

**6. Treated cities were the 5 largest — isn't that a problem?**
"It's the main threat, and I say so in the memo. DiD absorbs the level
difference — big cities just order more — but not a shock that hit only large
metros around week 14. Three things make me comfortable: the pre-trends match,
the placebo test returns near zero, and the event study shows nothing happening
until exactly the launch week. What would make me uncomfortable is a
metro-specific event I don't know about, which is precisely why I recommend
randomising the rest of the rollout."

### Inference

**7. Why not just run a regression and use the p-value?**
"Because the unit of treatment is a city and there are only 12 of them. Standard
errors on 312 city-weeks would pretend I have 312 independent observations when
weeks within a city are highly correlated — that's the Bertrand-Duflo-
Mullainathan critique, and it produces false significance. Cluster-robust SEs
fix that asymptotically, but 12 clusters isn't asymptotic."

**8. So what did you use?**
"An exact randomisation test. There are only C(12,5) = 792 ways to pick 5
treated cities, so I computed the DiD for all 792. The real estimate is larger
than every single placebo assignment, giving p = 0.0013 with no distributional
assumptions at all. Then a cluster bootstrap — resampling whole cities — for the
confidence interval."

**9. Why resample cities rather than rows in the bootstrap?**
"The treatment was assigned at city level, so the city is the independent unit.
Resampling rows would break the within-city correlation and give a CI that's far
too narrow. One implementation detail: when a city gets drawn twice I rename the
copies, otherwise pandas collapses them and the CI silently shrinks."

**10. What's your confidence interval and what does it mean?**
"+4.1% to +7.2% on the steady-state effect. In plain terms: if the same rollout
were repeated many times, an interval built this way would contain the true
effect 95% of the time. For planning, I'd budget against the bottom of the
range, not the point estimate."

### Judgment

**11. You have two numbers, +6.7% and +5.6%. Which do you report?**
"+5.6%, the steady state. The full-post number blends in the launch fortnight
when the effect was +11.5% — that's novelty, people trying a new button. If
finance forecasts a year off the launch spike, we miss by roughly 2×. I'd report
the full-post number only for 'what did we actually get last quarter'."

**12. The feature lifted orders. Why isn't that the headline?**
"Because AOV dropped 2%. Reorder baskets repeat staples and skip the
browse-driven add-ons, so GMV per active is only +3.4%. Orders is the metric
that moved; GMV is the metric that pays. I'd track GMV per active as the success
criterion and pair the rollout with an add-on strip on the reorder screen to
claw back the basket size."

**13. What would have made you recommend against rollout?**
"Any of: GMV per active flat or negative — the orders lift would then just be
basket-splitting; a guardrail like cancellations or tickets rising with clean
pre-trends; or an effect concentrated purely in the novelty window with nothing
durable. None of those held, so it ships."

**14. Why does segment heterogeneity matter here?**
"The average hides the decision. Power users +9.5%, regular +7.7%, occasional
+4.3%, and new users' interval spans zero. That reframes the feature: it's a
retention lever, not an activation lever. If someone had put it in a new-user
activation OKR, this analysis stops that."

**15. Your new-user point estimate is −1.9%. Does the feature hurt them?**
"No — and I'm careful not to say that. The 95% CI is −6.0% to +2.8%, so it
includes zero. The honest statement is 'no measurable effect'. Claiming harm
from a point estimate whose interval spans zero is exactly the error I'd expect
an interviewer to be testing for."

### Technique

**16. Why did you run the analysis in logs?**
"So the estimate is a percentage. A difference of logs is a relative change, and
exp(x) − 1 converts back. It also stops the largest cities from dominating the
average just because their absolute numbers are bigger."

**17. What is the placebo test doing?**
"Throwing away all post-launch data and pretending the feature launched at week
7. Nothing happened then, so a trustworthy design should return zero. It
returned +0.5%. If it had returned +4%, my real estimate would be worthless —
it'd mean the method finds effects in noise."

**18. Why check adoption first?**
"So a null result is interpretable. 'No effect' and 'nobody found the button'
look identical in the outcome metric but need completely different responses —
one kills the feature, the other is a discoverability fix. 27.7% of orders went
through the flow, so usage isn't the issue."

**19. How would you extend this with more time?**
"Four things: a synthetic control as a robustness check on the primary estimate;
a longer post window, since 13 weeks measures a quarter not a habit; user-level
DiD with individual fixed effects instead of segment aggregates; and a proper
randomised rollout for the remaining cities so the next readout needs no
assumptions."

**20. What's the weakest part of this analysis?**
"Twelve clusters. The randomisation test is exact, but power is limited — a 2%
effect would have been undetectable, so I can't say much about small guardrail
movements. That's a real constraint of measuring a city-level rollout, and it's
why I'd push for user-level randomisation next time rather than defending the
quasi-experiment forever."

---

## The three numbers to have ready

**+5.6%** steady-state effect (CI +4.1% to +7.2%) · **+3.4%** GMV per active,
because AOV fell 2% · **+11.4%** the naive answer that was wrong.
