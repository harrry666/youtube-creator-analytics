"""
Anomaly detection: per-video spikes/underperformers and quarterly dips.
"""
import numpy as np
import pandas as pd


# ── Per-video anomalies ────────────────────────────────────────────────────────

def detect_video_anomalies(df: pd.DataFrame, spike_z: float = 2.5,
                            dip_z: float = -1.5) -> pd.DataFrame:
    """
    Adds z_score and anomaly_type columns based on views_per_day z-score.
    anomaly_type values: "viral_spike" | "underperform" | "normal"
    """
    df = df.copy()
    mean = df["views_per_day"].mean()
    std = df["views_per_day"].std()

    if std == 0:
        df["z_score"] = 0.0
        df["anomaly_type"] = "normal"
        return df

    df["z_score"] = ((df["views_per_day"] - mean) / std).round(2)
    df["anomaly_type"] = np.where(
        df["z_score"] >= spike_z, "viral_spike",
        np.where(df["z_score"] <= dip_z, "underperform", "normal")
    )
    return df


ANOMALY_EMOJI = {
    "viral_spike": "🚀",
    "underperform": "📉",
    "normal": "",
}


def anomaly_label(row) -> str:
    """Human-readable label for a video anomaly row."""
    if row["anomaly_type"] == "viral_spike":
        z = row["z_score"]
        if z >= 5:
            return "🚀 Mega Viral (5σ+)"
        if z >= 3:
            return "🔥 Viral (3σ+)"
        return "⬆️ Above-Avg Spike"
    if row["anomaly_type"] == "underperform":
        return "📉 Underperformed"
    return "—"


# ── Quarterly performance dips ─────────────────────────────────────────────────

def detect_quarterly_dips(df: pd.DataFrame, threshold: float = 0.35) -> pd.DataFrame:
    """
    Returns quarters where avg views dropped >threshold from rolling 4-quarter peak.
    Only considers quarters from 2016 onward to avoid sparse early data distortion.
    """
    q = df.groupby("quarter")["view_count"].mean().reset_index()
    q = q[q["quarter"] >= "2016-01-01"].copy()
    q["rolling_max"] = q["view_count"].rolling(4, min_periods=2).max().shift(1)
    q["drop_pct"] = (q["rolling_max"] - q["view_count"]) / q["rolling_max"]
    dips = q[(q["drop_pct"] > threshold) & q["rolling_max"].notna()].copy()
    dips["quarter_str"] = pd.DatetimeIndex(dips["quarter"]).strftime("%Y-%m")
    return dips.reset_index(drop=True)
