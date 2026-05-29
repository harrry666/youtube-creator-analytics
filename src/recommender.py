import pandas as pd
import numpy as np
from scipy import stats
from src.metrics import calc_posting_cadence, calc_momentum


TITLE_KEYWORDS = [
    "$", "win", "survive", "last to", "vs", "guess", "free",
    "every", "subscribe", "MV", "ft.", "official", "live", "challenge",
    "react", "first", "world", "million", "school", "build",
]

PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _rec(priority: str, title: str, insight: str, action: str) -> dict:
    return {"priority": priority, "title": title, "insight": insight, "action": action}


def _corr(x: pd.Series, y: pd.Series) -> tuple[float, float, str]:
    """Returns (r, p, significance_label). Requires >= 10 paired observations."""
    mask = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 10:
        return 0.0, 1.0, "n/a"
    r, p = stats.pearsonr(x[mask], y[mask])
    if p < 0.001:
        sig = "p<0.001"
    elif p < 0.01:
        sig = f"p={p:.3f}"
    elif p < 0.05:
        sig = f"p={p:.2f}"
    else:
        sig = f"p={p:.2f} (not significant)"
    return float(r), float(p), sig


def generate_recommendations(df: pd.DataFrame, creator_name: str) -> list[dict]:
    recs: list[dict] = []
    channel_avg_vpd = df["views_per_day"].mean()

    # ── 1. Duration vs views/day correlation ──────────────────────────────────
    if "duration_sec" in df.columns:
        d = df[df["view_count"] >= 50_000].copy()
        r, p, sig = _corr(d["duration_sec"], d["views_per_day"])
        if p < 0.05 and abs(r) >= 0.1:
            direction = "negatively" if r < 0 else "positively"
            format_rec = "short-form" if r < 0 else "long-form"
            priority = "HIGH" if abs(r) >= 0.4 else "MEDIUM"

            # also compute mean ratio for context
            s_mask = d["duration_sec"] < 120
            if s_mask.sum() >= 3 and (~s_mask).sum() >= 3:
                sv = d[s_mask]["views_per_day"].mean()
                lv = d[~s_mask]["views_per_day"].mean()
                ratio = sv / lv if lv > 0 else 1.0
                ratio_txt = f"Short-form averages {ratio:.1f}x more views/day than long-form."
            else:
                ratio_txt = ""

            recs.append(_rec(
                priority,
                f"Prioritize {format_rec.title()} Content",
                f"Duration {direction} correlates with views/day (r={r:.2f}, {sig}). {ratio_txt}",
                f"Shift content mix toward {format_rec}. Statistical signal is {'strong' if abs(r) >= 0.4 else 'moderate'} — directional evidence supports the change.",
            ))

    # ── 2. Title keyword analysis (with per-keyword correlation) ─────────────
    kw_results = []
    for kw in TITLE_KEYWORDS:
        mask = df["title"].str.contains(kw, case=False, regex=False, na=False)
        if mask.sum() >= 3:
            kw_flag = mask.astype(float)
            r_kw, p_kw, sig_kw = _corr(kw_flag, df["views_per_day"])
            ratio = df[mask]["views_per_day"].mean() / channel_avg_vpd if channel_avg_vpd > 0 else 1.0
            kw_results.append({
                "kw": kw, "r": r_kw, "p": p_kw, "sig": sig_kw,
                "ratio": ratio, "n": int(mask.sum()),
            })

    if kw_results:
        sig_kws = [k for k in kw_results if k["p"] < 0.05 and k["ratio"] > 1.2]
        if sig_kws:
            top = max(sig_kws, key=lambda x: x["ratio"])
            recs.append(_rec(
                "HIGH" if top["ratio"] > 2.0 else "MEDIUM",
                f'Use "{top["kw"]}" in More Titles',
                f'"{top["kw"]}" videos average {top["ratio"]:.1f}x channel views/day (r={top["r"]:.2f}, {top["sig"]}, n={top["n"]}). Correlation is statistically significant.',
                f'Include "{top["kw"]}" in at least 1 of every 3 upcoming titles. Avoid forcing it where the topic doesn\'t fit.',
            ))

    # ── 3. Engagement rate vs virality ────────────────────────────────────────
    if "virality_score" in df.columns and "engagement_rate" in df.columns:
        r_ev, p_ev, sig_ev = _corr(df["engagement_rate"], df["virality_score"])
        avg_eng = df["engagement_rate"].mean() * 100
        if avg_eng < 1.5:
            eng_note = f"Avg engagement is {avg_eng:.2f}% — below the 2% threshold for healthy community signal."
            recs.append(_rec(
                "MEDIUM",
                "Activate Engagement to Drive Virality",
                f"Engagement rate {'correlates with virality (r=' + f'{r_ev:.2f}, {sig_ev})' if p_ev < 0.05 else 'does not significantly correlate with virality for this channel'}. {eng_note}",
                "Add a direct question or controversy in the first 30 seconds. Reply to top comments within 24 hours.",
            ))

    # ── 4. Posting cadence ────────────────────────────────────────────────────
    cadence = calc_posting_cadence(df)
    if cadence < 0.5:
        recs.append(_rec(
            "HIGH",
            "Increase Posting Frequency",
            f"Current cadence: {cadence:.1f} videos/week. Low cadence reduces algorithm feed placement.",
            "Target at least 1 video/week. Even lower-production content maintains channel health.",
        ))
    elif cadence > 7:
        recs.append(_rec(
            "LOW",
            "Audit Quality vs. Volume Balance",
            f"Posting {cadence:.1f} videos/week. Verify high-volume output isn't diluting watch-time metrics.",
            "Score all videos by composite performance. Trim output if bottom-20% consistently underperforms.",
        ))

    # ── 5. Momentum alert ─────────────────────────────────────────────────────
    momentum = calc_momentum(df)
    if momentum < 0.65:
        recs.append(_rec(
            "HIGH",
            "Address Declining Channel Momentum",
            f"Recent 90-day avg is {momentum:.2f}x the all-time channel average. Channel is contracting.",
            "Identify the inflection point in the last 15 videos. Test a throwback format that previously drove high engagement.",
        ))

    # ── 6. Viral hit leverage ─────────────────────────────────────────────────
    if "virality_score" in df.columns:
        viral = df[df["virality_score"] >= 3].nlargest(3, "virality_score")
        if len(viral) > 0:
            top_viral = viral.iloc[0]
            recs.append(_rec(
                "MEDIUM",
                "Replicate Viral Formula",
                f'"{top_viral["title"][:50]}…" had a {top_viral["virality_score"]:.1f}x virality score.',
                "Analyze what made this video spike: title pattern, format, length, topic. "
                "Create a direct follow-up within 30 days.",
            ))

    if not recs:
        recs.append(_rec(
            "LOW",
            "Channel Performance Is Healthy",
            "No critical issues detected across format, cadence, engagement, or momentum metrics.",
            "Continue current strategy. Focus on incremental A/B testing of thumbnail styles and title formats.",
        ))

    return sorted(recs, key=lambda r: PRIORITY_RANK.get(r["priority"], 99))
