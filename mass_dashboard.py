# mass_dashboard.py
# Run with: streamlit run mass_dashboard.py
# Place MASS_DATA.csv in the same folder OR upload your latest CSV inside the app.

from __future__ import annotations
import io
import re
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="MASS Database Dashboard", layout="wide")
DEFAULT_EXPECTED_COLS = {"userid", "Age", "Sex", "Classification"}

# ------------------------- Helpers -------------------------

def _normalize_sex(x: str) -> str:
    if x is None:
        return "Unknown"
    s = str(x).strip().upper()
    if s in {"M", "MALE"}:
        return "M"
    if s in {"F", "FEMALE"}:
        return "F"
    if s in {"NB", "NONBINARY", "NON-BINARY"}:
        return "NB"
    if s in {"O", "OTHER"}:
        return "Other"
    if s == "" or s == "NAN":
        return "Unknown"
    return s

def _clean_classification(x: str, mode: str) -> str:
    s = "" if x is None else str(x)
    if mode == "Raw":
        return s
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _load_csv(upload) -> pd.DataFrame:
    if upload is None:
        try:
            return pd.read_csv("MASS_DATA.csv")
        except Exception:
            st.error("No file uploaded and MASS_DATA.csv not found in the app folder.")
            st.stop()
    return pd.read_csv(io.BytesIO(upload.getvalue()))

def _make_age_groups(age: pd.Series, bin_width: int, start: int, end: int) -> pd.Categorical:
    edges = list(range(start, end + bin_width, bin_width))
    labels = []
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1] - 1
        labels.append(f"{a}-{b}")
    return pd.cut(age, bins=edges, right=False, labels=labels, include_lowest=True)

def _mode_or_unknown(s: pd.Series) -> str:
    s = s.dropna().astype(str)
    if len(s) == 0:
        return "Unknown"
    m = s.mode()
    return str(m.iloc[0]) if len(m) else str(s.iloc[0])

def _max_match_1d(a: np.ndarray, b: np.ndarray, tol: float) -> int:
    """Maximum number of matches between 1D points with |a-b|<=tol using greedy (optimal for 1D)."""
    a = np.sort(a)
    b = np.sort(b)
    i = j = matches = 0
    while i < len(a) and j < len(b):
        if abs(a[i] - b[j]) <= tol:
            matches += 1
            i += 1
            j += 1
        elif a[i] < b[j] - tol:
            i += 1
        else:
            j += 1
    return matches

def _hc_age_band_from_age(age: float) -> str:
    if pd.isna(age):
        return "HC_UnknownAge"
    if age < 35:
        return "HC_lt35"
    if age < 60:
        return "HC_35-60"
    return "HC_60plus"

def _diagnosis_from_classification(cls: str) -> str:
    s = "" if cls is None else str(cls).strip()
    if s.upper().startswith("HC"):
        return "HC"
    return s

def _sex_balance_table(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """
    Returns per-group sex counts + imbalance metrics.
    Works best when df is already participant-level (unique userid).
    """
    tab = (
        df.pivot_table(index=group_col, columns="Sex_clean", values="userid", aggfunc="nunique", fill_value=0)
        .astype(int)
    )
    # Ensure common columns exist
    for col in ["F", "M"]:
        if col not in tab.columns:
            tab[col] = 0
    tab["Total"] = tab.sum(axis=1)
    tab["Female_%"] = np.where(tab["Total"] > 0, (tab["F"] / tab["Total"]) * 100, np.nan)
    tab["Male_%"] = np.where(tab["Total"] > 0, (tab["M"] / tab["Total"]) * 100, np.nan)
    tab["AbsDiff(F-M)"] = (tab["F"] - tab["M"]).abs()
    tab["Ratio(F/M)"] = np.where(tab["M"] > 0, tab["F"] / tab["M"], np.nan)
    return tab.sort_values(["AbsDiff(F-M)", "Total"], ascending=[False, False])

# ------------------------- UI -------------------------

st.title("MASS Database Dashboard")
st.caption("Visualize + QC your database while you collect: Age × Sex × Classification (plus matching planners).")

with st.sidebar:
    st.header("Data")
    upload = st.file_uploader("Upload your CSV", type=["csv"])
    st.markdown("**Expected columns:** `userid`, `Age`, `Sex`, `Classification`")

    st.header("Counting unit")
    count_unit = st.radio(
        "Count participants as…",
        ["Unique participants (userid) — recommended", "Rows (every record)"],
        index=0,
        help="If your CSV contains repeated visits/records per person, choose Unique participants."
    )

    st.header("Cleaning")
    class_mode = st.radio(
        "Classification column",
        ["Cleaned", "Raw"],
        index=0,
        help="Cleaned = strips whitespace and collapses double spaces."
    )
    drop_missing = st.checkbox("Drop rows with missing Age/Sex/Classification", value=True)

    st.header("Healthy Controls handling")
    hc_mode = st.radio(
        "Show HC as…",
        ["Three age bands (HC_lt35, HC_35-60, HC_60plus)", "Single group (HC)"],
        index=0,
        help="Uses Age to assign bands, so inconsistent HC labels in your file won't matter."
    )

    st.header("Age groups (general binning)")
    bin_width = st.slider("Bin width (years)", min_value=2, max_value=20, value=5, step=1)
    start_age = st.number_input("Start age", min_value=0, max_value=120, value=18, step=1)
    end_age = st.number_input("End age", min_value=0, max_value=120, value=90, step=1)
    if end_age <= start_age:
        st.warning("End age must be larger than start age.")
        st.stop()

df_rows = _load_csv(upload)

# Validate columns
missing = DEFAULT_EXPECTED_COLS - set(df_rows.columns)
if missing:
    st.error(f"Missing expected columns: {sorted(missing)}")
    st.stop()

# Standardize
df_rows = df_rows.copy()
df_rows["Sex_clean"] = df_rows["Sex"].apply(_normalize_sex)
df_rows["Classification_clean"] = df_rows["Classification"].apply(lambda x: _clean_classification(x, class_mode))
df_rows["Age"] = pd.to_numeric(df_rows["Age"], errors="coerce")

if drop_missing:
    df_rows = df_rows.dropna(subset=["Age", "Sex_clean", "Classification_clean", "userid"])

df_rows = df_rows[df_rows["Classification_clean"].astype(str).str.strip() != ""]
df_rows["Diagnosis"] = df_rows["Classification_clean"].apply(_diagnosis_from_classification)

# HC band from Age (authoritative)
df_rows["HC_Band"] = df_rows["Age"].apply(_hc_age_band_from_age)
df_rows["HC_Display"] = np.where(df_rows["Diagnosis"] == "HC", df_rows["HC_Band"], df_rows["Classification_clean"])

# Choose primary display grouping
group_col = "HC_Display" if hc_mode.startswith("Three") else "Diagnosis"

# General age bins for plots
df_rows["AgeGroup"] = _make_age_groups(df_rows["Age"], bin_width=int(bin_width), start=int(start_age), end=int(end_age))

# Participant-level vs row-level
if count_unit.startswith("Unique"):
    g = df_rows.groupby("userid", dropna=False)
    inconsist = g.agg(
        age_unique=("Age", lambda x: x.nunique(dropna=True)),
        sex_unique=("Sex_clean", lambda x: x.nunique(dropna=True)),
        class_unique=("Classification_clean", lambda x: x.nunique(dropna=True)),
    ).reset_index()
    inconsistent_ids = inconsist[(inconsist["age_unique"] > 1) | (inconsist["sex_unique"] > 1) | (inconsist["class_unique"] > 1)]

    df = g.agg(
        Age=("Age", "median"),
        Sex_clean=("Sex_clean", _mode_or_unknown),
        Classification_clean=("Classification_clean", _mode_or_unknown),
        Diagnosis=("Diagnosis", _mode_or_unknown),
        HC_Band=("HC_Band", _mode_or_unknown),
        HC_Display=("HC_Display", _mode_or_unknown),
    ).reset_index()
    df["AgeGroup"] = _make_age_groups(df["Age"], bin_width=int(bin_width), start=int(start_age), end=int(end_age))
else:
    inconsistent_ids = pd.DataFrame(columns=["userid", "age_unique", "sex_unique", "class_unique"])
    df = df_rows.copy()

# QC panel
with st.expander("Data quality checks", expanded=True):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Rows in file", f"{len(df_rows):,}")
    c2.metric("Unique participants (userid)", f"{df_rows['userid'].nunique():,}")
    c3.metric("Display groups", f"{df[group_col].nunique():,}")
    c4.metric("Sex categories", f"{df['Sex_clean'].nunique():,}")
    c5.metric("Age range", f"{int(np.nanmin(df['Age']))}–{int(np.nanmax(df['Age']))}")

    extra_rows = int(len(df_rows) - df_rows["userid"].nunique())
    if extra_rows > 0:
        st.info(f"Your file contains {extra_rows:,} extra rows beyond unique userids (possible repeats/visits).")

    bad_age = df_rows[(df_rows["Age"] < 0) | (df_rows["Age"] > 120)]
    if len(bad_age):
        st.warning(f"Out-of-range ages detected: {len(bad_age)} rows (Age < 0 or > 120).")

    unknown_sex = df_rows[df_rows["Sex_clean"].isin(["Unknown"])]
    if len(unknown_sex):
        st.info(f"Sex labeled as 'Unknown' for {len(unknown_sex)} rows.")

    if len(inconsistent_ids):
        st.warning(f"{len(inconsistent_ids)} userids have inconsistent Age/Sex/Classification across rows.")
        st.dataframe(inconsistent_ids.sort_values(["age_unique","sex_unique","class_unique"], ascending=False).head(30), use_container_width=True)

tabs = st.tabs(["Overview", "Sex balance (within group)", "Compare groups", "Matching & recruitment", "Data table"])

# -------------------- Overview --------------------
with tabs[0]:
    left, right = st.columns([1.2, 1])

    with left:
        st.subheader(f"Participants by {group_col}")
        counts = df[group_col].value_counts().rename_axis(group_col).reset_index(name="n")
        fig = px.bar(counts, x=group_col, y="n")
        fig.update_layout(xaxis_tickangle=-35, height=420, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Age distribution (all participants)")
        nb = max(10, int((df["Age"].max() - df["Age"].min()) // max(1, int(bin_width))))
        fig2 = px.histogram(df, x="Age", nbins=nb)
        fig2.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("AgeGroup × Sex counts (overall)")
    pivot_overall = (
        df.pivot_table(index="AgeGroup", columns="Sex_clean", values="userid", aggfunc="nunique", fill_value=0)
        .astype(int)
    )
    st.dataframe(pivot_overall, use_container_width=True)

# -------------------- Sex balance within group --------------------
with tabs[1]:
    st.subheader(f"Sex balance within each {group_col} (your matching rule)")

    # Table
    balance = _sex_balance_table(df, group_col=group_col).reset_index()
    st.dataframe(balance, use_container_width=True)

    # Plot
    plot_df = (
        df.groupby([group_col, "Sex_clean"])["userid"].nunique().reset_index(name="n")
        .sort_values(group_col)
    )
    fig = px.bar(plot_df, x=group_col, y="n", color="Sex_clean", barmode="group")
    fig.update_layout(xaxis_tickangle=-35, height=420, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # Focus: pick a group (e.g., PD) and see age distribution by sex
    st.subheader("Drill-down: one group")
    groups = sorted(df[group_col].dropna().unique().tolist())
    default = "PD" if "PD" in groups else (groups[0] if groups else None)
    chosen = st.selectbox(f"Select a {group_col} to inspect", options=groups, index=(groups.index(default) if default in groups else 0))

    d1 = df[df[group_col] == chosen].copy()
    c1, c2 = st.columns(2)
    with c1:
        sex_counts = d1.groupby("Sex_clean")["userid"].nunique().reset_index(name="n")
        st.markdown("**Sex counts**")
        st.dataframe(sex_counts, use_container_width=True)
    with c2:
        st.markdown("**Age histogram by sex**")
        fig = px.histogram(d1, x="Age", color="Sex_clean", nbins=max(10, int((d1["Age"].max() - d1["Age"].min()) // max(1, int(bin_width)))))
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**AgeGroup × Sex (within this group)**")
    t = d1.pivot_table(index="AgeGroup", columns="Sex_clean", values="userid", aggfunc="nunique", fill_value=0).astype(int)
    st.dataframe(t, use_container_width=True)

# -------------------- Compare groups --------------------
with tabs[2]:
    st.subheader(f"Compare {group_col} by age and sex")

    all_groups = sorted(df[group_col].unique().tolist())
    default_sel = all_groups[:2] if len(all_groups) >= 2 else all_groups
    selected = st.multiselect(f"Choose {group_col} to compare", options=all_groups, default=default_sel)

    if not selected:
        st.info("Select at least one group.")
    else:
        dsel = df[df[group_col].isin(selected)].copy()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Age distributions**")
            fig = px.violin(dsel, x=group_col, y="Age", color=group_col, box=True, points="all")
            fig.update_layout(height=420, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("**Sex counts**")
            sex_counts = dsel.groupby([group_col, "Sex_clean"])["userid"].nunique().reset_index(name="n")
            fig = px.bar(sex_counts, x=group_col, y="n", color="Sex_clean", barmode="group")
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**AgeGroup × Sex heatmap (per selected group)**")
        table = dsel.groupby([group_col, "AgeGroup", "Sex_clean"])["userid"].nunique().reset_index(name="n")
        fig = px.density_heatmap(table, x="AgeGroup", y=group_col, z="n", facet_col="Sex_clean", facet_col_wrap=1)
        fig.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# -------------------- Matching & recruitment --------------------
with tabs[3]:
    st.subheader("Recruitment planners")

    st.markdown("### A) Balance males vs females *within* each group (your current rule)")
    target_mode = st.radio(
        "Target within-group sex balance as…",
        ["Match to current max (bring the smaller sex up to the larger sex within each group)",
         "Custom target per sex (per group)"],
        index=0
    )

    groups = sorted(df[group_col].unique().tolist())
    if target_mode.startswith("Custom"):
        custom_target = st.number_input("Target N per sex (M and F) per group", min_value=0, max_value=500, value=10, step=1)

    # Compute needs per group
    needs_rows = []
    for g in groups:
        d = df[df[group_col] == g]
        nF = int(d[d["Sex_clean"] == "F"]["userid"].nunique())
        nM = int(d[d["Sex_clean"] == "M"]["userid"].nunique())
        if target_mode.startswith("Match"):
            target = max(nF, nM)
        else:
            target = int(custom_target)
        needs_rows.append({
            group_col: g,
            "F": nF,
            "M": nM,
            "target_per_sex": target,
            "need_more_F": max(0, target - nF),
            "need_more_M": max(0, target - nM),
            "abs_diff_FM": abs(nF - nM),
            "total_N": nF + nM
        })
    needs = pd.DataFrame(needs_rows).sort_values(["abs_diff_FM", "total_N"], ascending=[False, False])
    st.dataframe(needs, use_container_width=True)

    st.download_button(
        "Download within-group sex-balance plan (CSV)",
        data=needs.to_csv(index=False).encode("utf-8"),
        file_name="mass_within_group_sex_balance_plan.csv",
        mime="text/csv",
    )

    st.divider()
    st.markdown("### B) Match *across* multiple groups by AgeGroup × Sex (optional)")
    st.caption("Use this if you ever want PD vs HC matched by both age bins and sex (cell-wise matching).")

    selected = st.multiselect(f"Select {group_col} to match across", options=groups, default=[g for g in ["PD", "HC_60plus", "HC_60plus_clean", "HC"] if g in groups][:2])

    if len(selected) < 2:
        st.info("Select at least two groups to compute across-group matching.")
    else:
        d = df[df[group_col].isin(selected)].copy()
        pivot = (
            d.pivot_table(index=["AgeGroup", "Sex_clean"], columns=group_col, values="userid", aggfunc="nunique", fill_value=0)
            .astype(int)
            .sort_index()
        )
        st.markdown("**Counts table (AgeGroup × Sex)**")
        st.dataframe(pivot, use_container_width=True)

        # Per-cell deficits to reach the max group in that cell
        target = pivot[selected].max(axis=1)
        plan = pivot[selected].copy()
        plan["target"] = target.astype(int)
        for c in selected:
            plan[f"need_more__{c}"] = (plan["target"] - plan[c]).clip(lower=0).astype(int)
        st.markdown("**Recruitment planner (fill deficits to reach max per cell)**")
        st.dataframe(plan.reset_index(), use_container_width=True)

        st.download_button(
            "Download across-group AgeGroup×Sex matching plan (CSV)",
            data=plan.reset_index().to_csv(index=False).encode("utf-8"),
            file_name="mass_across_group_matching_plan.csv",
            mime="text/csv",
        )

        # Exact-age matching for TWO groups only
        st.subheader("Exact-age matching (only for 2 selected groups)")
        if len(selected) != 2:
            st.info("Select exactly 2 groups above to see exact-age matching.")
        else:
            a, b = selected[0], selected[1]
            tol = st.slider("Age tolerance for matching (± years)", min_value=0, max_value=10, value=0, step=1)
            d2 = d[d[group_col].isin([a, b])]
            results = []
            for sex in sorted(d2["Sex_clean"].unique().tolist()):
                ages_a = d2[(d2[group_col] == a) & (d2["Sex_clean"] == sex)]["Age"].dropna().to_numpy()
                ages_b = d2[(d2[group_col] == b) & (d2["Sex_clean"] == sex)]["Age"].dropna().to_numpy()
                matches = _max_match_1d(ages_a, ages_b, tol=float(tol))
                results.append({"Sex": sex, f"N_{a}": len(ages_a), f"N_{b}": len(ages_b), "Max matched pairs": matches})
            st.dataframe(pd.DataFrame(results), use_container_width=True)

# -------------------- Data table --------------------
with tabs[4]:
    st.subheader("Data table")
    view_unit = st.radio("Show…", ["Participant-level (unique userid)", "All rows"], index=0)
    base = df if view_unit.startswith("Participant") else df_rows

    groups = sorted(base[group_col].unique().tolist())
    sexes = sorted(base["Sex_clean"].unique().tolist())

    c1, c2, c3 = st.columns(3)
    with c1:
        group_filter = st.multiselect(group_col, options=groups, default=groups)
    with c2:
        sex_filter = st.multiselect("Sex", options=sexes, default=sexes)
    with c3:
        age_min, age_max = st.slider(
            "Age range",
            min_value=int(max(0, np.nanmin(base["Age"]))),
            max_value=int(min(120, np.nanmax(base["Age"]))),
            value=(int(max(0, np.nanmin(base["Age"]))), int(min(120, np.nanmax(base["Age"])))),
        )

    dtab = base[
        base[group_col].isin(group_filter)
        & base["Sex_clean"].isin(sex_filter)
        & (base["Age"] >= age_min)
        & (base["Age"] <= age_max)
    ].copy()

    show_cols = ["userid", "Age", "AgeGroup", "Sex_clean", "Classification_clean", "Diagnosis", "HC_Band", group_col]
    show_cols = [c for c in show_cols if c in dtab.columns]
    st.dataframe(dtab[show_cols], use_container_width=True)

    st.download_button(
        "Download displayed data (CSV)",
        data=dtab.to_csv(index=False).encode("utf-8"),
        file_name="mass_displayed.csv",
        mime="text/csv",
    )
