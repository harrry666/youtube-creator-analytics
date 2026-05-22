"""
Reusable KPI calculation functions for YouTube creator analytics.
All public functions accept a DataFrame with standard column schema and return
a scalar, Series, or dict — no side effects.
"""
import numpy as np
import pandas as pd


# ── Data cleaning ──────────────────────────────────────────────────────────────

def clean_and_validate(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Removes bad rows and flags data quality issues.
    Returns (cleaned_df, list_of_warning_strings).
    """
    warnings: list[str] = []
    df = df.copy()

    # Drop rows with missing or zero views
    bad_views = df["view_count"].isna() | (df["view_count"] <= 0)
    if bad_views.sum():
        warnings.append(f"{bad_views.sum()} videos removed (zero/missing views)")
        df = df[~bad_views]

    # Remove duplicates keeping first occurrence
    dupes = df.duplicated(subset=["video_id"], keep="first")
    if dupes.sum():
        warnings.append(f"{dupes.sum()} duplicate videos removed")
        df = df[~dupes]

    # Cap impossible engagement rates
    over_eng = df["engagement_rate"] > 1.0
    if over_eng.sum():
        warnings.append(f"{over_eng.sum()} engagement rates capped at 100%")
        df.loc[over_eng, "engagement_rate"] = 1.0

    # Note statistical outliers (>4σ) without removing them
    std = df["view_count"].std()
    mean = df["view_count"].mean()
    if std > 0:
        spikes = (np.abs(df["view_count"] - mean) / std > 4).sum()
        if spikes:
            warnings.append(f"{spikes} video(s) flagged as statistical outliers (>4σ views)")

    return df.reset_index(drop=True), warnings


# ── Channel-level KPIs ─────────────────────────────────────────────────────────

def calc_momentum(df: pd.DataFrame, recent_days: int = 90) -> float:
    """
    Recent-90-day avg views / all-time avg views.
    >1.0 means the channel is growing; <1.0 means declining.
    """
    cutoff = df["published_at"].max() - pd.Timedelta(days=recent_days)
    recent_mean = df[df["published_at"] >= cutoff]["view_count"].mean()
    overall_mean = df["view_count"].mean()
    if not overall_mean or pd.isna(recent_mean):
        return 1.0
    return round(float(recent_mean / overall_mean), 3)


def calc_hit_rate(df: pd.DataFrame) -> float:
    """Fraction of videos at or above the channel's median view count."""
    median = df["view_count"].median()
    return round(float((df["view_count"] >= median).mean()), 3)


def calc_consistency_score(df: pd.DataFrame) -> float:
    """
    1 − coefficient_of_variation of views_per_day, clamped to [0, 1].
    Higher = more predictable output quality.
    """
    mean = df["views_per_day"].mean()
    if mean == 0:
        return 0.0
    cv = df["views_per_day"].std() / mean
    return round(max(0.0, 1.0 - min(cv, 1.0)), 3)


def calc_posting_cadence(df: pd.DataFrame) -> float:
    """Average videos published per week across the dataset's date range."""
    span_days = (df["published_at"].max() - df["published_at"].min()).days
    if span_days <= 0:
        return 0.0
    return round(len(df) / (span_days / 7), 2)


def calc_comment_to_like_ratio(df: pd.DataFrame) -> float:
    """Total comments / total likes. Higher = deeper community engagement."""
    likes = df["like_count"].sum() if "like_count" in df.columns else 0
    comments = df["comment_count"].sum() if "comment_count" in df.columns else 0
    return round(float(comments / likes), 4) if likes > 0 else 0.0


# ── Per-video metrics ──────────────────────────────────────────────────────────

def calc_virality_score(df: pd.DataFrame) -> pd.Series:
    """
    Per-video views_per_day / channel avg views_per_day.
    1.0 = average channel performance. >3.0 = viral.
    """
    avg = df["views_per_day"].mean()
    if avg == 0:
        return pd.Series(1.0, index=df.index)
    return (df["views_per_day"] / avg).round(2)


def calc_composite_score(df: pd.DataFrame) -> pd.Series:
    """
    Composite performance score 0–100 per video.
    Weights: views_per_day 40%, engagement_rate 35%, view_count 25%.
    Uses min-max normalisation within the provided DataFrame.
    """
    def norm(s: pd.Series) -> pd.Series:
        lo, hi = s.min(), s.max()
        if hi > lo:
            return (s - lo) / (hi - lo)
        return pd.Series(0.5, index=s.index)

    score = (
        norm(df["views_per_day"]) * 0.40
        + norm(df["engagement_rate"]) * 0.35
        + norm(df["view_count"]) * 0.25
    )
    return (score * 100).round(1)


def performance_grade(score: float) -> str:
    """Maps composite score (0–100) to letter grade S/A/B/C/D."""
    if score >= 85:
        return "S"
    if score >= 70:
        return "A"
    if score >= 50:
        return "B"
    if score >= 30:
        return "C"
    return "D"


# ── Trend comparison ───────────────────────────────────────────────────────────

def period_trend(df: pd.DataFrame, col: str, days: int = 30) -> tuple[float, float, float | None]:
    """
    Returns (recent_mean, prev_mean, pct_change) comparing the last `days`
    days to the preceding `days` days.  pct_change is None when no prev data.
    """
    latest = df["published_at"].max()
    cutoff_recent = latest - pd.Timedelta(days=days)
    cutoff_prev = cutoff_recent - pd.Timedelta(days=days)

    recent_mean = df[df["published_at"] >= cutoff_recent][col].mean()
    prev_mean = df[(df["published_at"] >= cutoff_prev) & (df["published_at"] < cutoff_recent)][col].mean()

    if pd.isna(prev_mean) or prev_mean == 0:
        return float(recent_mean), float(prev_mean) if not pd.isna(prev_mean) else 0.0, None

    pct = (recent_mean - prev_mean) / prev_mean * 100
    return float(recent_mean), float(prev_mean), round(float(pct), 1)


# ── Summary dict ───────────────────────────────────────────────────────────────

def kpi_summary(df: pd.DataFrame) -> dict:
    """Returns a single dict of all key channel KPIs."""
    return {
        "total_videos": len(df),
        "total_views": int(df["view_count"].sum()),
        "avg_views": df["view_count"].mean(),
        "median_views": df["view_count"].median(),
        "avg_vpd": df["views_per_day"].mean(),
        "avg_engagement": df["engagement_rate"].mean(),
        "momentum": calc_momentum(df),
        "hit_rate": calc_hit_rate(df),
        "consistency": calc_consistency_score(df),
        "cadence": calc_posting_cadence(df),
        "comment_to_like": calc_comment_to_like_ratio(df),
    }
