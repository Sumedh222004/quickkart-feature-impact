# Resume Bullets

Numbers are reproducible from `analysis/run_analysis.py`. Keep only what you can
defend — `interview_qa.md` has the defences.

**Honesty rule:** the title says "simulated" once, visibly. Never imply this was
real company data. "I engineered a dataset with known ground truth, then had to
recover it" is a stronger answer than a vague public CSV.

---

## A. Compact (2 lines)

> **Feature Impact Measurement without A/B Testing (simulated quick-commerce data)** — Python, causal inference
> Estimated the causal effect of a staggered city rollout using difference-in-differences with parallel-trends testing, an exact randomisation test across all 792 possible assignments, and a cluster bootstrap; showed the naive before/after read (+11.4%) was ~2× the true effect (+5.6%), and that a 2% AOV decline cut the real GMV gain to +3.4%.

## B. Standard (3 bullets)

**Feature Impact & Causal Inference — "Reorder in 1 Tap" (simulated quick-commerce platform)**
*Python (pandas, NumPy, SciPy, matplotlib) · [GitHub link]*

- Measured the causal impact of a feature rolled out to 5 of 12 cities **with no A/B test**, using **difference-in-differences** on a 26-week panel; validated the parallel-trends assumption via city-level pre-trend tests and an event study, and established significance with an **exact randomisation test over all 792 possible treatment assignments** (p = 0.001) plus a cluster bootstrap CI.
- Showed the naive before/after read of **+11.4% was ~2× inflated** by seasonality; the true effect was **+5.6% orders per active user** (95% CI +4.1% to +7.2%), decaying from a +11.5% novelty spike — and that a **−2.1% AOV** shift reduced the real gain to **+3.4% GMV per active**, reframing the success metric.
- Flagged a cancellation-rate movement as **non-attributable** after it failed the pre-trend test, and used segment-level DiD to show the feature is a retention lever (power users +9.5%) with **no measurable effect on new users** — changing the rollout plan and preventing a misattributed activation target.

## C. One-bullet version (if space is tight)

- Estimated feature impact from a non-randomised city rollout using **difference-in-differences** with parallel-trends validation, randomisation inference and cluster bootstrap — correcting a naive **+11.4%** read to a true **+5.6%** (CI +4.1–7.2%) and surfacing a 2% AOV offset that halved the business case.

---

## Skills line this justifies

`Causal inference (difference-in-differences, event studies, placebo tests, randomisation inference, cluster bootstrap) · Python (pandas, NumPy, SciPy) · Experimentation & quasi-experiments · Product metrics · Analytical communication (decision memos)`

## Claim → proof map

| Claim | Where it's proven |
|---|---|
| +5.6% (CI +4.1–7.2%), p = 0.001 | `run_analysis.py` §4–5 · memo |
| naive +11.4%, ~2× inflated | §2 |
| novelty +11.5% → +5.6% | §6 event study |
| AOV −2.1% → GMV +3.4% | §7 |
| cancellations non-attributable | §3 pre-trend test, §7 note |
| power +9.5%, new users ~0 | §8 with bootstrap CIs |
| placebo +0.5% | §9 |

## How this differs from your other projects

Say this if asked why you have several analytics projects:

- **Blinkit project** — descriptive and diagnostic: what happened across the
  funnel, cohorts and stores.
- **Promotion framing project** — randomised experimentation: designing a test.
- **This project** — causal inference when randomisation *wasn't* possible.

Three different questions, three different toolkits.
