# Minimal Read Me (Users + Quick Verification)

This is the **least complicated setup** that still lets users actively use the project.

## 1) One-time setup

In VS Code terminal, run:

```bash
python3 -m pip install -r requirements.txt
```

Install VS Code extension:
- Live Server 

## 2) Main user workflow (Live Dashboard)

Run:

```bash
python3 parser.py --all --live
```

Then:
1. Open `dashboard.html` in VS Code
2. Click **Go Live**

### What to try as a real user

1. **Pitcher Profiles tab**
	- Search a pitcher name
	- Change count filter (example: `2-1`)
	- Read pitch percentages for that count

2. **Heatmaps tab**
	- Search for a pitcher
	- View full count-by-pitch visual pattern

3. **Team Trends tab**
	- Filter by one count
	- Compare team-level pitch mix

4. **Strategy Context tab**
	- Select pitcher + leverage filter
	- Read interpretation notes for tendencies vs baseline

This is the primary day-to-day usage mode.

## 3) Secondary user workflow (Export files)

If users need files for sharing/reports:

```bash
python3 parser.py --all
```

Choose `1` at prompt (Save files).

Use these outputs first:
- `outputs/pitcher_count_profiles_wide.csv` (main table)
- `outputs/pitcher_count_tendencies.xlsx` (shareable workbook)

## 4) Minimal send-off check

Before sharing with others, confirm:
1. Dashboard opens and all 4 tabs are usable
2. Search/filter works on at least one pitcher
3. Export mode creates CSV and Excel outputs

## 5) Deploy (GitHub Pages / Netlify / Vercel static)

Use this exact sequence:

1. Build live assets locally:

```bash
python3 parser.py --all --live
```

2. Confirm these exist before deploy:
	- `dashboard.html`
	- `dashboard.js`
	- `outputs/data.js`
	- `outputs/heatmaps/*.png` (optional but recommended)

3. Commit and push **including `outputs/`**.

4. Deploy as a **static site** with publish root set to project root.

If deployment succeeds but page shows no tables, `outputs/data.js` was not generated or not included in deploy.

## If `python3` is not recognized

Use:

```bash
python -m pip install -r requirements.txt
python parser.py --all --live
```
