"""
Dynamic executive insight generation.
All public functions return HTML strings ready for st.markdown(..., unsafe_allow_html=True).
"""
import pandas as pd
from src.metrics import (
    calc_momentum, calc_hit_rate, calc_consistency_score,
    calc_posting_cadence, calc_comment_to_like_ratio,
)


def insight_block(head: str, body: str) -> str:
    return (
        f'<div class="insight-box">'
        f'<div class="insight-head">{head}</div>'
        f'<div class="insight-body">{body}</div>'
        f'</div>'
    )


def generate_creator_insights(df: pd.DataFrame, name: str) -> str:
    """
    Returns HTML of 5 data-driven insight blocks for a single creator.
    Each block leads with a specific number, followed by a direct conclusion.
    """
    momentum = calc_momentum(df)
    hit_rate = calc_hit_rate(df) * 100
    cadence = calc_posting_cadence(df)
    clr = calc_comment_to_like_ratio(df)
    avg_eng = df["engagement_rate"].mean() * 100

    blocks = []

    # 1. Momentum
    if momentum > 1.1:
        m_label, m_body = "🟢 Accelerating", (
            f"Recent 90-day avg is <b>{momentum:.2f}x</b> the all-time average. "
            f"The current content formula is working — momentum compounds. Do not change strategy mid-run."
        )
    elif momentum < 0.85:
        m_label, m_body = "🔴 Declining", (
            f"Recent 90-day avg is only <b>{momentum:.2f}x</b> the all-time average. "
            f"Channel is contracting. Audit the last 10 videos — identify if the inflection is format, frequency, or external."
        )
    else:
        m_label, m_body = "🟡 Stable", (
            f"Recent 90-day avg is <b>{momentum:.2f}x</b> the all-time average — flat. "
            f"No clear growth signal. This is the moment to experiment with a new format before numbers decline."
        )
    blocks.append(insight_block("MOMENTUM", f"{m_label} — {m_body}"))

    # 2. Hit rate
    if hit_rate > 65:
        hr_body = (
            f"<b>{hit_rate:.0f}%</b> of videos beat the channel median. "
            f"Exceptional consistency — {name} rarely releases a flop. "
            f"This is the most underrated metric for long-term growth."
        )
    elif hit_rate > 45:
        hr_body = (
            f"<b>{hit_rate:.0f}%</b> of videos beat the channel median — average range. "
            f"About half the catalog is underperforming. Identify the bottom quartile and find the pattern."
        )
    else:
        hr_body = (
            f"Only <b>{hit_rate:.0f}%</b> of videos beat the channel median. "
            f"Performance is driven by a few viral hits. The long tail is dead weight pulling averages down."
        )
    blocks.append(insight_block("HIT RATE", hr_body))

    # 3. Format performance
    if "format" in df.columns and df["format"].nunique() > 1:
        fmt = df.groupby("format")["views_per_day"].mean()
        best = fmt.idxmax()
        ratio = fmt.max() / fmt.min() if fmt.min() > 0 else 1.0
        blocks.append(insight_block("FORMAT VERDICT",
            f"<b>{best}</b> generates <b>{ratio:.1f}x</b> more views/day than the other format. "
            f"The algorithm is giving a clear signal — the channel should lean harder into {best.lower()} content. "
            f"{'At {ratio:.1f}x difference, this is not subtle.' if ratio > 3 else 'The gap is real but not decisive — test both formats this quarter.'}"
        ))

    # 4. Posting cadence
    if cadence >= 2.0:
        cad_body = (
            f"<b>{cadence:.1f} videos/week</b>. "
            f"High cadence = top-of-feed dominance. This is how {name} owns the algorithm. "
            f"Consistency at this volume is a structural moat — hard to replicate."
        )
    elif cadence >= 0.7:
        cad_body = (
            f"<b>{cadence:.1f} videos/week</b>. "
            f"Moderate cadence — enough to maintain algorithm signal. "
            f"There's headroom to increase frequency with short-form content without sacrificing production quality."
        )
    else:
        cad_body = (
            f"Only <b>{cadence:.1f} videos/week</b>. "
            f"Low frequency. Each video carries enormous weight — one underperformer tanks the quarter. "
            f"Either accept the risk or introduce short-form to maintain feed presence."
        )
    blocks.append(insight_block("CADENCE", cad_body))

    # 5. Fandom depth
    if clr > 0.06:
        fd_body = (
            f"Comment-to-like ratio: <b>{clr:.3f}</b>. "
            f"The audience argues, debates, and reacts in comments — not just passive clickers. "
            f"This community converts to long-term subscribers and merch buyers."
        )
    elif clr > 0.02:
        fd_body = (
            f"Comment-to-like ratio: <b>{clr:.3f}</b>. "
            f"Moderate engagement depth. Viewers like but rarely comment — typical for broad entertainment content."
        )
    else:
        fd_body = (
            f"Comment-to-like ratio: <b>{clr:.3f}</b>. "
            f"Very passive audience. High reach but low emotional investment. "
            f"Add a question or controversy in the first 30 seconds to activate comments."
        )
    blocks.append(insight_block("FANDOM DEPTH", fd_body))

    return "\n".join(blocks)


def generate_comparison_insights(da: pd.DataFrame, db: pd.DataFrame,
                                  name_a: str, name_b: str) -> str:
    """Returns HTML of 4 comparison insight blocks for two creators."""
    avg_a = da["view_count"].mean() / 1e6
    avg_b = db["view_count"].mean() / 1e6
    eng_a = da["engagement_rate"].mean() * 100
    eng_b = db["engagement_rate"].mean() * 100
    mom_a = calc_momentum(da)
    mom_b = calc_momentum(db)
    cad_a = calc_posting_cadence(da)
    cad_b = calc_posting_cadence(db)

    view_winner = name_a if avg_a >= avg_b else name_b
    view_loser = name_b if avg_a >= avg_b else name_a
    w_avg = max(avg_a, avg_b)
    l_avg = min(avg_a, avg_b)
    ratio = w_avg / l_avg if l_avg > 0 else 1.0

    eng_winner = name_a if eng_a >= eng_b else name_b
    w_eng = max(eng_a, eng_b)
    l_eng = min(eng_a, eng_b)

    mom_winner = name_a if mom_a >= mom_b else name_b
    cad_winner = name_a if cad_a >= cad_b else name_b

    blocks = [
        insight_block("RAW REACH",
            f"{view_winner} leads: <b>{w_avg:.1f}M avg views/video</b> vs <b>{l_avg:.1f}M</b> — "
            f"<b>{ratio:.1f}x gap</b>. "
            + (f"The size difference reflects brand scale and algorithm compounding over years, not just content quality."
               if ratio > 5 else
               f"Near-parity on reach. The real differentiation is engagement depth and content format efficiency.")
        ),
        insight_block("ENGAGEMENT BATTLE",
            f"{eng_winner} wins engagement: <b>{w_eng:.2f}%</b> vs <b>{l_eng:.2f}%</b>. "
            + (f"Different creator leads on engagement vs views — reach doesn't equal community depth. "
               f"Brand deals should value {eng_winner} more per-view than raw numbers suggest."
               if view_winner != eng_winner else
               f"Same creator dominates both metrics — rare. Signals reach dominance AND audience resonance.")
        ),
        insight_block("MOMENTUM (Last 90 Days)",
            f"{mom_winner} is accelerating faster — recent avg is <b>{max(mom_a, mom_b):.2f}x</b> vs "
            f"<b>{min(mom_a, mom_b):.2f}x</b> historical. "
            f"Momentum is the leading indicator. The trailing 90 days predict next 6 months better than total view count."
        ),
        insight_block("POSTING CADENCE",
            f"{cad_winner} posts <b>{max(cad_a, cad_b):.1f} videos/week</b> vs "
            f"<b>{min(cad_a, cad_b):.1f}</b>. "
            + (f"The frequency gap is a structural driver of the reach gap. Volume in the feed compounds over time."
               if max(cad_a, cad_b) > min(cad_a, cad_b) * 1.8 else
               f"Similar cadence — the view gap comes from content formula and brand scale, not volume alone.")
        ),
    ]
    return "\n".join(blocks)
