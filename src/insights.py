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
            f"Whatever {name} is doing right now is working. Don't change it."
        )
    elif momentum < 0.85:
        m_label, m_body = "🔴 Declining", (
            f"Recent 90-day avg is <b>{momentum:.2f}x</b> the all-time average. "
            f"The channel is losing ground. Look at the last 10 uploads and figure out where it turned."
        )
    else:
        m_label, m_body = "🟡 Stable", (
            f"Recent 90-day avg is <b>{momentum:.2f}x</b> the all-time average. Flat. "
            f"No growth signal right now. Try something different before the numbers start dipping."
        )
    blocks.append(insight_block("MOMENTUM", f"{m_label}. {m_body}"))

    # 2. Hit rate
    if hit_rate > 65:
        hr_body = (
            f"<b>{hit_rate:.0f}%</b> of videos beat the channel median. "
            f"That's unusually consistent. Most creators have a lot more misses mixed in."
        )
    elif hit_rate > 45:
        hr_body = (
            f"<b>{hit_rate:.0f}%</b> of videos beat the channel median. "
            f"About half the catalog is underperforming. Worth digging into what those videos have in common."
        )
    else:
        hr_body = (
            f"<b>{hit_rate:.0f}%</b> of videos beat the channel median. "
            f"A few big hits are carrying the whole channel. Most of the catalog isn't doing much."
        )
    blocks.append(insight_block("HIT RATE", hr_body))

    # 3. Format performance
    if "format" in df.columns and df["format"].nunique() > 1:
        fmt = df.groupby("format")["views_per_day"].mean()
        best = fmt.idxmax()
        ratio = fmt.max() / fmt.min() if fmt.min() > 0 else 1.0
        gap_note = "That gap is big enough to act on." if ratio > 3 else "Worth testing more systematically this quarter."
        blocks.append(insight_block("FORMAT VERDICT",
            f"<b>{best}</b> gets <b>{ratio:.1f}x</b> more views/day than the other format. "
            f"{gap_note}"
        ))

    # 4. Posting cadence
    if cadence >= 2.0:
        cad_body = (
            f"<b>{cadence:.1f} videos/week</b>. "
            f"Staying in the feed that consistently is how {name} keeps the algorithm happy. Hard to compete with."
        )
    elif cadence >= 0.7:
        cad_body = (
            f"<b>{cadence:.1f} videos/week</b>. "
            f"Enough to stay in the algorithm's rotation. "
            f"There's room to add Shorts between uploads without touching the main production schedule."
        )
    else:
        cad_body = (
            f"<b>{cadence:.1f} videos/week</b>. Very low. "
            f"Each upload carries a lot of pressure. One bad video and the whole quarter suffers. "
            f"A few Shorts between releases would help."
        )
    blocks.append(insight_block("CADENCE", cad_body))

    # 5. Fandom depth
    if clr > 0.06:
        fd_body = (
            f"Comment-to-like ratio: <b>{clr:.3f}</b>. "
            f"People are actually talking in the comments, not just watching and leaving. "
            f"That's a more loyal audience than the view numbers suggest."
        )
    elif clr > 0.02:
        fd_body = (
            f"Comment-to-like ratio: <b>{clr:.3f}</b>. "
            f"Viewers like and move on. Not a lot of conversation happening. "
            f"Normal for mainstream entertainment, but there's room to activate the audience more."
        )
    else:
        fd_body = (
            f"Comment-to-like ratio: <b>{clr:.3f}</b>. "
            f"People are mostly watching without reacting. Reach is high but nobody's really invested. "
            f"Opening with a direct question or a hot take in the first 30 seconds usually helps."
        )
    blocks.append(insight_block("FANDOM DEPTH", fd_body))

    return "\n".join(blocks)


def generate_comparison_insights(da: pd.DataFrame, db: pd.DataFrame,
                                  name_a: str, name_b: str,
                                  music_a: bool = False, music_b: bool = False) -> str:
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
    w_avg = max(avg_a, avg_b)
    l_avg = min(avg_a, avg_b)
    ratio = w_avg / l_avg if l_avg > 0 else 1.0

    eng_winner = name_a if eng_a >= eng_b else name_b
    w_eng = max(eng_a, eng_b)
    l_eng = min(eng_a, eng_b)

    either_music = music_a or music_b
    both_music = music_a and music_b

    # ── Block 1: Raw Reach ────────────────────────────────────────────────────
    if either_music and not both_music:
        music_name = name_a if music_a else name_b
        yt_name = name_b if music_a else name_a
        reach_body = (
            f"{view_winner} averages <b>{w_avg:.1f}M views/video</b> vs <b>{l_avg:.1f}M</b>, a {ratio:.1f}x gap. "
            f"Worth noting: {music_name} is a music artist and {yt_name} is a YouTube creator. "
            f"Music MV views build up over decades on their own. The comparison is more complicated than the number makes it look."
        )
    else:
        if ratio > 5:
            reach_note = f"That gap comes from years of brand scale and algorithm compounding, not just better content."
        else:
            reach_note = f"Roughly the same reach. The real difference shows up in engagement and format efficiency."
        reach_body = (
            f"{view_winner} leads: <b>{w_avg:.1f}M avg views/video</b> vs <b>{l_avg:.1f}M</b> ({ratio:.1f}x). "
            f"{reach_note}"
        )

    # ── Block 2: Engagement ───────────────────────────────────────────────────
    if view_winner != eng_winner:
        eng_note = (
            f"Different creator wins on engagement vs views. Reach and community depth don't always go together. "
            f"If you're a brand looking at CPM, {eng_winner} is undervalued by the raw numbers."
        )
    else:
        eng_note = "Same creator wins both. That's unusual. Usually there's a trade-off between reach and engagement. Not here."
    eng_body = (
        f"{eng_winner} wins engagement: <b>{w_eng:.2f}%</b> vs <b>{l_eng:.2f}%</b>. {eng_note}"
    )

    # ── Block 3: Momentum ─────────────────────────────────────────────────────
    if either_music:
        active_name = (name_b if music_a else name_a)
        music_name = (name_a if music_a else name_b)
        active_mom = mom_b if music_a else mom_a
        mom_body = (
            f"{music_name} hasn't uploaded in a while, so their momentum number just reflects old catalog slowly fading. "
            f"{active_name}'s recent 90-day avg is <b>{active_mom:.2f}x</b> historical. "
            f"Momentum only means something for people who are actively uploading."
        )
        if both_music:
            mom_winner = name_a if mom_a >= mom_b else name_b
            mom_body = (
                f"Neither artist is actively uploading. The momentum numbers just reflect how their old catalogs are holding up. "
                f"{mom_winner} has a slightly higher ratio (<b>{max(mom_a,mom_b):.2f}x</b> vs <b>{min(mom_a,mom_b):.2f}x</b>). "
                f"Probably a playlist pick-up or a viral moment, not anything they did."
            )
    else:
        mom_winner = name_a if mom_a >= mom_b else name_b
        mom_body = (
            f"{mom_winner}'s channel is moving faster right now. "
            f"Recent avg is <b>{max(mom_a, mom_b):.2f}x</b> vs <b>{min(mom_a, mom_b):.2f}x</b> historical. "
            f"What happened in the last 90 days tells you more about where these channels are headed than the all-time totals do."
        )

    # ── Block 4: Cadence ──────────────────────────────────────────────────────
    if either_music:
        music_nm = name_a if music_a else name_b
        yt_nm = name_b if music_a else name_a
        yt_cad = cad_b if music_a else cad_a
        if both_music:
            cad_body = (
                f"Neither artist is uploading. Both are running on catalog alone. "
                f"YouTube Shorts made from existing MV clips would be the easiest way back into the algorithm without producing anything new."
            )
        else:
            cad_body = (
                f"{yt_nm} posts <b>{yt_cad:.1f} videos/week</b>. {music_nm} hasn't really uploaded anything. "
                f"Comparing cadence here doesn't make much sense. They're operating on completely different models."
            )
    else:
        cad_winner = name_a if cad_a >= cad_b else name_b
        if max(cad_a, cad_b) > min(cad_a, cad_b) * 1.8:
            cad_note = "More uploads means more chances to show up in the feed. The posting gap is a big part of why the reach gap exists."
        else:
            cad_note = "Similar posting pace. The view difference is about content formula and brand size, not how often they upload."
        cad_body = (
            f"{cad_winner} posts <b>{max(cad_a, cad_b):.1f} videos/week</b> vs <b>{min(cad_a, cad_b):.1f}</b>. "
            f"{cad_note}"
        )

    blocks = [
        insight_block("RAW REACH", reach_body),
        insight_block("ENGAGEMENT BATTLE", eng_body),
        insight_block("MOMENTUM (Last 90 Days)", mom_body),
        insight_block("POSTING CADENCE", cad_body),
    ]
    return "\n".join(blocks)
