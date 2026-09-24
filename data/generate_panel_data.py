"""
QuickKart — "Reorder in 1 Tap" Feature Rollout: Synthetic Data Generator
========================================================================
Creates a SIMULATED city x week panel for a quick-commerce app that shipped a
"Reorder in 1 Tap" feature to 5 of its 12 cities. No real company data is used
or implied.

WHY SYNTHETIC: the analysis has to recover a KNOWN answer. Every effect below
is injected on purpose, so the difference-in-differences estimate can be scored
against ground truth. Public datasets cannot do that.

--------------------------------------------------------------------------
THE SETUP
--------------------------------------------------------------------------
    12 cities, 26 weeks (W1-W26).
    Product shipped the feature in 5 cities at the start of WEEK 14.
    The 5 cities were NOT randomly chosen - product picked the largest ones.
    (That is exactly why a naive before/after comparison is unsafe and why
     parallel-trends has to be tested rather than assumed.)

--------------------------------------------------------------------------
GROUND TRUTH INJECTED (what a correct analysis should find)
--------------------------------------------------------------------------
 G1. orders per active user  +6.0% steady state in treated cities post-launch,
                             with a NOVELTY SPIKE: +11% in weeks 1-2, +8% in
                             week 3, settling to +6.0% from week 4 onward.
 G2. AOV                     -2.0% in treated cities post-launch. Reorder
                             baskets repeat staples and skip browse-driven
                             add-ons. So the headline orders number OVERSTATES
                             the value: GMV per active only moves
                             1.060 * 0.980 - 1 = +3.9%.
 G3. session -> order conv.  +4.0% (relative) in treated cities post-launch.
 G4. cancellation rate       NO treatment effect, BUT treated cities have a
                             PRE-EXISTING UPWARD TREND (capacity strain that
                             started before launch). A blind DiD will report a
                             fake "effect" here; the pre-trend test is supposed
                             to catch it and the analyst is supposed to refuse
                             to attribute it.
 G5. support tickets         No effect at all (clean guardrail).
 G6. seasonality             A festive bump in weeks 18-20 lifts ALL cities
                             (+8%). This is what makes naive pre/post wrong.
 G7. heterogeneity           Effect is concentrated in habitual users:
                             power +11%, regular +7%, occasional +3%,
                             new ~+0.5%.
 G8. adoption                In treated cities post-launch, ~28% of orders come
                             through the reorder flow (0 before / in control).

Seed is fixed, so the numbers are reproducible run to run.

Usage:  python generate_panel_data.py
Output: output/city_week_panel.csv, output/user_period.csv, output/rollout.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parent / "output"

N_WEEKS = 26
LAUNCH_WEEK = 14                      # first treated week
PRE_WEEKS = list(range(1, LAUNCH_WEEK))          # 1..13
POST_WEEKS = list(range(LAUNCH_WEEK, N_WEEKS + 1))  # 14..26

# --- cities -----------------------------------------------------------------
# Treated = the 5 largest cities (deliberately non-random assignment).
CITIES = [
    # name,            size_index, treated
    ("Bengaluru",      1.00, 1),
    ("Mumbai",         0.96, 1),
    ("Delhi NCR",      0.94, 1),
    ("Hyderabad",      0.78, 1),
    ("Pune",           0.71, 1),
    ("Chennai",        0.69, 0),
    ("Kolkata",        0.60, 0),
    ("Ahmedabad",      0.52, 0),
    ("Jaipur",         0.41, 0),
    ("Lucknow",        0.34, 0),
    ("Indore",         0.29, 0),
    ("Kochi",          0.25, 0),
]

# --- ground-truth effect sizes ----------------------------------------------
EFF_ORDERS_BY_WEEKS_SINCE = {0: 0.110, 1: 0.110, 2: 0.080}   # novelty decay
EFF_ORDERS_STEADY = 0.060                                     # week 4 onwards
EFF_AOV = -0.020
EFF_CONV = 0.040
REORDER_SHARE_TREATED_POST = 0.28

# --- seasonality (index by week 1..26) --------------------------------------
def seasonality(week: int) -> float:
    """Common demand wave + a festive bump in weeks 18-20 (affects ALL cities)."""
    wave = 1.0 + 0.030 * np.sin(2 * np.pi * (week - 3) / 26.0)
    festive = 1.08 if 18 <= week <= 20 else 1.0
    return wave * festive


def build_city_week_panel() -> pd.DataFrame:
    rows = []
    for name, size, treated in CITIES:
        # city-specific levels
        base_opa = 0.86 + 0.16 * size + rng.normal(0, 0.02)     # orders/active/week
        base_aov = 560 + 130 * size + rng.normal(0, 12)          # Rs
        base_conv = 0.395 + 0.045 * size + rng.normal(0, 0.006)
        base_cancel = 0.020 + 0.006 * size + rng.normal(0, 0.0012)
        base_tickets = 11.0 + 4.0 * size + rng.normal(0, 0.6)    # per 1k orders
        base_actives = int((9_000 + 46_000 * size) * rng.normal(1.0, 0.04))

        # common growth slope (this is what makes PARALLEL TRENDS hold) plus a
        # tiny city-specific wobble so the test is not trivially perfect
        growth = 0.0045 + rng.normal(0, 0.0006)

        for week in range(1, N_WEEKS + 1):
            post = int(week >= LAUNCH_WEEK)
            weeks_since = week - LAUNCH_WEEK
            season = seasonality(week)
            trend = (1 + growth) ** (week - 1)

            # ---- treatment effect on orders per active (G1) ----
            eff_orders = 0.0
            if treated and post:
                eff_orders = EFF_ORDERS_BY_WEEKS_SINCE.get(weeks_since, EFF_ORDERS_STEADY)

            opa = (base_opa * season * trend * (1 + eff_orders)
                   * rng.normal(1.0, 0.022))

            # ---- AOV (G2): small NEGATIVE effect ----
            eff_aov = EFF_AOV if (treated and post) else 0.0
            aov = base_aov * (1 + eff_aov) * (1 + 0.0012 * (week - 1)) * rng.normal(1.0, 0.014)

            # ---- session -> order conversion (G3) ----
            eff_conv = EFF_CONV if (treated and post) else 0.0
            conv = base_conv * season ** 0.3 * (1 + eff_conv) * rng.normal(1.0, 0.018)

            # ---- cancellations (G4): NO effect, but a treated-city PRE-TREND ----
            # capacity strain in the big cities begins in week 1 and keeps rising,
            # entirely independent of the feature.
            pretrend = 0.00022 * (week - 1) if treated else 0.0
            cancel = (base_cancel + pretrend) * rng.normal(1.0, 0.05)

            # ---- support tickets (G5): clean, no effect ----
            tickets = base_tickets * season ** 0.2 * rng.normal(1.0, 0.045)

            # ---- volumes ----
            actives = int(base_actives * trend * season ** 0.5 * rng.normal(1.0, 0.02))
            orders = int(round(actives * opa))
            gmv = int(round(orders * aov))
            sessions = int(round(orders / max(conv, 0.05)))
            reorder_share = (REORDER_SHARE_TREATED_POST * rng.normal(1.0, 0.05)
                             if (treated and post) else 0.0)

            rows.append({
                "city": name,
                "week": week,
                "treated": treated,
                "post": post,
                "launch_week": LAUNCH_WEEK if treated else np.nan,
                "active_users": actives,
                "orders": orders,
                "orders_per_active": round(orders / actives, 5),
                "gmv_inr": gmv,
                "aov_inr": round(gmv / orders, 2),
                "gmv_per_active": round(gmv / actives, 3),
                "sessions": sessions,
                "session_conversion": round(orders / sessions, 5),
                "cancel_rate": round(min(max(cancel, 0.002), 0.2), 5),
                "tickets_per_1k_orders": round(max(tickets, 0.5), 3),
                "reorder_order_share": round(max(reorder_share, 0.0), 4),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# User-level table (G7: who does the feature actually help?)
# One row per user per period (pre / post), so the heterogeneity cut is a
# simple groupby rather than a second simulation.
# ---------------------------------------------------------------------------
SEGMENTS = np.array(["new", "occasional", "regular", "power"])
SEG_MIX = np.array([0.22, 0.34, 0.31, 0.13])
SEG_BASE_ORDERS = {"new": 1.3, "occasional": 3.1, "regular": 7.4, "power": 15.8}
SEG_EFFECT = {"new": 0.005, "occasional": 0.030, "regular": 0.070, "power": 0.110}


def build_user_period(panel: pd.DataFrame) -> pd.DataFrame:
    frames = []
    uid = 1
    for name, size, treated in CITIES:
        n_users = int(2200 * (0.45 + 0.75 * size))
        seg = rng.choice(SEGMENTS, size=n_users, p=SEG_MIX)
        user_ids = np.arange(uid, uid + n_users)
        uid += n_users

        base = np.array([SEG_BASE_ORDERS[s] for s in seg]) * rng.gamma(9, 1 / 9, n_users)
        aov_u = np.array([560 + 130 * size] * n_users) * rng.normal(1.0, 0.12, n_users)

        for period in ("pre", "post"):
            is_post = period == "post"
            lift = np.array([SEG_EFFECT[s] for s in seg]) if (treated and is_post) else 0.0
            # both periods are 13 weeks long; mild common growth + festive in post
            period_factor = 1.045 if is_post else 1.0
            orders = rng.poisson(np.maximum(base * period_factor * (1 + lift), 0.05))
            aov_eff = (1 + EFF_AOV) if (treated and is_post) else 1.0
            gmv = np.round(orders * aov_u * aov_eff).astype(int)

            frames.append(pd.DataFrame({
                "user_id": user_ids,
                "city": name,
                "treated": treated,
                "segment": seg,
                "period": period,
                "orders": orders,
                "gmv_inr": gmv,
            }))
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    panel = build_city_week_panel()
    users = build_user_period(panel)

    rollout = pd.DataFrame([
        {"city": c, "size_index": s, "treated": t,
         "launch_week": LAUNCH_WEEK if t else None,
         "rollout_group": "treatment" if t else "control"}
        for c, s, t in CITIES
    ])

    kw = dict(index=False, lineterminator="\n")
    panel.to_csv(OUT / "city_week_panel.csv", **kw)
    users.to_csv(OUT / "user_period.csv", **kw)
    rollout.to_csv(OUT / "rollout.csv", **kw)

    print("=============== GENERATION SUMMARY ===============")
    print(f"city_week_panel : {len(panel):>7,} rows  "
          f"({panel.city.nunique()} cities x {panel.week.nunique()} weeks)")
    print(f"user_period     : {len(users):>7,} rows  "
          f"({users.user_id.nunique():,} users x 2 periods)")
    print(f"treated cities  : {', '.join(rollout.loc[rollout.treated == 1, 'city'])}")
    print(f"launch week     : {LAUNCH_WEEK}  (pre W1-W13, post W14-W26)")
    print(f"total orders    : {panel.orders.sum():,}")
    print(f"total GMV       : Rs {panel.gmv_inr.sum():,}")
    print("==================================================")
    print("Injected ground truth the analysis must recover:")
    print(f"  orders/active  +{EFF_ORDERS_STEADY:.1%} steady (novelty +11% wks 1-2)")
    print(f"  AOV            {EFF_AOV:+.1%}   ->  GMV/active "
          f"{(1 + EFF_ORDERS_STEADY) * (1 + EFF_AOV) - 1:+.1%}")
    print(f"  conversion     {EFF_CONV:+.1%}")
    print("  cancel_rate     NO effect, but treated cities carry a PRE-TREND")
    print("  tickets         NO effect")


if __name__ == "__main__":
    main()
