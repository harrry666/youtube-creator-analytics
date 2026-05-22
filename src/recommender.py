"""
Rule-based content strategy recommendation engine.
Analyzes patterns in creator data and returns prioritized, actionable recommendations.
"""
import pandas as pd
from src.metrics import calc_posting_cadence, calc_momentum


TITLE_KEYWORDS = [
    "$", "win", "survive", "last to", "vs", "guess", "free",
    "every", "subscribe", "MV", "ft.", "official", "live", "challenge",
    "react", "first", "world", "million", "school", "build",
]

PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _rec(priority: str, title: str, insight: str, action: str) -> dict:
    return {"priority": priority, "title": title, "insight": insight, "action": action}


def generate_recommendations(df: pd.DataFrame, creator_name: str) -> list[dict]:
    """
    Analyzes content patterns and returns a list of recommendation dicts:
      {priority: HIGH|MEDIUM|LOW, title: str, insight: str, action: str}
    Sorted by priority (HIGH first).
    """
    recs: list[dict] = []
    channel_avg_views = df["view_count"].mean()

    # ── 1. Format recommendation ───────────────────────────────────────────────
    if "format" in df.columns and df["format"].nunique() > 1:
        fmt = df.groupby("format")["views_per_day"].mean()
        best, worst = fmt.idxmax(), fmt.idxmin()
        ratio = fmt.max() / fmt.min() if fmt.min() > 0 else 1.0
        if ratio > 1.5:
            priority = "HIGH" if ratio > 3 else "MEDIUM"
            recs.append(_rec(
                priority,
                f"Double Down on {best}",
                f"{best} generates {ratio:.1f}x more views/day than {worst} content.",
                f"Shift content mix toward {best.lower()}. Target 70/30 split next quarter and re-evaluate."
            ))

    # ── 2. Title keyword analysis ──────────────────────────────────────────────
    kw_results = []
    for kw in TITLE_KEYWORDS:
        mask = df["title"].str.contains(kw, case=False, regex=False, na=False)
        if mask.sum() >= 3:
            kw_results.append({
                "kw": kw,
                "avg_views": df[mask]["view_count"].mean(),
                "n": int(mask.sum()),
            })
    if kw_results:
        top_kw = max(kw_results, key=lambda x: x["avg_views"])
        r = top_kw["avg_views"] / channel_avg_views if channel_avg_views > 0 else 1.0
        if r > 1.3:
            recs.append(_rec(
                "HIGH" if r > 2.0 else "MEDIUM",
                f'Use "{top_kw["kw"]}" in More Titles',
                f'Videos with "{top_kw["kw"]}" in the title average {r:.1f}x the channel average (n={top_kw["n"]}).',
                f'Include "{top_kw["kw"]}" in at least 1 of every 3 upcoming video titles.'
            ))

    # ── 3. Video length / format efficiency ───────────────────────────────────
    if "duration_sec" in df.columns:
        d = df[df["view_count"] >= 50_000].copy()
        s_mask = d["duration_sec"] < 120
        l_mask = ~s_mask
        if s_mask.sum() >= 3 and l_mask.sum() >= 3:
            sv = d[s_mask]["views_per_day"].mean()
            lv = d[l_mask]["views_per_day"].mean()
            if sv > lv * 1.5:
                recs.append(_rec(
                    "MEDIUM",
                    "Increase Short-form Volume",
                    f"Short-form (<2 min) gets {sv/lv:.1f}x more views/day than long-form.",
                    "Test 1 Short per long-form video. Use Shorts as top-of-funnel traffic drivers."
                ))
            elif lv > sv * 1.5:
                recs.append(_rec(
                    "MEDIUM",
                    "Prioritize Long-form",
                    f"Long-form (≥2 min) gets {lv/sv:.1f}x more views/day than short-form.",
                    "Reduce Shorts. Invest production budget into 1 high-quality long-form video per week."
                ))

    # ── 4. Posting cadence ────────────────────────────────────────────────────
    cadence = calc_posting_cadence(df)
    if cadence < 0.5:
        recs.append(_rec(
            "HIGH",
            "Increase Posting Frequency",
            f"Current: {cadence:.1f} videos/week. Low cadence costs feed placement and algorithm signal.",
            "Target at least 1 video/week. Even low-production content maintains channel health in the algorithm."
        ))
    elif cadence > 7:
        recs.append(_rec(
            "LOW",
            "Audit Quality vs Volume Balance",
            f"Posting {cadence:.1f} videos/week. Verify bottom-quartile videos aren't hurting watch-time metrics.",
            "Score all videos by composite performance. Cut output if bottom-20% consistently underperforms."
        ))

    # ── 5. Engagement health ──────────────────────────────────────────────────
    avg_eng = df["engagement_rate"].mean() * 100
    if avg_eng < 1.5:
        recs.append(_rec(
            "MEDIUM",
            "Activate Engagement",
            f"Avg engagement: {avg_eng:.2f}%. Below 2% signals passive viewership.",
            "Add a direct question or controversy in the first 30 seconds. Reply to top comments in the first 24 hours."
        ))

    # ── 6. Momentum alert ─────────────────────────────────────────────────────
    momentum = calc_momentum(df)
    if momentum < 0.65:
        recs.append(_rec(
            "HIGH",
            "Address Declining Channel Momentum",
            f"Recent 90-day avg is only {momentum:.2f}x the all-time channel average. Channel is contracting.",
            "Identify the inflection point in the last 15 videos. Was it a format change, posting gap, or external event? "
            "Test a throwback format that previously drove high engagement."
        ))

    # ── 7. Viral hit leverage ─────────────────────────────────────────────────
    if "virality_score" in df.columns:
        viral = df[df["virality_score"] >= 3].nlargest(3, "virality_score")
        if len(viral) > 0:
            top_viral = viral.iloc[0]
            recs.append(_rec(
                "MEDIUM",
                "Replicate Viral Formula",
                f'"{top_viral["title"][:50]}…" had a {top_viral["virality_score"]:.1f}x virality score.',
                "Analyze what made this video viral: title pattern, format, length, topic. "
                "Create a direct follow-up or series based on the same formula within 30 days."
            ))

    if not recs:
        recs.append(_rec(
            "LOW",
            "Channel Performance Is Healthy",
            "No critical issues detected across format, cadence, engagement, or momentum metrics.",
            "Continue current strategy. Focus on incremental A/B testing of thumbnail styles and title formats."
        ))

    return sorted(recs, key=lambda r: PRIORITY_RANK.get(r["priority"], 99))
