from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


# All legal pre-pitch count states for MLB/NCAA baseball.
ALL_COUNTS = [
	"0-0",
	"1-0",
	"0-1",
	"2-0",
	"1-1",
	"0-2",
	"3-0",
	"2-1",
	"1-2",
	"3-1",
	"2-2",
	"3-2",
]

# Default pitch type normalization map.
PITCH_TYPE_MAP = {
	"fastball": "Fastball",
	"four-seam": "Fastball",
	"four seam": "Fastball",
	"2-seam": "Sinker",
	"two-seam": "Sinker",
	"two seam": "Sinker",
	"sinker": "Sinker",
	"cutter": "Cutter",
	"slider": "Slider",
	"curveball": "Curveball",
	"curve": "Curveball",
	"changeup": "Changeup",
	"change up": "Changeup",
	"change-up": "Changeup",
	"splitter": "Splitter",
	"knuckleball": "Knuckleball",
	"sweeper": "Sweeper",
	"slurve": "Slurve",
	"other": "Other",
	"undefined": "Unknown",
	"": "Unknown",
}

COUNT_LEVERAGE_MAP = {
	"0-0": "Neutral",
	"1-0": "Hitter",
	"0-1": "Pitcher",
	"2-0": "Hitter",
	"1-1": "Neutral",
	"0-2": "Pitcher",
	"3-0": "Hitter",
	"2-1": "Hitter",
	"1-2": "Pitcher",
	"3-1": "Hitter",
	"2-2": "Neutral",
	"3-2": "Full",
}

HARD_PITCHES = {"Fastball", "Sinker", "Cutter"}
BREAKING_PITCHES = {"Slider", "Curveball", "Sweeper", "Slurve"}
OFFSPEED_PITCHES = {"Changeup", "Splitter", "Knuckleball"}


def _pick_first_existing_column(columns: Iterable[str], candidates: List[str]) -> Optional[str]:
	"""Return the first candidate column found in a DataFrame column set."""
	col_set = set(columns)
	for candidate in candidates:
		if candidate in col_set:
			return candidate
	return None


def find_trackman_csv_files(data_dir: Path) -> List[Path]:
	"""Return sorted CSV files in the provided directory."""
	files = sorted(data_dir.glob("*.csv"))
	if not files:
		raise FileNotFoundError(f"No CSV files found in {data_dir}")
	return files


def interactive_file_picker(data_dir: Path) -> List[Path]:
	"""
	Present an interactive numbered menu so the user can choose which CSV
	files to analyze. Typing 'all' or pressing Enter with no input selects
	everything. Returns the chosen list of Paths.
	"""
	all_files = find_trackman_csv_files(data_dir)

	print()
	print("=" * 60)
	print("  CSV FILES AVAILABLE FOR ANALYSIS")
	print("=" * 60)
	for i, fp in enumerate(all_files, start=1):
		print(f"  [{i}] {fp.name}")
	print()
	print("Type the numbers of the files you want (e.g.  1 3 5)")
	print("Press Enter with nothing typed, or type 'all', to use all files.")
	print("=" * 60)

	raw = input("Your selection: ").strip()

	if not raw or raw.lower() == "all":
		print(f"\nUsing all {len(all_files)} files.\n")
		return all_files

	chosen: List[Path] = []
	invalid: List[str] = []
	for token in raw.split():
		if token.isdigit():
			idx = int(token)
			if 1 <= idx <= len(all_files):
				chosen.append(all_files[idx - 1])
			else:
				invalid.append(token)
		else:
			invalid.append(token)

	if invalid:
		print(f"[WARN] Ignored unrecognised entries: {', '.join(invalid)}")

	if not chosen:
		print("No valid files selected. Falling back to all files.\n")
		return all_files

	print(f"\nSelected {len(chosen)} file(s):")
	for fp in chosen:
		print(f"  • {fp.name}")
	print()
	return chosen


def load_trackman_data(file_paths: List[Path]) -> pd.DataFrame:
	"""Load and concatenate multiple Trackman CSV files."""
	frames = []
	for fp in file_paths:
		df = pd.read_csv(fp, low_memory=False)
		df["SourceFile"] = fp.name
		frames.append(df)
	merged = pd.concat(frames, ignore_index=True)
	return merged


def normalize_pitch_type(value: object) -> str:
	"""Normalize pitch type labels into a compact, consistent taxonomy."""
	if pd.isna(value):
		return "Unknown"
	cleaned = str(value).strip()
	if not cleaned:
		return "Unknown"
	key = cleaned.lower()
	return PITCH_TYPE_MAP.get(key, cleaned.title())


def build_count_string(balls: object, strikes: object) -> Optional[str]:
	"""Create count string like '2-1' from balls and strikes values."""
	try:
		b = int(float(balls))
		s = int(float(strikes))
	except (TypeError, ValueError):
		return None

	# Legal in-progress pre-pitch count states.
	if b < 0 or b > 3 or s < 0 or s > 2:
		return None
	return f"{b}-{s}"


def standardize_trackman_columns(raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
	"""
	Standardize key columns used by the tendency model.

	Returns
	-------
	(standardized_df, column_mapping_used)
	"""
	mapping = {
		"pitcher": _pick_first_existing_column(raw.columns, ["Pitcher", "PitcherName"]),
		"pitcher_team": _pick_first_existing_column(raw.columns, ["PitcherTeam"]),
		"balls": _pick_first_existing_column(raw.columns, ["Balls"]),
		"strikes": _pick_first_existing_column(raw.columns, ["Strikes"]),
		"tagged_pitch_type": _pick_first_existing_column(raw.columns, ["TaggedPitchType"]),
		"auto_pitch_type": _pick_first_existing_column(raw.columns, ["AutoPitchType"]),
		"pitch_call": _pick_first_existing_column(raw.columns, ["PitchCall"]),
		"outs": _pick_first_existing_column(raw.columns, ["Outs"]),
		"inning": _pick_first_existing_column(raw.columns, ["Inning"]),
		"top_bottom": _pick_first_existing_column(raw.columns, ["Top/Bottom", "TopBottom"]),
		"home_team": _pick_first_existing_column(raw.columns, ["HomeTeam"]),
		"away_team": _pick_first_existing_column(raw.columns, ["AwayTeam"]),
		"pa_of_inning": _pick_first_existing_column(raw.columns, ["PAofInning"]),
		"date": _pick_first_existing_column(raw.columns, ["Date"]),
	}

	required = ["pitcher", "balls", "strikes"]
	missing_required = [k for k in required if mapping[k] is None]
	if missing_required:
		raise ValueError(f"Missing required columns for analysis: {missing_required}")

	if mapping["tagged_pitch_type"] is None and mapping["auto_pitch_type"] is None:
		raise ValueError("Need at least one pitch type column: TaggedPitchType or AutoPitchType")

	data = pd.DataFrame()
	data["Pitcher"] = raw[mapping["pitcher"]].astype(str).str.strip()
	data["Balls"] = raw[mapping["balls"]]
	data["Strikes"] = raw[mapping["strikes"]]

	tagged = raw[mapping["tagged_pitch_type"]] if mapping["tagged_pitch_type"] else np.nan
	auto = raw[mapping["auto_pitch_type"]] if mapping["auto_pitch_type"] else np.nan
	data["RawPitchType"] = pd.Series(tagged).fillna(pd.Series(auto))
	data["PitchType"] = data["RawPitchType"].apply(normalize_pitch_type)

	data["Count"] = [build_count_string(b, s) for b, s in zip(data["Balls"], data["Strikes"])]

	# Optional context columns.
	data["PitchCall"] = raw[mapping["pitch_call"]] if mapping["pitch_call"] else np.nan
	data["Outs"] = raw[mapping["outs"]] if mapping["outs"] else np.nan
	data["Inning"] = raw[mapping["inning"]] if mapping["inning"] else np.nan
	data["TopBottom"] = raw[mapping["top_bottom"]] if mapping["top_bottom"] else np.nan
	data["HomeTeam"] = raw[mapping["home_team"]] if mapping["home_team"] else np.nan
	data["AwayTeam"] = raw[mapping["away_team"]] if mapping["away_team"] else np.nan
	data["PAofInning"] = raw[mapping["pa_of_inning"]] if mapping["pa_of_inning"] else np.nan
	data["Date"] = raw[mapping["date"]] if mapping["date"] else np.nan
	data["SourceFile"] = raw["SourceFile"] if "SourceFile" in raw.columns else np.nan

	# Home/Away flag from the pitcher's perspective.
	pitcher_team_col = mapping.get("pitcher_team")
	if pitcher_team_col and mapping["home_team"] and mapping["away_team"]:
		pt = raw[pitcher_team_col].astype(str)
		ht = raw[mapping["home_team"]].astype(str)
		at = raw[mapping["away_team"]].astype(str)
		data["PitcherHomeAway"] = np.where(pt == ht, "Home", np.where(pt == at, "Away", "Unknown"))
	else:
		data["PitcherHomeAway"] = "Unknown"

	return data, {k: v for k, v in mapping.items() if v is not None}


def filter_data_by_team_query(clean_data: pd.DataFrame, team_query: str) -> pd.DataFrame:
	"""Filter rows by team acronym/name match across known team columns."""
	query = (team_query or "").strip().lower()
	if not query:
		return clean_data

	df = clean_data.copy()
	mask = pd.Series(False, index=df.index)
	for col in ["HomeTeam", "AwayTeam", "PitcherTeam"]:
		if col in df.columns:
			vals = df[col].astype(str).str.lower()
			mask = mask | vals.str.contains(query, na=False)

	filtered = df[mask].copy()
	return filtered


def build_pitcher_count_tendencies(clean_data: pd.DataFrame, min_pitches: int = 1) -> pd.DataFrame:
	"""Compute pitcher-by-count pitch type frequencies and probabilities."""
	df = clean_data.copy()
	df = df[df["Count"].isin(ALL_COUNTS)]
	df = df[df["Pitcher"].notna() & (df["Pitcher"].astype(str).str.strip() != "")]

	grouped = (
		df.groupby(["Pitcher", "Count", "PitchType"], dropna=False)
		.size()
		.reset_index(name="PitchCount")
	)

	grouped["TotalPitchesAtCount"] = grouped.groupby(["Pitcher", "Count"]) ["PitchCount"].transform("sum")
	grouped["Probability"] = grouped["PitchCount"] / grouped["TotalPitchesAtCount"]
	grouped["ProbabilityPct"] = (grouped["Probability"] * 100).round(2)

	# Enforce minimum sample size per pitcher-count bucket.
	grouped = grouped[grouped["TotalPitchesAtCount"] >= min_pitches].copy()

	grouped = grouped.sort_values(["Pitcher", "Count", "PitchCount"], ascending=[True, True, False])
	return grouped.reset_index(drop=True)


def build_pitcher_profile_wide(tendencies_long: pd.DataFrame) -> pd.DataFrame:
	"""Pivot long-form probabilities into one row per pitcher/count."""
	wide = tendencies_long.pivot_table(
		index=["Pitcher", "Count", "TotalPitchesAtCount"],
		columns="PitchType",
		values="ProbabilityPct",
		fill_value=0,
	).reset_index()

	# Keep baseball count order.
	wide["Count"] = pd.Categorical(wide["Count"], categories=ALL_COUNTS, ordered=True)
	wide = wide.sort_values(["Pitcher", "Count"]).reset_index(drop=True)
	wide.columns.name = None
	return wide


def build_context_splits(clean_data: pd.DataFrame, min_pitches: int = 5) -> Dict[str, pd.DataFrame]:
	"""Create optional context breakdowns requested in project scope."""
	df = clean_data.copy()
	df = df[df["Count"].isin(ALL_COUNTS)]

	# Early vs late inning split.
	if "Inning" in df.columns:
		inning_num = pd.to_numeric(df["Inning"], errors="coerce")
		df["InningBucket"] = np.where(inning_num <= 3, "Early (1-3)", np.where(inning_num >= 7, "Late (7+)", "Middle (4-6)"))
	else:
		df["InningBucket"] = "Unknown"

	# First/second/third+ batter of inning using PAofInning.
	pa_num = pd.to_numeric(df.get("PAofInning", np.nan), errors="coerce")
	df["BatterOrderInInning"] = np.select(
		[pa_num == 1, pa_num == 2, pa_num >= 3],
		["1st Batter", "2nd Batter", "3rd+ Batter"],
		default="Unknown",
	)

	breakdown_specs = {
		"by_outs": ["Pitcher", "Outs", "Count", "PitchType"],
		"by_home_away": ["Pitcher", "PitcherHomeAway", "Count", "PitchType"],
		"by_inning_bucket": ["Pitcher", "InningBucket", "Count", "PitchType"],
		"by_batter_order_in_inning": ["Pitcher", "BatterOrderInInning", "Count", "PitchType"],
	}

	outputs: Dict[str, pd.DataFrame] = {}
	for name, keys in breakdown_specs.items():
		tmp = df.groupby(keys, dropna=False).size().reset_index(name="PitchCount")
		tmp["TotalPitchesInSplit"] = tmp.groupby(keys[:-1])["PitchCount"].transform("sum")
		tmp = tmp[tmp["TotalPitchesInSplit"] >= min_pitches].copy()
		tmp["Probability"] = tmp["PitchCount"] / tmp["TotalPitchesInSplit"]
		tmp["ProbabilityPct"] = (tmp["Probability"] * 100).round(2)
		outputs[name] = tmp.sort_values(keys[:-1] + ["PitchCount"], ascending=[True] * len(keys[:-1]) + [False])

	return outputs


def build_team_level_trends(clean_data: pd.DataFrame, min_pitches: int = 10) -> pd.DataFrame:
	"""Optional aggregate team-level trends by count and pitch type."""
	df = clean_data.copy()
	df = df[df["Count"].isin(ALL_COUNTS)]
	if "SourceFile" not in df.columns:
		df["SourceFile"] = "Unknown"

	# Team inferred from PitcherTeam when available, fallback Unknown.
	team = "Unknown"
	if "PitcherHomeAway" in df.columns:
		team = df["PitcherHomeAway"]

	df["TeamContext"] = team

	out = df.groupby(["Count", "PitchType"], dropna=False).size().reset_index(name="PitchCount")
	out["TotalPitchesAtCount"] = out.groupby(["Count"])["PitchCount"].transform("sum")
	out = out[out["TotalPitchesAtCount"] >= min_pitches].copy()
	out["Probability"] = out["PitchCount"] / out["TotalPitchesAtCount"]
	out["ProbabilityPct"] = (out["Probability"] * 100).round(2)
	out["Count"] = pd.Categorical(out["Count"], categories=ALL_COUNTS, ordered=True)
	return out.sort_values(["Count", "PitchCount"], ascending=[True, False]).reset_index(drop=True)


def classify_pitch_family(pitch_type: str) -> str:
	"""Map pitch type into broad families for research-context summaries."""
	if pitch_type in HARD_PITCHES:
		return "Hard"
	if pitch_type in BREAKING_PITCHES:
		return "Breaking"
	if pitch_type in OFFSPEED_PITCHES:
		return "Offspeed"
	return "Other/Unknown"


def _strategy_note(leverage: str, family: str, delta_pct: float, threshold_pct: float) -> str:
	"""Generate rule-based interpretation notes using common count strategy ideas."""
	if abs(delta_pct) < threshold_pct:
		return "Near baseline for this count"

	if leverage == "Hitter" and family == "Hard":
		return "Matches common hitter-count pattern (more hard pitches)" if delta_pct > 0 else "Counter-trend: fewer hard pitches in hitter count"
	if leverage == "Pitcher" and family in {"Breaking", "Offspeed"}:
		return "Matches common pitcher-count pattern (more chase/soft pitches)" if delta_pct > 0 else "Counter-trend: fewer chase/soft pitches in pitcher count"
	if leverage == "Pitcher" and family == "Hard":
		return "Counter-trend: more hard pitches in pitcher count" if delta_pct > 0 else "Matches common pitcher-count pattern (less hard pitch reliance)"
	if leverage == "Full" and family == "Hard":
		return "Leans to hard pitch in full count" if delta_pct > 0 else "Leans away from hard pitch in full count"
	return "Count-specific preference differs from baseline" if delta_pct > 0 else "Count-specific preference lower than baseline"


def build_research_context_report(
	tendencies_long: pd.DataFrame,
	min_count_sample: int = 8,
	delta_threshold_pct: float = 10.0,
) -> pd.DataFrame:
	"""
	Create a research-context helper table that compares each pitcher to count baseline.

	This does not fetch external literature. It encodes common baseball strategy concepts
	as rules and highlights where each pitcher aligns or deviates by count.
	"""
	df = tendencies_long.copy()
	df = df[df["TotalPitchesAtCount"] >= min_count_sample].copy()
	if df.empty:
		return pd.DataFrame()

	df["CountLeverage"] = df["Count"].map(COUNT_LEVERAGE_MAP).fillna("Unknown")
	df["PitchFamily"] = df["PitchType"].apply(classify_pitch_family)

	# Pitcher-level family probabilities at each count.
	pitcher_family = (
		df.groupby(["Pitcher", "Count", "CountLeverage", "PitchFamily"], dropna=False)
		.agg(
			FamilyPitchCount=("PitchCount", "sum"),
			TotalPitchesAtCount=("TotalPitchesAtCount", "max"),
		)
		.reset_index()
	)
	pitcher_family["PitcherFamilyProbability"] = pitcher_family["FamilyPitchCount"] / pitcher_family["TotalPitchesAtCount"]
	pitcher_family["PitcherFamilyProbabilityPct"] = (pitcher_family["PitcherFamilyProbability"] * 100).round(2)

	# Global count baseline by family.
	count_family_baseline = (
		df.groupby(["Count", "PitchFamily"], dropna=False)
		.agg(FamilyPitchCount=("PitchCount", "sum"))
		.reset_index()
	)
	count_totals = count_family_baseline.groupby("Count", as_index=False)["FamilyPitchCount"].sum().rename(
		columns={"FamilyPitchCount": "GlobalTotalAtCount"}
	)
	count_family_baseline = count_family_baseline.merge(count_totals, on="Count", how="left")
	count_family_baseline["BaselineProbability"] = (
		count_family_baseline["FamilyPitchCount"] / count_family_baseline["GlobalTotalAtCount"]
	)
	count_family_baseline["BaselineProbabilityPct"] = (count_family_baseline["BaselineProbability"] * 100).round(2)

	report = pitcher_family.merge(
		count_family_baseline[["Count", "PitchFamily", "BaselineProbabilityPct"]],
		on=["Count", "PitchFamily"],
		how="left",
	)
	report["DeltaVsCountBaselinePct"] = (
		report["PitcherFamilyProbabilityPct"] - report["BaselineProbabilityPct"]
	).round(2)

	report["StrategyInterpretation"] = [
		_strategy_note(lev, fam, delta, delta_threshold_pct)
		for lev, fam, delta in zip(
			report["CountLeverage"],
			report["PitchFamily"],
			report["DeltaVsCountBaselinePct"],
		)
	]

	report["Count"] = pd.Categorical(report["Count"], categories=ALL_COUNTS, ordered=True)
	report = report.sort_values(
		["Pitcher", "Count", "PitchFamily"],
		ascending=[True, True, True],
	).reset_index(drop=True)

	return report


def save_pitcher_heatmaps(
	tendencies_long: pd.DataFrame,
	output_dir: Path,
	min_total_pitches_per_pitcher: int = 25,
) -> None:
	"""Save one heatmap per pitcher showing pitch-type probability by count."""
	output_dir.mkdir(parents=True, exist_ok=True)
	sns.set_theme(style="whitegrid")

	totals = (
		tendencies_long[["Pitcher", "PitchCount"]]
		.groupby("Pitcher", as_index=False)
		.sum()
		.rename(columns={"PitchCount": "TotalPitches"})
	)
	eligible = set(totals.loc[totals["TotalPitches"] >= min_total_pitches_per_pitcher, "Pitcher"])

	for pitcher, grp in tendencies_long.groupby("Pitcher"):
		if pitcher not in eligible:
			continue

		pivot = grp.pivot_table(index="PitchType", columns="Count", values="ProbabilityPct", fill_value=0)
		ordered_cols = [c for c in ALL_COUNTS if c in pivot.columns]
		pivot = pivot.reindex(columns=ordered_cols)

		plt.figure(figsize=(12, 5))
		ax = sns.heatmap(pivot, annot=True, fmt=".1f", cmap="Blues", linewidths=0.3)
		ax.set_title(f"{pitcher} - Pitch Type Probability by Count (%)")
		ax.set_xlabel("Count")
		ax.set_ylabel("Pitch Type")
		plt.tight_layout()

		safe_name = "".join(ch for ch in pitcher if ch.isalnum() or ch in ("_", "-", " ")).strip().replace(" ", "_")
		plt.savefig(output_dir / f"{safe_name}_count_heatmap.png", dpi=160)
		plt.close()


def write_outputs(
	tendencies_long: pd.DataFrame,
	profile_wide: pd.DataFrame,
	context_splits: Dict[str, pd.DataFrame],
	team_trends: pd.DataFrame,
	output_dir: Path,
	excel_name: str = "pitcher_count_tendencies.xlsx",
) -> None:
	"""Write project deliverables to CSV and (if available) Excel."""
	output_dir.mkdir(parents=True, exist_ok=True)

	tendencies_long.to_csv(output_dir / "pitcher_count_tendencies_long.csv", index=False)
	profile_wide.to_csv(output_dir / "pitcher_count_profiles_wide.csv", index=False)
	team_trends.to_csv(output_dir / "team_level_count_trends.csv", index=False)

	for split_name, df in context_splits.items():
		df.to_csv(output_dir / f"context_{split_name}.csv", index=False)

	try:
		with pd.ExcelWriter(output_dir / excel_name, engine="openpyxl") as writer:
			tendencies_long.to_excel(writer, sheet_name="pitcher_count_long", index=False)
			profile_wide.to_excel(writer, sheet_name="pitcher_count_wide", index=False)
			team_trends.to_excel(writer, sheet_name="team_trends", index=False)
			for split_name, df in context_splits.items():
				sheet = split_name[:31]
				df.to_excel(writer, sheet_name=sheet, index=False)
	except Exception as exc:
		print(f"[WARN] Excel output skipped ({exc}). CSV files were still written.")


def summarize_key_insights(tendencies_long: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
	"""Return top strongest pitcher-count tendencies for quick reporting."""
	insights = tendencies_long.copy()
	insights = insights[insights["TotalPitchesAtCount"] >= 5].copy()
	insights = insights.sort_values(["Probability", "TotalPitchesAtCount"], ascending=[False, False])
	return insights.head(top_n).reset_index(drop=True)


def generate_data_js(
	tendencies_long: pd.DataFrame,
	team_trends: pd.DataFrame,
	research_context: pd.DataFrame,
	output_dir: Path,
	min_heatmap_pitches: int = 15,
) -> None:
	"""
	Write outputs/data.js containing all pitch data as a JavaScript object
	and save per-pitcher heatmap images to outputs/heatmaps/.
	Open dashboard.html in VS Code and click Go Live in the status bar to view.
	"""
	import json

	import matplotlib
	matplotlib.use("Agg")

	output_dir.mkdir(parents=True, exist_ok=True)
	heatmap_dir = output_dir / "heatmaps"
	heatmap_dir.mkdir(parents=True, exist_ok=True)

	sns.set_theme(style="whitegrid")
	totals = (
		tendencies_long[["Pitcher", "PitchCount"]]
		.groupby("Pitcher", as_index=False)
		.sum()
		.rename(columns={"PitchCount": "TotalPitches"})
	)
	eligible = set(totals.loc[totals["TotalPitches"] >= min_heatmap_pitches, "Pitcher"])
	heatmap_files: Dict[str, str] = {}

	for pitcher, grp in tendencies_long.groupby("Pitcher"):
		if pitcher not in eligible:
			continue
		pivot = grp.pivot_table(index="PitchType", columns="Count", values="ProbabilityPct", fill_value=0)
		ordered_cols = [c for c in ALL_COUNTS if c in pivot.columns]
		pivot = pivot.reindex(columns=ordered_cols)
		fig, ax = plt.subplots(figsize=(12, 4))
		sns.heatmap(pivot, annot=True, fmt=".1f", cmap="Blues", linewidths=0.3, ax=ax)
		ax.set_title(f"{pitcher} - Pitch Type % by Count")
		plt.tight_layout()
		safe_name = "".join(ch for ch in pitcher if ch.isalnum() or ch in ("_", "-", " ")).strip().replace(" ", "_")
		img_path = heatmap_dir / f"{safe_name}_count_heatmap.png"
		fig.savefig(img_path, dpi=130)
		plt.close(fig)
		heatmap_files[pitcher] = f"outputs/heatmaps/{safe_name}_count_heatmap.png"

	def _df_to_list(df: pd.DataFrame) -> list:
		return json.loads(df.to_json(orient="records", default_handler=str))

	pitchers_sorted = sorted(tendencies_long["Pitcher"].unique().tolist())

	payload = {
		"pitchers": pitchers_sorted,
		"allCounts": ALL_COUNTS,
		"dataLong": _df_to_list(tendencies_long),
		"teamTrends": _df_to_list(team_trends),
		"researchContext": _df_to_list(research_context) if not research_context.empty else [],
		"heatmapFiles": heatmap_files,
	}

	(output_dir / "data.js").write_text(
		"window.PITCH_DATA = " + json.dumps(payload, indent=2) + ";",
		encoding="utf-8",
	)
	print(f"Data written: {output_dir / 'data.js'}")
	print(f"Heatmaps saved: {heatmap_dir}")
	print("Open dashboard.html with Go Live in VS Code to view the dashboard.")


def generate_html_dashboard(
	tendencies_long: pd.DataFrame,
	profile_wide: pd.DataFrame,
	team_trends: pd.DataFrame,
	research_context: pd.DataFrame,
	output_dir: Path,
) -> Path:
	"""
	Generate a self-contained interactive HTML dashboard.
	No files other than the single HTML are produced.
	Opens automatically in the default browser when done.
	"""
	import base64, io, json, webbrowser

	output_dir.mkdir(parents=True, exist_ok=True)

	# ---- encode heatmaps as base64 so the HTML is fully self-contained ----
	images: Dict[str, str] = {}
	sns.set_theme(style="whitegrid")
	totals = (
		tendencies_long[["Pitcher", "PitchCount"]]
		.groupby("Pitcher", as_index=False)
		.sum()
		.rename(columns={"PitchCount": "TotalPitches"})
	)
	eligible = set(totals.loc[totals["TotalPitches"] >= 15, "Pitcher"])
	for pitcher, grp in tendencies_long.groupby("Pitcher"):
		if pitcher not in eligible:
			continue
		pivot = grp.pivot_table(index="PitchType", columns="Count", values="ProbabilityPct", fill_value=0)
		ordered_cols = [c for c in ALL_COUNTS if c in pivot.columns]
		pivot = pivot.reindex(columns=ordered_cols)
		fig, ax = plt.subplots(figsize=(12, 4))
		sns.heatmap(pivot, annot=True, fmt=".1f", cmap="Blues", linewidths=0.3, ax=ax)
		ax.set_title(f"{pitcher} – Pitch Type % by Count")
		plt.tight_layout()
		buf = io.BytesIO()
		fig.savefig(buf, format="png", dpi=130)
		plt.close(fig)
		images[pitcher] = base64.b64encode(buf.getvalue()).decode()

	# ---- serialise DataFrames to JSON for the JS layer ----
	def df_to_json(df: pd.DataFrame) -> str:
		return df.to_json(orient="records", default_handler=str)

	pitchers_sorted = sorted(tendencies_long["Pitcher"].unique().tolist())

	html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pitch Tendency Dashboard</title>
<style>
  :root {{ --accent:#1a5fa8; --light:#eef4fb; --border:#cddcee; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family: system-ui, sans-serif; background:#f5f7fa; color:#222; }}
  header {{ background:var(--accent); color:#fff; padding:18px 28px; }}
  header h1 {{ font-size:1.4rem; }}
  header p {{ font-size:.85rem; opacity:.85; margin-top:4px; }}
  nav {{ display:flex; gap:0; background:#fff; border-bottom:2px solid var(--accent); }}
  nav button {{ padding:12px 22px; border:none; background:none; cursor:pointer; font-size:.9rem; font-weight:600; color:#555; border-bottom:3px solid transparent; transition:.15s; }}
  nav button.active, nav button:hover {{ color:var(--accent); border-color:var(--accent); }}
  section {{ display:none; padding:24px 28px; }}
  section.active {{ display:block; }}
  h2 {{ font-size:1.1rem; margin-bottom:14px; color:var(--accent); }}
  /* controls */
  .controls {{ display:flex; flex-wrap:wrap; gap:12px; margin-bottom:18px; align-items:center; }}
  select, input[type=text] {{ padding:7px 11px; border:1px solid var(--border); border-radius:6px; font-size:.9rem; background:#fff; }}
  label {{ font-size:.85rem; color:#555; }}
  /* table */
  .tbl-wrap {{ overflow-x:auto; border-radius:8px; box-shadow:0 1px 4px #0001; }}
  table {{ width:100%; border-collapse:collapse; font-size:.85rem; background:#fff; }}
  thead th {{ background:var(--accent); color:#fff; padding:9px 12px; text-align:left; white-space:nowrap; }}
  tbody tr:nth-child(even) {{ background:var(--light); }}
  tbody td {{ padding:8px 12px; border-bottom:1px solid var(--border); white-space:nowrap; }}
  .pct-cell {{ font-weight:600; }}
  .heat-grid {{ display:flex; flex-wrap:wrap; gap:20px; }}
  .heat-card {{ background:#fff; border:1px solid var(--border); border-radius:8px; padding:14px; box-shadow:0 1px 4px #0001; }}
  .heat-card h3 {{ font-size:.9rem; color:var(--accent); margin-bottom:8px; }}
  .heat-card img {{ max-width:100%; border-radius:4px; }}
  .no-img {{ color:#888; font-size:.85rem; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:20px; font-size:.78rem; font-weight:600; }}
  .badge-hitter {{ background:#d4edda; color:#155724; }}
  .badge-pitcher {{ background:#f8d7da; color:#721c24; }}
  .badge-neutral {{ background:#fff3cd; color:#856404; }}
  .badge-full {{ background:#cce5ff; color:#004085; }}
  .search-box {{ padding:7px 12px; border:1px solid var(--border); border-radius:6px; font-size:.9rem; width:220px; }}
</style>
</head>
<body>
<header>
  <h1>⚾ Pitch Tendency Dashboard</h1>
  <p>Interactive analysis of pitcher selection patterns by count</p>
</header>
<nav>
  <button class="active" onclick="showTab('tab-profile')">Pitcher Profiles</button>
  <button onclick="showTab('tab-heatmaps')">Heatmaps</button>
  <button onclick="showTab('tab-team')">Team Trends</button>
  <button onclick="showTab('tab-research')">Strategy Context</button>
</nav>

<!-- TAB: PITCHER PROFILES -->
<section id="tab-profile" class="active">
  <h2>Pitcher Pitch-Type Probability by Count</h2>
  <div class="controls">
    <div><label>Pitcher<br>
      <select id="sel-pitcher" onchange="renderProfile()"><option value="">All</option></select>
    </label></div>
    <div><label>Count<br>
      <select id="sel-count" onchange="renderProfile()"><option value="">All</option></select>
    </label></div>
    <div><label>Search pitcher<br>
      <input class="search-box" id="search-pitcher" oninput="filterPitcherSelect()" placeholder="type name...">
    </label></div>
  </div>
  <div class="tbl-wrap"><table id="tbl-profile"><thead></thead><tbody></tbody></table></div>
</section>

<!-- TAB: HEATMAPS -->
<section id="tab-heatmaps">
  <h2>Heatmaps – Pitch % by Count (per pitcher)</h2>
  <div class="controls">
    <input class="search-box" id="heat-search" oninput="filterHeatmaps()" placeholder="search pitcher...">
  </div>
  <div class="heat-grid" id="heat-grid"></div>
</section>

<!-- TAB: TEAM TRENDS -->
<section id="tab-team">
  <h2>Team-Level Pitch Tendencies by Count</h2>
  <div class="controls">
    <label>Count<br><select id="sel-team-count" onchange="renderTeam()"><option value="">All</option></select></label>
  </div>
  <div class="tbl-wrap"><table id="tbl-team"><thead></thead><tbody></tbody></table></div>
</section>

<!-- TAB: RESEARCH / STRATEGY -->
<section id="tab-research">
  <h2>Strategy Context – How Each Pitcher Compares to League Norms</h2>
  <div class="controls">
    <label>Pitcher<br><select id="sel-res-pitcher" onchange="renderResearch()"><option value="">All</option></select></label>
    <label>Count Leverage<br><select id="sel-res-lev" onchange="renderResearch()"><option value="">All</option></select></label>
  </div>
  <div class="tbl-wrap"><table id="tbl-research"><thead></thead><tbody></tbody></table></div>
</section>

<script>
const ALL_COUNTS = {json.dumps(ALL_COUNTS)};
const PITCHERS   = {json.dumps(pitchers_sorted)};
const DATA_LONG  = {df_to_json(tendencies_long)};
const DATA_TEAM  = {df_to_json(team_trends)};
const DATA_RES   = {df_to_json(research_context) if not research_context.empty else '[]'};
const IMAGES     = {json.dumps(images)};

function showTab(id) {{
  document.querySelectorAll('section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
}}

// ---- populate selects ----
function populateSelect(sel, values) {{
  const existing = sel.value;
  while (sel.options.length > 1) sel.remove(1);
  values.forEach(v => {{ const o = new Option(v, v); sel.add(o); }});
  if ([...sel.options].some(o => o.value === existing)) sel.value = existing;
}}

function filterPitcherSelect() {{
  const q = document.getElementById('search-pitcher').value.toLowerCase();
  const filtered = PITCHERS.filter(p => p.toLowerCase().includes(q));
  populateSelect(document.getElementById('sel-pitcher'), filtered);
  renderProfile();
}}

// ---- pitcher profile tab ----
function renderProfile() {{
  const pitcher = document.getElementById('sel-pitcher').value;
  const count   = document.getElementById('sel-count').value;
  let rows = DATA_LONG.filter(r =>
    (!pitcher || r.Pitcher === pitcher) &&
    (!count   || r.Count   === count)
  );
  // collect pitch types present
  const pitchTypes = [...new Set(rows.map(r => r.PitchType))].sort();
  const thead = document.querySelector('#tbl-profile thead');
  const tbody = document.querySelector('#tbl-profile tbody');
  thead.innerHTML = '<tr>' + ['Pitcher','Count','Pitches','Total'].concat(pitchTypes).map(h => `<th>${{h}}</th>`).join('') + '</tr>';
  // group by pitcher+count
  const grouped = {{}};
  rows.forEach(r => {{
    const key = r.Pitcher + '|||' + r.Count;
    if (!grouped[key]) grouped[key] = {{ Pitcher: r.Pitcher, Count: r.Count, Total: r.TotalPitchesAtCount, types: {{}} }};
    grouped[key].types[r.PitchType] = r.ProbabilityPct;
  }});
  tbody.innerHTML = Object.values(grouped).map(g => {{
    const cells = pitchTypes.map(pt => `<td class="pct-cell">${{g.types[pt] != null ? g.types[pt].toFixed(1)+'%' : '—'}}</td>`).join('');
    return `<tr><td>${{g.Pitcher}}</td><td>${{g.Count}}</td><td>${{g.Total}}</td><td>${{g.Total}}</td>${{cells}}</tr>`;
  }}).join('');
}}

// ---- heatmaps tab ----
function renderHeatmaps(filter='') {{
  const grid = document.getElementById('heat-grid');
  grid.innerHTML = '';
  const q = filter.toLowerCase();
  Object.entries(IMAGES).forEach(([name, b64]) => {{
    if (q && !name.toLowerCase().includes(q)) return;
    const card = document.createElement('div');
    card.className = 'heat-card';
    card.innerHTML = `<h3>${{name}}</h3><img src="data:image/png;base64,${{b64}}" alt="heatmap">`;
    grid.appendChild(card);
  }});
  if (!grid.children.length) grid.innerHTML = '<p class="no-img">No heatmaps match the search.</p>';
}}
function filterHeatmaps() {{ renderHeatmaps(document.getElementById('heat-search').value); }}

// ---- team trends tab ----
function renderTeam() {{
  const count = document.getElementById('sel-team-count').value;
  let rows = DATA_TEAM.filter(r => !count || r.Count === count);
  const thead = document.querySelector('#tbl-team thead');
  const tbody = document.querySelector('#tbl-team tbody');
  if (!rows.length) {{ thead.innerHTML=''; tbody.innerHTML='<tr><td>No data</td></tr>'; return; }}
  const cols = Object.keys(rows[0]);
  thead.innerHTML = '<tr>' + cols.map(c => `<th>${{c}}</th>`).join('') + '</tr>';
  tbody.innerHTML = rows.map(r => '<tr>' + cols.map(c => `<td>${{r[c] ?? ''}}</td>`).join('') + '</tr>').join('');
}}

// ---- research tab ----
const LEV_CLASS = {{ Hitter:'badge-hitter', Pitcher:'badge-pitcher', Neutral:'badge-neutral', Full:'badge-full' }};
function renderResearch() {{
  const pitcher = document.getElementById('sel-res-pitcher').value;
  const lev     = document.getElementById('sel-res-lev').value;
  let rows = DATA_RES.filter(r =>
    (!pitcher || r.Pitcher === pitcher) &&
    (!lev     || r.CountLeverage === lev)
  );
  const thead = document.querySelector('#tbl-research thead');
  const tbody = document.querySelector('#tbl-research tbody');
  if (!rows.length) {{ thead.innerHTML=''; tbody.innerHTML='<tr><td>No data</td></tr>'; return; }}
  thead.innerHTML = `<tr><th>Pitcher</th><th>Count</th><th>Leverage</th><th>Pitch Family</th><th>Pitcher %</th><th>Baseline %</th><th>Delta</th><th>Interpretation</th></tr>`;
  tbody.innerHTML = rows.map(r => {{
    const cls = LEV_CLASS[r.CountLeverage] || '';
    const delta = r.DeltaVsCountBaselinePct;
    const color = delta > 0 ? '#155724' : '#721c24';
    return `<tr>
      <td>${{r.Pitcher}}</td>
      <td>${{r.Count}}</td>
      <td><span class="badge ${{cls}}">${{r.CountLeverage}}</span></td>
      <td>${{r.PitchFamily}}</td>
      <td class="pct-cell">${{r.PitcherFamilyProbabilityPct?.toFixed(1)}}%</td>
      <td class="pct-cell">${{r.BaselineProbabilityPct?.toFixed(1)}}%</td>
      <td style="color:${{color}};font-weight:600">${{{{
        (delta > 0 ? '+' : '') + delta?.toFixed(1)
      }}}}%</td>
      <td>${{r.StrategyInterpretation}}</td>
    </tr>`;
  }}).join('');
}}

// ---- init ----
(function init() {{
  populateSelect(document.getElementById('sel-pitcher'), PITCHERS);
  populateSelect(document.getElementById('sel-count'), ALL_COUNTS);
  populateSelect(document.getElementById('sel-team-count'), ALL_COUNTS);
  populateSelect(document.getElementById('sel-res-pitcher'), PITCHERS);
  const levs = [...new Set(DATA_RES.map(r => r.CountLeverage))].filter(Boolean).sort();
  populateSelect(document.getElementById('sel-res-lev'), levs);
  renderProfile();
  renderHeatmaps();
  renderTeam();
  renderResearch();
}})();
</script>
</body>
</html>
"""

	out_path = output_dir / "dashboard.html"
	out_path.write_text(html, encoding="utf-8")
	webbrowser.open(out_path.as_uri())
	print(f"Dashboard saved and opened: {out_path}")
	return out_path


def run_pipeline(
	data_dir: Path,
	output_dir: Path,
	min_count_sample: int,
	context_min_sample: int,
	min_heatmap_pitches: int,
	csv_files: Optional[List[Path]] = None,
	live_mode: bool = False,
) -> None:
	"""End-to-end execution for pitcher tendency analysis."""
	if csv_files is None:
		csv_files = find_trackman_csv_files(data_dir)
	print(f"Analyzing {len(csv_files)} CSV file(s):")
	for f in csv_files:
		print(f"  • {f.name}")

	raw = load_trackman_data(csv_files)
	clean, col_map = standardize_trackman_columns(raw)
	print("Using columns:", col_map)

	tendencies_long = build_pitcher_count_tendencies(clean, min_pitches=min_count_sample)
	if tendencies_long.empty:
		raise ValueError("No tendency rows were produced. Check input data and column mapping.")

	profile_wide = build_pitcher_profile_wide(tendencies_long)
	context_splits = build_context_splits(clean, min_pitches=context_min_sample)
	team_trends = build_team_level_trends(clean)
	research_context = build_research_context_report(
		tendencies_long,
		min_count_sample=max(5, context_min_sample),
		delta_threshold_pct=10.0,
	)

	print(f"Pitchers profiled: {tendencies_long['Pitcher'].nunique():,}")

	if live_mode:
		generate_data_js(tendencies_long, team_trends, research_context, output_dir, min_heatmap_pitches)
	else:
		write_outputs(tendencies_long, profile_wide, context_splits, team_trends, output_dir)
		save_pitcher_heatmaps(tendencies_long, output_dir / "heatmaps", min_total_pitches_per_pitcher=min_heatmap_pitches)
		if not research_context.empty:
			research_context.to_csv(output_dir / "research_context_strategy_report.csv", index=False)
		else:
			print("[INFO] research_context_strategy_report.csv skipped (not enough sample size).")
		insights = summarize_key_insights(tendencies_long)
		insights.to_csv(output_dir / "top_pitcher_count_insights.csv", index=False)
		print(f"Outputs written to: {output_dir}")


def parse_args() -> argparse.Namespace:
	"""CLI arguments for the analysis pipeline."""
	parser = argparse.ArgumentParser(
		description="Build pitcher tendencies by count from Trackman CSV files."
	)
	parser.add_argument(
		"--data-dir",
		type=Path,
		default=Path(__file__).resolve().parent,
		help="Directory containing Trackman CSV files.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		default=Path(__file__).resolve().parent / "outputs",
		help="Directory where output files are written.",
	)
	parser.add_argument(
		"--min-count-sample",
		type=int,
		default=1,
		help="Minimum pitches for a pitcher+count bucket to keep.",
	)
	parser.add_argument(
		"--context-min-sample",
		type=int,
		default=5,
		help="Minimum pitches for a context split bucket to keep.",
	)
	parser.add_argument(
		"--min-heatmap-pitches",
		type=int,
		default=25,
		help="Minimum total pitches by pitcher to generate a heatmap.",
	)
	parser.add_argument(
		"--all",
		action="store_true",
		help="Skip the file picker and analyze every CSV in the data directory.",
	)
	parser.add_argument(
		"--live",
		action="store_true",
		help="Open an interactive HTML dashboard instead of writing files.",
	)
	return parser.parse_args()


if __name__ == "__main__":
	args = parse_args()

	if args.all:
		selected_files = find_trackman_csv_files(args.data_dir)
	else:
		selected_files = interactive_file_picker(args.data_dir)

	# Determine output mode
	if args.live:
		live_mode = True
	else:
		print()
		print("=" * 60)
		print("  HOW DO YOU WANT YOUR RESULTS?")
		print("=" * 60)
		print("  [1] Save files  – CSV, Excel, and heatmap images")
		print("  [2] Live view   – Interactive HTML dashboard (opens in browser)")
		print("=" * 60)
		mode_input = input("Your choice (1 or 2, default 1): ").strip()
		live_mode = mode_input == "2"
		print()

	run_pipeline(
		data_dir=args.data_dir,
		output_dir=args.output_dir,
		min_count_sample=args.min_count_sample,
		context_min_sample=args.context_min_sample,
		min_heatmap_pitches=args.min_heatmap_pitches,
		csv_files=selected_files,
		live_mode=live_mode,
	)
