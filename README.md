# Baseball Pitch Prediction – Full User Guide

This guide is for end users who may only know VS Code.

If you follow this in order, you can run every available function without reading code.

---

## What this project does

It analyzes Trackman CSV files and gives:

1. **Live dashboard** (interactive in browser via VS Code Go Live)
2. **Spreadsheet exports** (CSV + Excel files)
3. **Pitcher heatmaps** and strategy context outputs

---

## Before you start

You need these installed on your computer:

1. **VS Code**
2. **Python 3.9 or newer**
3. **VS Code extension: Live Server** (`ritwickdey.liveserver`)

To install Live Server inside VS Code:

1. Open Extensions panel (left sidebar)
2. Search for `Live Server`
3. Install **Live Server** by Ritwick Dey

---

## Step 1 — Open the project folder in VS Code

Open the folder that contains:

- [parser.py](parser.py)
- [dashboard.html](dashboard.html)
- [dashboard.js](dashboard.js)
- [requirements.txt](requirements.txt)

Also put all Trackman CSV files in this same folder.

---

## Step 2 — Install required Python packages (copy/paste)

Open terminal in VS Code (**Terminal → New Terminal**) and run:

```bash
python3 -m pip install -r requirements.txt
```

If `python3` does not work, run:

```bash
python -m pip install -r requirements.txt
```

Packages installed from [requirements.txt](requirements.txt):

- pandas
- numpy
- matplotlib
- seaborn
- openpyxl

---

## Step 3 — Run the program (copy/paste)

Standard run:

```bash
python3 parser.py
```

If `python3` does not work:

```bash
python parser.py
```

When it starts, you will get a file picker list.

- Type numbers like `1 3 5` to analyze specific CSVs
- Press Enter (or type `all`) to analyze all CSVs

Then you will get an output mode menu:

- `1` = Save files (CSV/Excel/images)
- `2` = Live dashboard data mode

---

## Functionality A — Live Dashboard (recommended)

### A1) Build dashboard data

Fast command (all files + live mode):

```bash
python3 parser.py --all --live
```

Fallback if needed:

```bash
python parser.py --all --live
```

### A2) Open dashboard

1. Open [dashboard.html](dashboard.html) in VS Code
2. Click **Go Live** in bottom-right corner
3. Browser opens with live dashboard

If Go Live does not appear:

1. Confirm Live Server extension is installed
2. Reload VS Code window
3. Reopen [dashboard.html](dashboard.html)

### A3) What to use in dashboard

1. **Pitcher Profiles tab**: search pitcher + filter by count
2. **Heatmaps tab**: visual count-by-pitch tendencies
3. **Team Trends tab**: aggregate pitch mix by count
4. **Strategy Context tab**: tendency notes vs count baseline

Files used by live mode:

- [dashboard.html](dashboard.html)
- [dashboard.js](dashboard.js)
- [outputs/data.js](outputs/data.js)
- [outputs/heatmaps](outputs/heatmaps)

---

## Research component (what it is and how to use it)

The research component is a **rule-based strategy context layer** built into the analysis.

It does not pull internet articles. Instead, it compares each pitcher to count-based baselines from your dataset and then adds plain-language interpretation.

### How it works

1. Groups pitch types into families:
	- **Hard** (Fastball/Sinker/Cutter)
	- **Breaking** (Slider/Curveball/Sweeper/Slurve)
	- **Offspeed** (Changeup/Splitter/Knuckleball)
2. Labels count state as leverage type (Hitter / Pitcher / Neutral / Full).
3. For each pitcher and count, calculates pitch-family usage.
4. Compares that usage to the global baseline usage at the same count.
5. Writes a delta and interpretation note.

### Where to see it

- Live dashboard: **Strategy Context** tab
- File export: [outputs/research_context_strategy_report.csv](outputs/research_context_strategy_report.csv)

### Key columns in the report

- `PitcherFamilyProbabilityPct`: pitcher usage % for that pitch family at that count
- `BaselineProbabilityPct`: overall baseline % for that family at that count
- `DeltaVsCountBaselinePct`: difference vs baseline
- `StrategyInterpretation`: plain-language note (for example “matches common hitter-count pattern”)

Use this section to quickly identify whether a pitcher follows typical count strategy or shows counter-trend behavior.

---

## Functionality B — File Export Mode (CSV / Excel)

Run:

```bash
python3 parser.py --all
```

Then choose `1` when asked for output mode.

Main outputs are in [outputs](outputs):

- [outputs/pitcher_count_profiles_wide.csv](outputs/pitcher_count_profiles_wide.csv)
- [outputs/pitcher_count_tendencies.xlsx](outputs/pitcher_count_tendencies.xlsx)
- [outputs/pitcher_count_tendencies_long.csv](outputs/pitcher_count_tendencies_long.csv)
- [outputs/top_pitcher_count_insights.csv](outputs/top_pitcher_count_insights.csv)
- [outputs/research_context_strategy_report.csv](outputs/research_context_strategy_report.csv)
- [outputs/team_level_count_trends.csv](outputs/team_level_count_trends.csv)
- [outputs/context_by_outs.csv](outputs/context_by_outs.csv)
- [outputs/context_by_home_away.csv](outputs/context_by_home_away.csv)
- [outputs/context_by_inning_bucket.csv](outputs/context_by_inning_bucket.csv)
- [outputs/context_by_batter_order_in_inning.csv](outputs/context_by_batter_order_in_inning.csv)

---

## Useful commands (copy/paste)

Analyze all files with picker skipped:

```bash
python3 parser.py --all
```

Analyze selected files (interactive picker):

```bash
python3 parser.py
```

Live mode directly:

```bash
python3 parser.py --all --live
```

Run with sample filters:

```bash
python3 parser.py --all --min-count-sample 5 --context-min-sample 8 --min-heatmap-pitches 30
```

---

## Troubleshooting

### `python3` not found

Use `python` instead of `python3` in commands.

### Package install errors

Run:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### Dashboard opens but no data

Run live build first:

```bash
python3 parser.py --all --live
```

Then refresh browser on [dashboard.html](dashboard.html) via Go Live.
