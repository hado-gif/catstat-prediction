from __future__ import annotations

import importlib.util
import traceback
from io import BytesIO
from pathlib import Path

import streamlit as st


def _log(message: str) -> None:
    print(message, flush=True)

st.set_page_config(page_title="Pitch Tendency App", layout="wide")
_log("[startup] streamlit page configured")

try:
    import pandas as pd
    _log("[startup] pandas imported")
except Exception as exc:
    st.title("⚾ Pitch Tendency App")
    st.error(f"Startup failed while importing pandas: {exc}")
    st.code(traceback.format_exc())
    st.stop()

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    _PLOTTING_OK = True
    _log("[startup] plotting libraries imported")
except Exception:
    plt = None  # type: ignore[assignment]
    sns = None  # type: ignore[assignment]
    _PLOTTING_OK = False
    _log("[startup] plotting libraries unavailable")

_PARSER_PATH = Path(__file__).resolve().with_name("parser.py")
try:
    _log(f"[startup] loading parser module from {_PARSER_PATH}")
    _SPEC = importlib.util.spec_from_file_location("local_parser", _PARSER_PATH)
    if _SPEC is None or _SPEC.loader is None:
        raise RuntimeError(f"Could not load parser module from {_PARSER_PATH}")
    _PARSER = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_PARSER)

    ALL_COUNTS = _PARSER.ALL_COUNTS
    build_pitcher_count_tendencies = _PARSER.build_pitcher_count_tendencies
    build_research_context_report = _PARSER.build_research_context_report
    build_team_level_trends = _PARSER.build_team_level_trends
    filter_data_by_team_query = _PARSER.filter_data_by_team_query
    standardize_trackman_columns = _PARSER.standardize_trackman_columns
    _log("[startup] parser module loaded")
except Exception as exc:
    st.title("⚾ Pitch Tendency App")
    st.error(f"App startup failed while loading parser.py: {exc}")
    st.code(traceback.format_exc())
    st.stop()


st.title("⚾ Pitch Tendency App")
st.caption("Upload Trackman CSV files, filter by team acronym/name, and view pitcher tendencies.")


with st.sidebar:
    st.header("Inputs")
    st.markdown("Upload CSV files below. In a deployed app, users can do this directly from the browser.")
    uploaded_files = st.file_uploader(
        "Upload one or more CSV files",
        type=["csv"],
        accept_multiple_files=True,
    )
    team_query = st.text_input("Team filter (optional)", placeholder="VCU or Saint Joseph")
    min_count_sample = st.number_input("Min pitches per pitcher+count", min_value=1, max_value=200, value=1)
    context_min_sample = st.number_input("Min sample for strategy context", min_value=1, max_value=200, value=5)


@st.cache_data(show_spinner=False)
def _load_uploaded_csvs(file_bytes_and_names: tuple[tuple[bytes, str], ...]) -> pd.DataFrame:
    frames = []
    for content, name in file_bytes_and_names:
        df = pd.read_csv(BytesIO(content), low_memory=False)
        df["SourceFile"] = name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


@st.cache_data(show_spinner=False)
def _build_outputs(
    file_bytes_and_names: tuple[tuple[bytes, str], ...],
    team_query: str,
    min_count_sample: int,
    context_min_sample: int,
):
    raw = _load_uploaded_csvs(file_bytes_and_names)
    clean, col_map = standardize_trackman_columns(raw)
    clean = filter_data_by_team_query(clean, team_query)

    tendencies_long = build_pitcher_count_tendencies(clean, min_pitches=int(min_count_sample))
    team_trends = build_team_level_trends(clean)
    research_context = build_research_context_report(
        tendencies_long,
        min_count_sample=max(5, int(context_min_sample)),
        delta_threshold_pct=10.0,
    )
    return tendencies_long, team_trends, research_context, col_map


if not uploaded_files:
    st.info("Upload CSV files to start.")
    st.stop()

try:
    payload = tuple((f.getvalue(), f.name) for f in uploaded_files)
    tendencies_long, team_trends, research_context, col_map = _build_outputs(
        payload,
        team_query or "",
        int(min_count_sample),
        int(context_min_sample),
    )
    if tendencies_long.empty:
        st.warning("No results after filtering. Try reducing filters or sample thresholds.")
        st.stop()
except Exception as exc:
    st.error(f"Could not process files: {exc}")
    st.stop()

st.success(f"Loaded {len(uploaded_files)} file(s) • Pitchers: {tendencies_long['Pitcher'].nunique()}")
with st.expander("Detected column mapping"):
    st.json(col_map)


tab_profiles, tab_heatmaps, tab_team, tab_strategy = st.tabs(
    ["Pitcher Profiles", "Heatmaps", "Team Trends", "Strategy Context"]
)

with tab_profiles:
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search = st.text_input("Search pitcher", "")
    with c2:
        count = st.selectbox("Count", [""] + ALL_COUNTS, format_func=lambda x: "All" if x == "" else x)
    with c3:
        sort_by = st.selectbox("Sort by", ["Pitcher", "Count"])

    rows = tendencies_long.copy()
    if search.strip():
        rows = rows[rows["Pitcher"].str.lower().str.contains(search.strip().lower(), regex=False)]
    if count:
        rows = rows[rows["Count"] == count]

    if rows.empty:
        st.info("No profile rows match filters.")
    else:
        pitch_types = sorted(rows["PitchType"].dropna().unique().tolist())
        grouped = rows.pivot_table(
            index=["Pitcher", "Count", "TotalPitchesAtCount"],
            columns="PitchType",
            values="ProbabilityPct",
            aggfunc="first",
        ).reset_index()
        for pt in pitch_types:
            if pt not in grouped.columns:
                grouped[pt] = pd.NA

        if sort_by == "Pitcher":
            grouped = grouped.sort_values(["Pitcher", "Count"])
        else:
            grouped["Count"] = pd.Categorical(grouped["Count"], categories=ALL_COUNTS, ordered=True)
            grouped = grouped.sort_values(["Count", "Pitcher"])

        st.dataframe(grouped, use_container_width=True)
        st.download_button(
            "Download profile table (CSV)",
            data=grouped.to_csv(index=False),
            file_name="pitcher_profiles_filtered.csv",
            mime="text/csv",
        )

with tab_heatmaps:
    pitchers = sorted(tendencies_long["Pitcher"].dropna().unique().tolist())
    if not pitchers:
        st.info("No pitchers found.")
    elif not _PLOTTING_OK:
        st.warning("Heatmaps are unavailable because plotting libraries failed to load.")
    else:
        pitcher = st.selectbox("Pitcher", pitchers)
        subset = tendencies_long[tendencies_long["Pitcher"] == pitcher]
        pivot = subset.pivot_table(index="PitchType", columns="Count", values="ProbabilityPct", fill_value=0)
        pivot = pivot.reindex(columns=[c for c in ALL_COUNTS if c in pivot.columns])

        fig, ax = plt.subplots(figsize=(11, 4.5))
        sns.heatmap(pivot, annot=True, fmt=".1f", cmap="Blues", linewidths=0.3, ax=ax)
        ax.set_title(f"{pitcher} - Pitch Type % by Count")
        ax.set_xlabel("Count")
        ax.set_ylabel("Pitch Type")
        st.pyplot(fig)

with tab_team:
    team_count = st.selectbox("Count filter", [""] + ALL_COUNTS, format_func=lambda x: "All" if x == "" else x)
    team_rows = team_trends.copy()
    if team_count:
        team_rows = team_rows[team_rows["Count"] == team_count]
    st.dataframe(team_rows, use_container_width=True)
    st.download_button(
        "Download team trends (CSV)",
        data=team_rows.to_csv(index=False),
        file_name="team_trends_filtered.csv",
        mime="text/csv",
    )

with tab_strategy:
    if research_context.empty:
        st.info("Not enough data for strategy context at current sample thresholds.")
    else:
        p_options = [""] + sorted(research_context["Pitcher"].dropna().unique().tolist())
        l_options = [""] + sorted(research_context["CountLeverage"].dropna().unique().tolist())

        c1, c2 = st.columns(2)
        with c1:
            p_filter = st.selectbox("Pitcher", p_options, format_func=lambda x: "All" if x == "" else x)
        with c2:
            l_filter = st.selectbox("Count leverage", l_options, format_func=lambda x: "All" if x == "" else x)

        res = research_context.copy()
        if p_filter:
            res = res[res["Pitcher"] == p_filter]
        if l_filter:
            res = res[res["CountLeverage"] == l_filter]

        st.dataframe(res, use_container_width=True)
        st.download_button(
            "Download strategy context (CSV)",
            data=res.to_csv(index=False),
            file_name="strategy_context_filtered.csv",
            mime="text/csv",
        )
