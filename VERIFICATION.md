# VERIFICATION.md — check the project works, step by step

Two ways to run it. **Stage 1 (local script) is the fastest full check** — one
command prints every number and saves every chart. **Stage 2 (Colab notebook)**
verifies the thing you'll actually learn from and show people.

Numbers below are exact, because the data is seeded — with one exception noted
in Stage 1.6.

---

## Stage 0 — What you need

Python (you already installed it for the Blinkit project). Nothing else — no
database, no SQL Server, no Power BI.

Unzip `quickkart-feature-impact.zip` to `C:\projects\` so you have
`C:\projects\quickkart-feature-impact\` containing `data`, `analysis`,
`notebooks`, `docs`.

⚠️ Check for the double-folder problem you hit last time: if you see
`C:\projects\quickkart-feature-impact\quickkart-feature-impact\`, the inner one
is the real project folder — use that path everywhere below.

---

## Stage 1 — Run the analysis script (5 minutes)

### 1.1 Open a command window in the project folder
Open the project folder in File Explorer → click the **address bar** → type
`cmd` → Enter.

### 1.2 Install the libraries
```
pip install -r requirements.txt
```
**Gate:** finishes without red errors. (numpy and pandas you already have; scipy
and matplotlib may install now.)

### 1.3 Run it
```
python analysis/run_analysis.py
```
Takes about 20–30 seconds.

### 1.4 Gate — the data section
```
cities: 12  weeks: 26  rows: 312
treated: ['Bengaluru', 'Delhi NCR', 'Hyderabad', 'Mumbai', 'Pune']
```

### 1.5 Gate — the core numbers
Check these against your screen:

| Section | Expected |
|---|---|
| 1. Adoption | mean **27.7%** of orders use the reorder flow |
| 2. Naive answer | treated **+11.36%**, control **+4.32%** |
| 3. Parallel trends | orders/active **p=0.535 PASS** · GMV **p=0.931 PASS** · conversion **p=0.388 PASS** · cancel rate **p=0.000 FAIL** |
| 4. DiD | full post **+6.70%** · steady state **+5.61%** |
| 5a. Randomization | 792 assignments, observed **+0.0648**, **p = 0.0013** |
| 6. Event study | first 2 weeks **+11.48%** · week 18+ **+5.62%** |
| 7. Secondary | GMV/active **+3.43%** · AOV **−2.07%** · conversion **+4.90%** |
| 8. Heterogeneity | new **−1.94%** · occasional **+4.28%** · regular **+7.70%** · power **+9.53%** |
| 9. Placebo | **+0.54%** (near zero = good) |

The single most important line is **section 3**: three PASS and one FAIL. That
FAIL is deliberate — it's the pre-trend trap the analysis is designed to catch.

### 1.6 The one number that moves between runs
The **bootstrap confidence intervals** (section 5b and section 8) are built by
random resampling, so they shift by a tenth of a percentage point or two between
runs and differ slightly between the script and the notebook. Expect the
steady-state CI around **[+4.1%, +7.2%]**. That wobble is the method working
normally, not a bug — everything else is fixed by the seed.

### 1.7 Gate — the charts
Open `docs\img\`. Five PNGs, all freshly timestamped:
`trends.png` · `event_study.png` · `guardrail_pretrend.png` ·
`heterogeneity.png` · `randomization_test.png`

Open `event_study.png`: grey bars hovering near zero before launch, a tall blue
bar (~12%) at launch, decaying toward the green dotted line (~5.6%).
Open `guardrail_pretrend.png`: the blue line is already climbing *before* the
red dashed launch line — that's the trap, visible.

**If Stage 1 passes, the project works.** Stage 2 is about being able to show and
explain it.

---

## Stage 2 — Run the notebook in Colab (10 minutes)

### 2.1 Open Colab
Go to **colab.research.google.com** → sign in with Google → **File → Upload
notebook** → upload
`notebooks\feature_impact_analysis.ipynb`

### 2.2 Give it the data
Easiest way, no GitHub needed:
1. In Colab, click the **folder icon** on the left strip (Files)
2. Drag **`city_week_panel.csv`** and **`user_period.csv`** (from
   `data\output\`) into that panel and wait for the upload spinners to finish
3. Find the cell that starts `import os` and **replace its whole contents** with:
```python
import pandas as pd
panel = pd.read_csv("city_week_panel.csv")
users = pd.read_csv("user_period.csv")
print(f"panel: {panel.shape[0]} rows = {panel.city.nunique()} cities x {panel.week.nunique()} weeks")
panel.head(3)
```

*(After you push the repo to GitHub you can undo this and just put your username
in the original cell instead — then the notebook works from anywhere with no
uploads.)*

### 2.3 Run everything
**Runtime → Run all.** Takes about a minute (the 792-assignment loop is the slow
part).

### 2.4 Gate
- No red error boxes anywhere
- `panel: 312 rows = 12 cities x 26 weeks`
- Same headline numbers as Stage 1: **+11.36% naive**, **+6.70% / +5.61% DiD**,
  **p = 0.0013**, **placebo +0.54%**
- Four charts render inline
- The last cell of the notebook is the recommendation table

---

## Stage 3 — Check you can explain it

The project isn't resume-ready until this passes, and it's the part that
actually matters in an interview.

1. Read `docs\code_walkthrough.md` side by side with the notebook.
2. Then, without looking, answer these out loud:
   - What does difference-in-differences subtract, and why?
   - Why is the naive +11.4% wrong?
   - What is the parallel-trends assumption, and how did you test it?
   - Why did cancellation rate get excluded from the findings?
   - Why an exact randomisation test instead of a regression p-value?
   - Why report +5.6% instead of +6.7% or +11%?
3. Compare against `docs\interview_qa.md` Q2, Q4, Q5, Q7, Q8, Q11.

---

## Stage 4 — Publish

Same flow as the Blinkit repo: new GitHub repo named
`quickkart-feature-impact` → **Add file → Upload files** → drag in the folders
(`data`, `analysis`, `notebooks`, `docs`) and the loose files (`README.md`,
`requirements.txt`, `VERIFICATION.md`) → Commit.

The CSVs are only 1.7 MB, so unlike the Blinkit project you upload the data too
— that's what makes the notebook runnable by anyone who opens it.

Then add the description and topics in the **About** panel, and paste the repo
URL into `docs/resume_bullets.md`.

---

## If something fails

Tell me the stage number and paste the error. Most likely causes:

| Symptom | Cause |
|---|---|
| `ModuleNotFoundError: scipy` | Stage 1.2 didn't run — `pip install -r requirements.txt` |
| `FileNotFoundError: city_week_panel.csv` | Wrong folder, or the double-folder problem — check Stage 0 |
| Numbers differ everywhere | You re-ran `generate_panel_data.py` with a different numpy version; the committed CSVs are the reference — just don't regenerate |
| CIs differ in the last decimal | Expected — see Stage 1.6 |
