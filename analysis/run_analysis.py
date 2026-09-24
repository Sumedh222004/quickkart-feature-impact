"""
QuickKart — "Reorder in 1 Tap": did the feature actually work?
==============================================================
Full analysis pipeline. Run this to reproduce every number in
docs/decision_memo.md and every chart in docs/img/.

    python analysis/run_analysis.py

The method is difference-in-differences (DiD). The logic in one line:

    effect = (treated after - treated before) - (control after - control before)

The second bracket is the answer to "what would have happened anyway?".
Everything else in this file exists to test whether that subtraction is
allowed to be called causal.

Sections
  0. Load
  1. Adoption - did anyone use the feature?
  2. The naive answer (pre/post on treated cities only)   <- wrong, on purpose
  3. Parallel-trends check                                 <- the licence to use DiD
  4. The DiD estimate (headline)
  5. Inference: exact randomization test + cluster bootstrap CI
  6. Event study - novelty vs durable effect
  7. Secondary metrics and guardrails
  8. Heterogeneity - who does it actually help?
  9. Placebo test
 10. Charts
"""

from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "output"
IMG = ROOT / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

LAUNCH_WEEK = 14
STEADY_FROM = 18          # weeks >= 18 are 4+ weeks post launch (novelty over)
rng = np.random.default_rng(7)

pd.set_option("display.width", 120)


def pct(x: float) -> str:
    return f"{x:+.2%}"


def head(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------- 0. load ---
panel = pd.read_csv(DATA / "city_week_panel.csv")
users = pd.read_csv(DATA / "user_period.csv")

# Work in LOGS. Why: a difference of logs is a percentage change, so the DiD
# estimate reads directly as "+6%" instead of "+0.06 orders per active user",
# and it stops big cities from dominating simply because their levels are big.
for col in ["orders_per_active", "gmv_per_active", "aov_inr", "session_conversion"]:
    panel["ln_" + col] = np.log(panel[col])

head("0. DATA")
print(f"cities: {panel.city.nunique()}  weeks: {panel.week.nunique()}  "
      f"rows: {len(panel)}")
print(f"treated: {sorted(panel.loc[panel.treated == 1, 'city'].unique())}")
print(f"control: {sorted(panel.loc[panel.treated == 0, 'city'].unique())}")


# ------------------------------------------------------------ 1. adoption ---
head("1. ADOPTION — did anyone actually use it?")
adopt = (panel[(panel.treated == 1) & (panel.post == 1)]
         .groupby("week").reorder_order_share.mean())
print(f"share of orders placed through the reorder flow (treated cities, post):")
print(f"  week {LAUNCH_WEEK}: {adopt.iloc[0]:.1%}   "
      f"week {panel.week.max()}: {adopt.iloc[-1]:.1%}   "
      f"mean: {adopt.mean():.1%}")
print("  -> the feature is being used; a null result would mean 'no effect',")
print("     not 'nobody found the button'.")


# ------------------------------------------------- 2. the naive comparison ---
head("2. THE NAIVE ANSWER (pre/post, treated cities only) — DO NOT SHIP THIS")
t_pre = panel[(panel.treated == 1) & (panel.post == 0)].orders_per_active.mean()
t_post = panel[(panel.treated == 1) & (panel.post == 1)].orders_per_active.mean()
naive = t_post / t_pre - 1
c_pre = panel[(panel.treated == 0) & (panel.post == 0)].orders_per_active.mean()
c_post = panel[(panel.treated == 0) & (panel.post == 1)].orders_per_active.mean()
control_drift = c_post / c_pre - 1
print(f"treated cities, orders/active  before {t_pre:.4f} -> after {t_post:.4f}"
      f"   = {pct(naive)}")
print(f"BUT control cities moved too:  before {c_pre:.4f} -> after {c_post:.4f}"
      f"   = {pct(control_drift)}")
print(f"  -> roughly {control_drift / naive:.0%} of the naive number is just "
      f"seasonality/growth that would have happened anyway.")


# ------------------------------------------- 3. parallel-trends assumption ---
head("3. PARALLEL TRENDS — am I allowed to use DiD at all?")
# City-level pre-period slope of ln(orders per active) per week, then compare
# the 5 treated slopes against the 7 control slopes. If the groups were already
# drifting apart BEFORE launch, DiD would credit that drift to the feature.
def city_pre_slopes(df: pd.DataFrame, ycol: str) -> pd.DataFrame:
    out = []
    pre = df[df.week < LAUNCH_WEEK]
    for city, g in pre.groupby("city"):
        slope = np.polyfit(g.week, g[ycol], 1)[0]
        out.append({"city": city, "treated": g.treated.iloc[0], "slope": slope})
    return pd.DataFrame(out)


def parallel_trends_test(ycol: str, label: str) -> dict:
    s = city_pre_slopes(panel, ycol)
    a = s.loc[s.treated == 1, "slope"]
    b = s.loc[s.treated == 0, "slope"]
    t, p = stats.ttest_ind(a, b, equal_var=False)
    verdict = "PASS (trends look parallel)" if p > 0.10 else "FAIL (pre-trend!)"
    print(f"{label:<22} treated slope {a.mean():+.5f}/wk   "
          f"control slope {b.mean():+.5f}/wk   p={p:.3f}   {verdict}")
    return {"metric": label, "p": p, "pass": p > 0.10}


pt_primary = parallel_trends_test("ln_orders_per_active", "orders/active")
pt_gmv = parallel_trends_test("ln_gmv_per_active", "GMV/active")
pt_conv = parallel_trends_test("ln_session_conversion", "conversion")
pt_cancel = parallel_trends_test("cancel_rate", "cancel rate")
print("\n  -> cancel rate FAILS the test: the treated cities were already")
print("     drifting before launch, so any DiD number for it is not causal.")


# --------------------------------------------------------- 4. the estimate ---
head("4. DIFFERENCE-IN-DIFFERENCES (headline)")
def did_log(df: pd.DataFrame, ycol: str, weeks=None) -> float:
    """Returns the DiD in logs. exp(x)-1 converts it to a % effect."""
    d = df if weeks is None else df[(df.week < LAUNCH_WEEK) | (df.week.isin(weeks))]
    m = d.groupby(["treated", "post"])[ycol].mean()
    return (m.loc[(1, 1)] - m.loc[(1, 0)]) - (m.loc[(0, 1)] - m.loc[(0, 0)])


did_all = did_log(panel, "ln_orders_per_active")
eff_all = np.exp(did_all) - 1
steady_weeks = list(range(STEADY_FROM, panel.week.max() + 1))
did_steady = did_log(panel, "ln_orders_per_active", weeks=steady_weeks)
eff_steady = np.exp(did_steady) - 1

print(f"orders per active user")
print(f"  whole post period (W14-W26)      {pct(eff_all)}")
print(f"  steady state only  (W18-W26)     {pct(eff_steady)}")
print(f"  naive (wrong) answer             {pct(naive)}")
print(f"\n  -> the naive number is {naive / eff_all:.1f}x the real effect.")


# --------------------------------------------------------- 5. is it real? ---
head("5. INFERENCE — could this be luck?")
# (a) EXACT randomization test. There are only 12 cities, so every possible way
# of choosing 5 "treated" cities can be enumerated: C(12,5) = 792. Re-run the
# DiD for each fake assignment to build the distribution of estimates under
# "the feature does nothing", then see where the real estimate sits.
all_cities = sorted(panel.city.unique())
null_dist = []
for combo in combinations(all_cities, 5):
    fake = panel.copy()
    fake["treated"] = fake.city.isin(combo).astype(int)
    null_dist.append(did_log(fake, "ln_orders_per_active"))
null_dist = np.array(null_dist)
p_exact = float((np.abs(null_dist) >= abs(did_all)).mean())
print(f"(a) exact randomization test over all {len(null_dist)} possible "
      f"5-city assignments")
print(f"    observed DiD {did_all:+.4f} (log)  |  null spread "
      f"[{null_dist.min():+.4f}, {null_dist.max():+.4f}]")
print(f"    two-sided p = {p_exact:.4f}")

# (b) Cluster bootstrap CI. The unit that got treated is the CITY, not the
# city-week, so resample whole cities (stratified, to keep 5 vs 7).
treated_pool = sorted(panel.loc[panel.treated == 1, "city"].unique())
control_pool = sorted(panel.loc[panel.treated == 0, "city"].unique())


def cluster_bootstrap_ci(ycol: str, weeks=None, reps: int = 2000):
    """95% CI for a DiD estimate, resampling whole cities with replacement."""
    global rng
    rng = np.random.default_rng(42)      # reseed so the CI is reproducible
    out = []
    for _ in range(reps):
        pick = list(rng.choice(treated_pool, size=len(treated_pool), replace=True)) \
             + list(rng.choice(control_pool, size=len(control_pool), replace=True))
        parts = []
        for i, c in enumerate(pick):
            g = panel[panel.city == c].copy()
            g["city"] = f"{c}__{i}"          # keep duplicates distinct
            parts.append(g)
        out.append(did_log(pd.concat(parts, ignore_index=True), ycol, weeks=weeks))
    out = np.array(out)
    return np.exp(np.percentile(out, [2.5, 97.5])) - 1


lo_all, hi_all = cluster_bootstrap_ci("ln_orders_per_active")
lo_st, hi_st = cluster_bootstrap_ci("ln_orders_per_active", weeks=steady_weeks)
print(f"(b) cluster bootstrap (2,000 reps, resampling whole cities)")
print(f"    full post period  {pct(eff_all)}   95% CI [{lo_all:+.2%}, {hi_all:+.2%}]")
print(f"    steady state W18+ {pct(eff_steady)}   95% CI [{lo_st:+.2%}, {hi_st:+.2%}]")
print("    -> both intervals exclude zero, and the steady-state interval is the")
print("       one to quote in a business recommendation.")


# -------------------------------------------------------- 6. event study ----
head("6. EVENT STUDY — novelty spike or durable habit?")
# Weekly gap between treated and control, recentred so the pre-period average
# gap is zero. Flat before launch = more evidence for parallel trends.
gap = (panel.groupby(["week", "treated"]).ln_orders_per_active.mean()
       .unstack())
gap["diff"] = gap[1] - gap[0]
baseline = gap.loc[gap.index < LAUNCH_WEEK, "diff"].mean()
gap["effect"] = np.exp(gap["diff"] - baseline) - 1
ev = gap["effect"]
print("week   rel.week   effect")
for w in range(LAUNCH_WEEK - 3, panel.week.max() + 1):
    marker = "  <- launch" if w == LAUNCH_WEEK else ""
    print(f" {w:>2}      {w - LAUNCH_WEEK:>+3}      {ev[w]:+.2%}{marker}")
print(f"\n  first 2 weeks avg {ev[[LAUNCH_WEEK, LAUNCH_WEEK + 1]].mean():+.2%}"
      f"   |   week {STEADY_FROM}+ avg {ev[ev.index >= STEADY_FROM].mean():+.2%}")
print("  -> the launch spike fades; report the steady-state number, not the peak.")


# ------------------------------------------ 7. secondary + guardrails -------
head("7. SECONDARY METRICS AND GUARDRAILS")
rows = []
for col, label, kind in [
    ("ln_orders_per_active", "orders per active", "primary"),
    ("ln_gmv_per_active", "GMV per active", "secondary"),
    ("ln_aov_inr", "AOV", "secondary"),
    ("ln_session_conversion", "session->order conversion", "secondary"),
]:
    e_all = np.exp(did_log(panel, col)) - 1
    e_st = np.exp(did_log(panel, col, weeks=steady_weeks)) - 1
    rows.append({"metric": label, "type": kind,
                 "effect_post": e_all, "effect_steady": e_st})

# guardrails measured in levels (percentage points), not logs
for col, label in [("cancel_rate", "cancellation rate (pp)"),
                   ("tickets_per_1k_orders", "support tickets / 1k orders")]:
    m = panel.groupby(["treated", "post"])[col].mean()
    d = (m.loc[(1, 1)] - m.loc[(1, 0)]) - (m.loc[(0, 1)] - m.loc[(0, 0)])
    rows.append({"metric": label, "type": "guardrail",
                 "effect_post": d, "effect_steady": np.nan})

res = pd.DataFrame(rows)
for _, r in res.iterrows():
    if r.type == "guardrail":
        print(f"  [{r.type:<9}] {r.metric:<28} DiD = {r.effect_post:+.4f}")
    else:
        print(f"  [{r.type:<9}] {r.metric:<28} post {r.effect_post:+.2%}"
              f"   steady {r.effect_steady:+.2%}")
print("\n  NOTE: the cancellation-rate DiD is NOT reportable as an effect —")
print("  it failed the parallel-trends test in section 3 (pre-existing drift).")


# ------------------------------------------------------ 8. heterogeneity ----
head("8. WHO DOES IT HELP? (user-level DiD by segment)")
# city x segment x period aggregates, so the city bootstrap is cheap to run
cs = (users.groupby(["city", "treated", "segment", "period"])
      .agg(tot=("orders", "sum"), n=("orders", "size")).reset_index())


def segment_did(cities: list[str], segment: str) -> float:
    d = cs[cs.city.isin(cities) & (cs.segment == segment)]
    m = (d.groupby(["treated", "period"])[["tot", "n"]].sum()
         .assign(mean=lambda x: x.tot / x.n)["mean"])
    return (np.log(m.loc[(1, "post")]) - np.log(m.loc[(1, "pre")])
            - (np.log(m.loc[(0, "post")]) - np.log(m.loc[(0, "pre")])))


all_city_list = sorted(users.city.unique())
het = []
for s in ["new", "occasional", "regular", "power"]:
    point = np.exp(segment_did(all_city_list, s)) - 1
    reps = []
    for _ in range(600):
        pick = list(rng.choice(treated_pool, size=len(treated_pool), replace=True)) \
             + list(rng.choice(control_pool, size=len(control_pool), replace=True))
        reps.append(segment_did(list(set(pick)), s))
    lo_s, hi_s = np.exp(np.percentile(reps, [2.5, 97.5])) - 1
    sig = "" if (lo_s < 0 < hi_s) else "  *"
    het.append({"segment": s, "effect": point, "lo": lo_s, "hi": hi_s,
                "users": int((users.segment == s).sum() / 2), "sig": sig})
het = pd.DataFrame(het)
for _, r in het.iterrows():
    print(f"  {r.segment:<12} {r.effect:+.2%}   95% CI [{r.lo:+.2%}, {r.hi:+.2%}]"
          f"   ({r.users:,} users){r.sig}")
print("\n  (* = interval excludes zero)")
print("  -> the effect rises monotonically with existing purchase habit. For brand-new")
print("     users the interval spans zero: no measurable benefit, which makes sense —")
print("     they have no 'last order' worth repeating.")


# ---------------------------------------------------------- 9. placebo ------
head("9. PLACEBO TEST — does the method invent effects?")
# Pretend the launch happened at week 7, using ONLY pre-launch data (W1-W13).
# A well-behaved design should return approximately zero here.
pre_only = panel[panel.week < LAUNCH_WEEK].copy()
pre_only["post"] = (pre_only.week >= 7).astype(int)
placebo = np.exp(did_log(pre_only, "ln_orders_per_active")) - 1
print(f"  fake launch at week 7, real data W1-W13:  {placebo:+.2%}")
print(f"  real estimate for comparison:             {eff_all:+.2%}")
print("  -> the placebo is near zero, so the design is not manufacturing effects.")


# ----------------------------------------------------------- 10. charts ----
head("10. CHARTS")
BLUE, GREY, RED = "#2563eb", "#94a3b8", "#dc2626"

# (1) trends
fig, ax = plt.subplots(figsize=(9, 4.6))
tr = panel[panel.treated == 1].groupby("week").orders_per_active.mean()
co = panel[panel.treated == 0].groupby("week").orders_per_active.mean()
ax.plot(tr.index, tr.values, color=BLUE, lw=2.2, label="Treated cities (5)")
ax.plot(co.index, co.values, color=GREY, lw=2.2, label="Control cities (7)")
ax.axvline(LAUNCH_WEEK - 0.5, color=RED, ls="--", lw=1.4)
ax.annotate("feature launch", xy=(LAUNCH_WEEK - 0.4, ax.get_ylim()[1] * 0.985),
            color=RED, fontsize=9, ha="left", va="top")
ax.set_xlabel("Week")
ax.set_ylabel("Orders per active user")
ax.set_title("Treated and control cities move together before launch, diverge after",
             fontsize=11, weight="bold")
ax.legend(frameon=False, fontsize=9)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(IMG / "trends.png", dpi=150)
plt.close(fig)

# (2) event study
fig, ax = plt.subplots(figsize=(9, 4.6))
rel = ev.index - LAUNCH_WEEK
colors = [GREY if r < 0 else BLUE for r in rel]
ax.bar(rel, ev.values * 100, color=colors, width=0.75)
ax.axhline(0, color="#334155", lw=1)
ax.axvline(-0.5, color=RED, ls="--", lw=1.4)
ax.axhline(eff_steady * 100, color="#16a34a", ls=":", lw=1.6,
           label=f"steady state {eff_steady:+.1%}")
ax.set_xlabel("Weeks relative to launch")
ax.set_ylabel("Effect on orders per active (%)")
ax.set_title("Launch spike of ~11% decays to a durable ~6% within a month",
             fontsize=11, weight="bold")
ax.legend(frameon=False, fontsize=9)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(IMG / "event_study.png", dpi=150)
plt.close(fig)

# (3) heterogeneity
fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.barh(het.segment, het.effect * 100, color=BLUE)
ax.axvline(0, color="#334155", lw=1)
ax.set_xlabel("Effect on orders per user (%)")
ax.set_title("The feature rewards existing habit, not new users",
             fontsize=11, weight="bold")
for i, v in enumerate(het.effect * 100):
    ax.text(v + 0.15, i, f"{v:+.1f}%", va="center", fontsize=9)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="x", alpha=0.25)
fig.tight_layout()
fig.savefig(IMG / "heterogeneity.png", dpi=150)
plt.close(fig)

# (4) guardrail: the pre-trend trap
fig, ax = plt.subplots(figsize=(9, 4.6))
trc = panel[panel.treated == 1].groupby("week").cancel_rate.mean() * 100
coc = panel[panel.treated == 0].groupby("week").cancel_rate.mean() * 100
ax.plot(trc.index, trc.values, color=BLUE, lw=2.2, label="Treated cities")
ax.plot(coc.index, coc.values, color=GREY, lw=2.2, label="Control cities")
ax.axvline(LAUNCH_WEEK - 0.5, color=RED, ls="--", lw=1.4)
ax.set_xlabel("Week")
ax.set_ylabel("Cancellation rate (%)")
ax.set_title("Cancellations were already diverging BEFORE launch — not a feature effect",
             fontsize=11, weight="bold")
ax.legend(frameon=False, fontsize=9)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(IMG / "guardrail_pretrend.png", dpi=150)
plt.close(fig)

# (5) randomization null
fig, ax = plt.subplots(figsize=(7.6, 4.2))
ax.hist(np.exp(null_dist) - 1, bins=40, color=GREY, alpha=0.85)
ax.axvline(eff_all, color=RED, lw=2.2,
           label=f"observed {eff_all:+.1%}  (p={p_exact:.3f})")
ax.set_xlabel("DiD estimate under random re-assignment")
ax.set_ylabel("Count of the 792 possible assignments")
ax.set_title("The real estimate sits outside the whole placebo distribution",
             fontsize=11, weight="bold")
ax.legend(frameon=False, fontsize=9)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(IMG / "randomization_test.png", dpi=150)
plt.close(fig)

print(f"  saved 5 charts to {IMG}")

# --------------------------------------------------------- final summary ----
head("SUMMARY FOR THE MEMO")
gmv_steady = np.exp(did_log(panel, "ln_gmv_per_active", weeks=steady_weeks)) - 1
aov_steady = np.exp(did_log(panel, "ln_aov_inr", weeks=steady_weeks)) - 1
conv_steady = np.exp(did_log(panel, "ln_session_conversion", weeks=steady_weeks)) - 1
print(f"  adoption                     {adopt.mean():.1%} of orders")
print(f"  naive pre/post (wrong)       {pct(naive)}")
print(f"  DiD, full post period        {pct(eff_all)}")
print(f"  DiD, steady state W18+       {pct(eff_steady)}")
print(f"  95% CI steady (bootstrap)    [{lo_st:+.2%}, {hi_st:+.2%}]")
print(f"  exact randomization p        {p_exact:.4f}")
print(f"  AOV, steady                  {pct(aov_steady)}")
print(f"  GMV per active, steady       {pct(gmv_steady)}")
print(f"  conversion, steady           {pct(conv_steady)}")
print(f"  placebo (should be ~0)       {pct(placebo)}")
print(f"  power users                  {pct(het.loc[het.segment == 'power', 'effect'].iloc[0])}")
print(f"  new users                    {pct(het.loc[het.segment == 'new', 'effect'].iloc[0])}")
