import re
import io
import json
import colorsys
import urllib.parse
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import feedparser
import streamlit as st
from colorthief import ColorThief

from src.metrics import (
    clean_and_validate, calc_composite_score, calc_virality_score,
    performance_grade, kpi_summary, period_trend,
)
from src.anomaly import detect_video_anomalies, detect_quarterly_dips, anomaly_label, ANOMALY_EMOJI
from src.insights import generate_creator_insights, generate_comparison_insights, insight_block
from src.recommender import generate_recommendations

st.set_page_config(
    page_title="Creator Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Creator config ─────────────────────────────────────────────────────────────
CREATORS = {
    "MrBeast":        {"slug": "mrbeast"},
    "Mark Rober":     {"slug": "markrober"},
    "IShowSpeed":     {"slug": "ishowspeed"},
    "Jay Chou 周杰倫":  {"slug": "jaychou"},
    "JJ Lin 林俊傑":   {"slug": "jjlin"},
}
MUSIC_ARTISTS = {"jaychou", "jjlin"}

CATEGORIES = {
    "Subscribe Bait": r"\bsubscribe\b",
    "Survive/Stranded": r"surviv|strand|island|wilderness",
    "Last To": r"last to",
    "Guess Challenge": r"\bguess\b",
    "Vs/Race": r"\bvs\b|\bracer?d?\b",
    "Win $": r"win \$|,000",
}

TITLE_KEYWORDS = [
    "$", "win", "subscribe", "survive", "last to", "vs", "guess",
    "free", "every", "MV", "ft.", "live", "Official", "周杰倫", "演唱會", "林俊傑",
]

GRADE_COLORS = {"S": "#FFD700", "A": "#22C55E", "B": "#3B82F6", "C": "#F59E0B", "D": "#EF4444"}
PRIORITY_COLORS = {"HIGH": "#EF4444", "MEDIUM": "#F59E0B", "LOW": "#22C55E"}


# ── Color extraction ───────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def extract_accent_color(avatar_url: str) -> str:
    try:
        r = requests.get(avatar_url, timeout=5)
        ct = ColorThief(io.BytesIO(r.content))
        palette = ct.get_palette(color_count=8, quality=1)
        best, best_score = palette[0], -1
        for rgb in palette:
            rv, gv, bv = [x / 255 for x in rgb]
            h, s, v = colorsys.rgb_to_hsv(rv, gv, bv)
            score = s * v if v > 0.35 and s > 0.2 else 0
            if score > best_score:
                best, best_score = rgb, score
        # ensure minimum brightness
        rv, gv, bv = [x / 255 for x in best]
        h, s, v = colorsys.rgb_to_hsv(rv, gv, bv)
        v = max(v, 0.55)
        s = max(s, 0.4)
        rgb_bright = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))
        return "#{:02x}{:02x}{:02x}".format(*rgb_bright)
    except Exception:
        return "#FF0000"


# ── CSS design system ──────────────────────────────────────────────────────────
def build_css(ac: str, banner_url: str = "") -> str:
    bg_css = f"""
    .stApp {{
        background-image: url('{banner_url}');
        background-size: cover;
        background-attachment: fixed;
        background-position: center top;
    }}
    .stApp::before {{
        content: '';
        position: fixed;
        inset: 0;
        background: rgba(6, 6, 15, 0.72);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        z-index: 0;
        pointer-events: none;
    }}
    """ if banner_url else ""

    return f"""<style>
{bg_css}
[data-testid="stSidebar"] {{
    background: rgba(8, 8, 20, 0.82);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.07);
}}
[data-testid="stSidebar"] .stMarkdown p {{ color: #94A3B8; font-size: 0.8rem; }}
[data-testid="stMain"] > div {{
    position: relative; z-index: 1;
}}
.kpi-card {{
    background: rgba(15, 15, 30, 0.65);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 20px 16px; text-align: center; height: 100%; min-height: 110px;
}}
.kpi-label {{ color: #94A3B8; font-size: 0.62rem; text-transform: uppercase;
              letter-spacing: 2px; margin-bottom: 8px; }}
.kpi-value {{ color: {ac}; font-size: 2.2rem; font-weight: 900; line-height: 1; }}
.kpi-sub   {{ color: #64748B; font-size: 0.7rem; margin-top: 6px; }}
.kpi-trend-up   {{ color: #22C55E; font-size: 0.7rem; font-weight: 700; margin-top: 4px; }}
.kpi-trend-down {{ color: #EF4444; font-size: 0.7rem; font-weight: 700; margin-top: 4px; }}
.kpi-trend-flat {{ color: #64748B; font-size: 0.7rem; margin-top: 4px; }}
.adv-card {{
    background: rgba(10, 10, 22, 0.65);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 16px; text-align: center;
}}
.adv-label {{ color: #64748B; font-size: 0.6rem; text-transform: uppercase;
              letter-spacing: 1.5px; margin-bottom: 6px; }}
.adv-value {{ color: #E2E8F0; font-size: 1.6rem; font-weight: 800; line-height: 1; }}
.adv-sub   {{ color: #475569; font-size: 0.65rem; margin-top: 4px; }}
.sec-head {{
    font-size: 0.82rem; font-weight: 700; color: {ac};
    border-left: 3px solid {ac}; padding-left: 10px;
    margin: 24px 0 12px; text-transform: uppercase; letter-spacing: 1px;
}}
.insight-box {{
    background: rgba(15, 15, 30, 0.65);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 18px 22px; margin: 8px 0;
}}
.insight-head {{
    color: {ac}; font-size: 0.65rem; font-weight: 800;
    text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px;
}}
.insight-body {{ color: #CBD5E1; font-size: 0.9rem; line-height: 1.7; }}
.rec-card {{
    background: rgba(15, 15, 30, 0.65);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-left: 4px solid; border-radius: 10px;
    padding: 16px 20px; margin: 10px 0;
    border-top: 1px solid rgba(255,255,255,0.06);
    border-right: 1px solid rgba(255,255,255,0.06);
    border-bottom: 1px solid rgba(255,255,255,0.06);
}}
.rec-priority {{ font-size: 0.62rem; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; }}
.rec-title   {{ font-size: 0.97rem; font-weight: 700; color: #E2E8F0; margin: 5px 0 4px; }}
.rec-insight {{ color: #94A3B8; font-size: 0.85rem; margin-bottom: 8px; }}
.rec-action  {{ color: #CBD5E1; font-size: 0.85rem; }}
.rec-action::before {{ content: "→ "; color: {ac}; font-weight: 700; }}
.thumb-title {{ font-size: 0.7rem; color: #94A3B8; margin-top: 6px; line-height: 1.3;
               height: 2.4em; overflow: hidden; }}
.thumb-stat  {{ font-size: 0.78rem; color: {ac}; font-weight: 700; margin-top: 3px; }}
.thumb-badge {{ font-size: 0.65rem; color: #7C3AED; margin-top: 2px; }}
.dip-row {{
    background: rgba(15, 15, 30, 0.65);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px; padding: 12px 16px; margin: 6px 0;
}}
.badge-ok   {{ background: rgba(20,83,45,0.8); color: #4ADE80; padding: 3px 10px;
               border-radius: 99px; font-size: 0.65rem; font-weight: 700; }}
.badge-warn {{ background: rgba(66,32,6,0.8); color: #FCD34D; padding: 3px 10px;
               border-radius: 99px; font-size: 0.65rem; font-weight: 700; }}
.page-title {{ font-size: 1.7rem; font-weight: 900; color: #E2E8F0; margin: 0; line-height: 1.1; }}
.page-sub   {{ color: #94A3B8; font-size: 0.8rem; margin-top: 4px; }}
.hero-section {{
    background: linear-gradient(180deg, rgba(0,0,0,0.1) 0%, rgba(6,6,15,0.85) 100%);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.07);
    padding: 32px 36px 24px;
    margin-bottom: 24px;
    text-align: center;
}}
.hero-name {{
    font-size: 3rem; font-weight: 900; color: #FFFFFF;
    letter-spacing: -1px; line-height: 1; margin: 14px 0 6px;
    text-shadow: 0 2px 20px rgba(0,0,0,0.6);
}}
.hero-sub {{
    color: rgba(255,255,255,0.5); font-size: 0.85rem;
    text-transform: uppercase; letter-spacing: 2px;
}}
.hero-kpi-row {{
    display: flex; justify-content: center; gap: 40px; margin-top: 20px;
}}
.hero-kpi {{
    text-align: center;
}}
.hero-kpi-val {{
    font-size: 1.8rem; font-weight: 900; color: {ac};
    line-height: 1;
}}
.hero-kpi-label {{
    font-size: 0.6rem; color: rgba(255,255,255,0.45);
    text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px;
}}
</style>"""


# ── UI components ──────────────────────────────────────────────────────────────
def kpi_card(label: str, value: str, sub: str, trend_pct=None) -> str:
    if trend_pct is None:
        trend_html = '<div class="kpi-trend-flat">—</div>'
    elif trend_pct >= 0:
        trend_html = f'<div class="kpi-trend-up">▲ {abs(trend_pct):.1f}% vs prev 30d</div>'
    else:
        trend_html = f'<div class="kpi-trend-down">▼ {abs(trend_pct):.1f}% vs prev 30d</div>'
    return (f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-sub">{sub}</div>'
            f'{trend_html}</div>')


def adv_card(label: str, value: str, sub: str, color: str = "#E2E8F0") -> str:
    return (f'<div class="adv-card">'
            f'<div class="adv-label">{label}</div>'
            f'<div class="adv-value" style="color:{color}">{value}</div>'
            f'<div class="adv-sub">{sub}</div></div>')


def rec_card(rec: dict) -> str:
    p = rec["priority"]
    color = PRIORITY_COLORS.get(p, "#888")
    emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(p, "⚪")
    return (f'<div class="rec-card" style="border-left-color:{color}">'
            f'<div class="rec-priority" style="color:{color}">{emoji} {p}</div>'
            f'<div class="rec-title">{rec["title"]}</div>'
            f'<div class="rec-insight">{rec["insight"]}</div>'
            f'<div class="rec-action">{rec["action"]}</div></div>')


def so_what_block(obs: str, imp: str, rec: str, accent_color: str = "#FF0000") -> str:
    return f"""
    <div style="background:#12122A;border:1px solid #2A2A4A;border-radius:8px;
                padding:16px 20px;margin-bottom:12px;">
      <div style="display:flex;gap:24px;align-items:flex-start;">
        <div style="min-width:110px;">
          <div style="color:#666;font-size:0.68rem;text-transform:uppercase;
                      letter-spacing:0.1em;margin-bottom:2px;">Observation</div>
          <div style="color:#E0E0F0;font-size:0.88rem;line-height:1.45;">{obs}</div>
        </div>
        <div style="color:#333;font-size:1.2rem;padding-top:14px;">→</div>
        <div style="min-width:140px;">
          <div style="color:#666;font-size:0.68rem;text-transform:uppercase;
                      letter-spacing:0.1em;margin-bottom:2px;">Implication</div>
          <div style="color:#E0E0F0;font-size:0.88rem;line-height:1.45;">{imp}</div>
        </div>
        <div style="color:#333;font-size:1.2rem;padding-top:14px;">→</div>
        <div style="flex:1;">
          <div style="color:{accent_color};font-size:0.68rem;text-transform:uppercase;
                      letter-spacing:0.1em;margin-bottom:2px;">Recommendation</div>
          <div style="color:#F0F0FF;font-size:0.88rem;font-weight:500;
                      line-height:1.45;">{rec}</div>
        </div>
      </div>
    </div>"""


def generate_so_what(df: pd.DataFrame, creator_name: str, ac: str) -> str:
    from src.metrics import calc_momentum, calc_posting_cadence

    blocks = []

    # Block 1: Momentum
    momentum = calc_momentum(df)
    if momentum >= 1.1:
        mom_obs = f"90-day avg views/day is <b>{momentum:.2f}x</b> the all-time channel average."
        mom_imp = "Channel is actively accelerating — algorithm is feeding it."
        mom_rec = "Double down on what's working now. Don't experiment mid-momentum."
    elif momentum >= 0.85:
        mom_obs = f"90-day avg views/day is <b>{momentum:.2f}x</b> the all-time average."
        mom_imp = "Channel is stable but not growing. Plateau risk if no format change."
        mom_rec = "Test one new content format this quarter. Measure against current baseline."
    else:
        mom_obs = f"90-day avg views/day is only <b>{momentum:.2f}x</b> the all-time average."
        mom_imp = "Channel is declining. Recent uploads are underperforming the historical baseline."
        mom_rec = "Identify the inflection point. Revert to the last format that drove above-baseline performance."
    blocks.append(so_what_block(mom_obs, mom_imp, mom_rec, ac))

    # Block 2: Format efficiency
    if "duration_sec" in df.columns and "format" in df.columns:
        grp = df.groupby("format")["views_per_day"].mean()
        if len(grp) > 1:
            best_fmt = grp.idxmax()
            worst_fmt = grp.idxmin()
            ratio = grp.max() / grp.min() if grp.min() > 0 else 1.0
            short_pct = (df["format"] == "Short-form (<2 min)").mean() * 100
            if ratio > 1.5:
                fmt_obs = f"<b>{best_fmt}</b> generates <b>{ratio:.1f}x</b> more views/day than {worst_fmt}."
                fmt_imp = f"Format is the biggest lever — bigger than topic or posting frequency."
                if "Short-form" in best_fmt:
                    fmt_rec = f"Short-form is {short_pct:.0f}% of uploads. Every 10% shift toward Shorts is an estimated {ratio*0.1:.1f}x lift on channel-wide avg views/day."
                else:
                    fmt_rec = f"Long-form dominates. Cut Shorts production. Reinvest in higher-quality long-form."
                blocks.append(so_what_block(fmt_obs, fmt_imp, fmt_rec, ac))

    # Block 3: Content decay
    AGE_BUCKETS = [(0,30),(31,90),(91,365),(366,730),(731,9999)]
    bucket_avgs = []
    for lo, hi in AGE_BUCKETS:
        mask = (df["video_age_days"] >= lo) & (df["video_age_days"] <= hi)
        if mask.sum() >= 3:
            bucket_avgs.append(df[mask]["views_per_day"].mean())
    if len(bucket_avgs) >= 2:
        decay_ratio = bucket_avgs[0] / bucket_avgs[-1] if bucket_avgs[-1] > 0 else 0
        if decay_ratio > 10:
            dec_obs = f"Fresh content (0–30d) averages <b>{decay_ratio:.0f}x</b> more views/day than content aged 2+ years."
            dec_imp = "Catalog has almost no long-tail value. Revenue is 100% dependent on new upload cadence."
            dec_rec = "Treat every upload window as critical. A 2-week posting gap costs disproportionately — model the revenue cliff."
        elif decay_ratio > 3:
            dec_obs = f"Fresh content averages <b>{decay_ratio:.1f}x</b> more views/day than aged content."
            dec_imp = "Moderate decay. Some catalog value exists but it doesn't compound meaningfully."
            dec_rec = "Build a Shorts strategy to reactivate old catalog clips. Zero production cost, potential long-tail upside."
        else:
            dec_obs = f"Content decay ratio is only <b>{decay_ratio:.1f}x</b> — one of the flattest in the dataset."
            dec_imp = "Evergreen content. Catalog compounds over time — each video is a long-term asset."
            dec_rec = "Prioritize production quality over upload frequency. One strong video outperforms five average ones."
        blocks.append(so_what_block(dec_obs, dec_imp, dec_rec, ac))

    return "".join(blocks)


# ── Data helpers ───────────────────────────────────────────────────────────────
def parse_sec(s: str) -> int:
    if not isinstance(s, str):
        return 0
    h = re.search(r"(\d+)H", s)
    m = re.search(r"(\d+)M", s)
    sec = re.search(r"(\d+)S", s)
    return ((int(h.group(1)) * 3600 if h else 0)
            + (int(m.group(1)) * 60 if m else 0)
            + (int(sec.group(1)) if sec else 0))


def categorize(title: str) -> str:
    t = title.lower()
    for label, pat in CATEGORIES.items():
        if re.search(pat, t):
            return label
    return "Other"


@st.cache_data(show_spinner=False)
def load_and_enrich(slug: str):
    df = pd.read_csv(f"data/processed/{slug}_metrics.csv")
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True).dt.tz_localize(None)
    df["duration_sec"] = df["duration"].apply(parse_sec)
    df["is_short"] = df["duration_sec"] < 120
    df["format"] = df["is_short"].map({True: "Short-form (<2 min)", False: "Long-form (≥2 min)"})
    df["category"] = df["title"].apply(categorize)
    df["quarter"] = df["published_at"].dt.to_period("Q").dt.to_timestamp()
    df, warnings = clean_and_validate(df)
    df["virality_score"] = calc_virality_score(df)
    df["composite_score"] = calc_composite_score(df)
    df["grade"] = df["composite_score"].apply(performance_grade)
    df = detect_video_anomalies(df)
    return df.sort_values("published_at").reset_index(drop=True), warnings


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_news(query: str, from_date: str, to_date: str):
    year = str(from_date)[:4]
    q = urllib.parse.quote(f"{query} {year}")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        feed = feedparser.parse(r.content)
        return [(e.title, e.link, e.get("published", "")) for e in feed.entries[:5]]
    except Exception:
        return []


def generate_text_report(df, creator, channel_info, kpis, recs, dips) -> str:
    today = date.today().isoformat()
    top5 = df.nlargest(5, "views_per_day")
    anom = df[df["anomaly_type"] != "normal"].nlargest(5, "z_score")
    lines = [
        "=" * 60,
        "CREATOR ANALYTICS REPORT",
        "=" * 60,
        f"Creator   : {channel_info.get('name', creator)}",
        f"Generated : {today}",
        f"Period    : {df['published_at'].min().date()} → {df['published_at'].max().date()}",
        f"Videos    : {kpis['total_videos']:,}",
        "",
        "KEY METRICS",
        "-" * 40,
        f"Avg Views         : {kpis['avg_views']/1e6:.1f}M",
        f"Median Views      : {kpis['median_views']/1e6:.1f}M",
        f"Avg Views/Day     : {kpis['avg_vpd']/1e6:.2f}M",
        f"Avg Engagement    : {kpis['avg_engagement']*100:.2f}%",
        f"Momentum Index    : {kpis['momentum']:.2f}x",
        f"Posting Cadence   : {kpis['cadence']:.1f} videos/week",
        "",
        "TOP 5 VIDEOS (by Views/Day)",
        "-" * 40,
    ]
    for i, (_, row) in enumerate(top5.iterrows(), 1):
        lines.append(f"{i}. {row['title'][:55]}")
        lines.append(f"   Views/Day: {row['views_per_day']/1e6:.2f}M  |  "
                     f"Engagement: {row['engagement_rate']*100:.2f}%  |  "
                     f"Score: {row['composite_score']:.0f}/100 ({row['grade']})")
    lines.append("")
    if not anom.empty:
        lines += ["ANOMALIES DETECTED", "-" * 40]
        for _, row in anom.iterrows():
            lines.append(f"{ANOMALY_EMOJI.get(row['anomaly_type'],'')} "
                         f"[z={row['z_score']:+.1f}] {row['title'][:55]}")
        lines.append("")
    if not dips.empty:
        lines += ["PERFORMANCE DIPS", "-" * 40]
        for _, row in dips.iterrows():
            lines.append(f"  {row['quarter_str']}  drop={row['drop_pct']*100:.0f}% from peak")
        lines.append("")
    lines += ["RECOMMENDATIONS", "-" * 40]
    for rec in recs:
        lines.append(f"[{rec['priority']}] {rec['title']}")
        lines.append(f"  → {rec['action']}")
        lines.append("")
    lines += ["=" * 60, "Generated by Creator Analytics · YouTube Data API v3"]
    return "\n".join(lines)


def chart_cfg(is_music: bool) -> dict:
    return dict(
        template="plotly_dark",
        paper_bgcolor="#121212" if is_music else "#0A0A0F",
        plot_bgcolor="#1E1E1E" if is_music else "#14141C",
        font_color="#E2E8F0",
        margin=dict(l=0, r=0, t=40, b=0),
    )


def accent(is_music: bool) -> str:
    return "#1DB954" if is_music else "#FF0000"


try:
    all_channel_info = json.load(open("data/channel_info.json"))
except Exception:
    all_channel_info = {}


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📊 Creator Analytics")
    st.caption("YouTube Data API v3 · Portfolio Project")
    st.divider()

    creator = st.selectbox("**Creator**", list(CREATORS.keys()))
    slug = CREATORS[creator]["slug"]
    is_music = slug in MUSIC_ARTISTS
    channel_info = all_channel_info.get(slug, {"name": creator, "avatar": "", "banner": ""})
    avatar_url = channel_info.get("avatar", "")
    AC = extract_accent_color(avatar_url) if avatar_url else accent(is_music)

    st.divider()
    st.markdown("**Filters**")

    with st.spinner("Loading…"):
        df_raw, data_warnings = load_and_enrich(slug)
    min_d = df_raw["published_at"].min().date()
    max_d = df_raw["published_at"].max().date()

    date_range = st.slider("Date range", min_value=min_d, max_value=max_d,
                           value=(min_d, max_d), format="YYYY-MM")
    fmt_filter = st.radio("Format", ["All", "Short-form (<2 min)", "Long-form (≥2 min)"],
                          horizontal=True)
    min_views = st.select_slider(
        "Min views",
        options=[0, 100_000, 500_000, 1_000_000, 5_000_000, 10_000_000],
        value=0,
        format_func=lambda x: "None" if x == 0 else f"{x/1e6:.1f}M",
    )
    top_n = st.slider("Top N for charts", 5, 20, 10)

    st.divider()
    st.markdown("**Data Health**")
    if data_warnings:
        for w in data_warnings:
            st.markdown(f'<span class="badge-warn">⚠ {w}</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-ok">✓ All checks passed</span>', unsafe_allow_html=True)
    st.caption(f"{len(df_raw):,} videos · {min_d} → {max_d}")
    if channel_info.get("avatar"):
        st.image(channel_info["avatar"], width=56)


# ── Apply global filters ───────────────────────────────────────────────────────
df_f = df_raw[
    (df_raw["published_at"].dt.date >= date_range[0])
    & (df_raw["published_at"].dt.date <= date_range[1])
    & (df_raw["view_count"] >= min_views)
].copy()
if fmt_filter != "All":
    df_f = df_f[df_f["format"] == fmt_filter]
df_f = df_f.reset_index(drop=True)

# Re-normalise scores on filtered subset
if len(df_f) > 1:
    df_f["virality_score"] = calc_virality_score(df_f)
    df_f["composite_score"] = calc_composite_score(df_f)
    df_f["grade"] = df_f["composite_score"].apply(performance_grade)
    df_f = detect_video_anomalies(df_f)

# ── Inject CSS ─────────────────────────────────────────────────────────────────
banner_url = channel_info.get("banner", "")
st.markdown(build_css(AC, banner_url), unsafe_allow_html=True)

# ── Hero section ───────────────────────────────────────────────────────────────
kpis = kpi_summary(df_f)
_, _, vpd_trend  = period_trend(df_f, "views_per_day")
_, _, eng_trend  = period_trend(df_f, "engagement_rate")
_, _, view_trend = period_trend(df_f, "view_count")

suffix = ""
if fmt_filter != "All":
    suffix += f" · {fmt_filter}"
if min_views > 0:
    suffix += f" · ≥{min_views/1e6:.1f}M views"

hero_avatar = ""
if channel_info.get("avatar"):
    hero_avatar = (
        f'<img src="{channel_info["avatar"]}" '
        f'style="width:88px;height:88px;border-radius:50%;'
        f'border:3px solid {AC};object-fit:cover;'
        f'box-shadow:0 0 24px {AC}55;" />'
    )

hero_kpis = [
    ("VIDEOS", f"{kpis['total_videos']:,}"),
    ("AVG VIEWS", f"{kpis['avg_views']/1e6:.1f}M"),
    ("VIEWS/DAY", f"{kpis['avg_vpd']/1e6:.2f}M"),
    ("ENGAGEMENT", f"{kpis['avg_engagement']*100:.2f}%"),
]
hero_kpi_html = "".join(
    f'<div class="hero-kpi">'
    f'<div class="hero-kpi-val">{val}</div>'
    f'<div class="hero-kpi-label">{label}</div>'
    f'</div>'
    for label, val in hero_kpis
)

st.markdown(
    f'<div class="hero-section">'
    f'{hero_avatar}'
    f'<div class="hero-name">{channel_info.get("name", creator)}</div>'
    f'<div class="hero-sub">{len(df_f):,} videos · {date_range[0]} → {date_range[1]}{suffix}</div>'
    f'<div class="hero-kpi-row">{hero_kpi_html}</div>'
    f'</div>',
    unsafe_allow_html=True,
)


if len(df_f) == 0:
    st.warning("No videos match the current filters. Adjust the filters in the sidebar.")
    st.stop()

# ── KPI row 2: Advanced metrics ────────────────────────────────────────────────
momentum = kpis["momentum"]
mom_color = "#22C55E" if momentum > 1.1 else ("#EF4444" if momentum < 0.85 else "#F59E0B")
mom_label = "↑ Growing" if momentum > 1.1 else ("↓ Declining" if momentum < 0.85 else "→ Stable")
viral_hit_rate = (df_f["views_per_day"] >= df_f["views_per_day"].mean() * 2).mean() * 100
clr = df_f["comment_rate"].mean() / df_f["like_rate"].mean() if df_f["like_rate"].mean() > 0 else 0

adv_cols = st.columns(4)
if is_music:
    days_since = int(df_f["video_age_days"].min())
    total_views = df_f["view_count"].sum()
    adv_data = [
        ("CATALOG SIZE",      f"{len(df_f):,}",            "total music videos",           "#E2E8F0"),
        ("CATALOG VIEWS",     f"{total_views/1e9:.2f}B" if total_views >= 1e9 else f"{total_views/1e6:.0f}M",
                              "lifetime accumulated",                                        AC),
        ("LAST RELEASE",      f"{days_since}d ago",        "days since newest upload",      "#F59E0B" if days_since > 365 else "#22C55E"),
        ("COMMENT / LIKE",    f"{clr:.2f}x",               "fandom depth proxy",            "#E2E8F0"),
    ]
else:
    adv_data = [
        ("MOMENTUM INDEX",    f"{momentum:.2f}x",          f"{mom_label} (90-day)",         mom_color),
        ("VIRAL HIT RATE",    f"{viral_hit_rate:.0f}%",    "videos > 2x channel avg",       AC),
        ("CADENCE",           f"{kpis['cadence']:.1f}/wk", "avg videos per week",           "#E2E8F0"),
        ("COMMENT / LIKE",    f"{clr:.2f}x",               "fandom depth proxy",            "#E2E8F0"),
    ]
for col, (label, val, sub, color) in zip(adv_cols, adv_data):
    col.markdown(adv_card(label, val, sub, color), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Top 5 thumbnails ──────────────────────────────────────────────────────────
st.markdown(f'<div class="sec-head">🔥 Top 5 — Views Per Day</div>', unsafe_allow_html=True)
top5 = df_f.nlargest(5, "views_per_day")
thumb_cols = st.columns(5)
for col, (_, row) in zip(thumb_cols, top5.iterrows()):
    thumb = f"https://img.youtube.com/vi/{row['video_id']}/hqdefault.jpg"
    url   = f"https://www.youtube.com/watch?v={row['video_id']}"
    badge = ANOMALY_EMOJI.get(row.get("anomaly_type", "normal"), "")
    with col:
        st.markdown(
            f'<a href="{url}" target="_blank">'
            f'<img src="{thumb}" style="width:100%;border-radius:10px;display:block;"></a>'
            f'<div class="thumb-title">{row["title"]}</div>'
            f'<div class="thumb-stat">{row["views_per_day"]/1e6:.1f}M/day</div>'
            f'<div class="thumb-badge">{badge} Score: {row["composite_score"]:.0f} ({row["grade"]})</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

CB = chart_cfg(is_music)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Overview",
    "📈 Performance",
    "🕰️ Career Arc",
    "🔍 Content DNA",
    "💡 Insights & Recs",
    "⚔️ Compare",
    "📤 Export",
])


# ── TAB 1: Overview ────────────────────────────────────────────────────────────
with tab1:
    st.markdown(
        """
        <div style="background:#12122A;border-left:4px solid #FF0000;padding:14px 18px;
                    border-radius:6px;margin-bottom:18px;">
          <div style="color:#A0A0C0;font-size:0.75rem;letter-spacing:0.08em;
                      text-transform:uppercase;margin-bottom:4px;">Research Question</div>
          <div style="color:#F0F0FF;font-size:1.05rem;font-weight:600;line-height:1.5;">
            What content strategies and channel behaviors best predict sustainable view velocity —
            and how do top YouTube creators trade off <span style="color:#FF0000;">reach</span>
            versus <span style="color:#1DB954;">community depth</span>?
          </div>
          <div style="color:#8888AA;font-size:0.82rem;margin-top:8px;">
            Hypothesis: high-cadence creators (Speed) maximize reach via volume;
            low-cadence creators (Rober) maximize depth via production quality.
            No single creator dominates both axes simultaneously.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="sec-head">Performance Leaderboard — Top {top_n} by Composite Score</div>',
                unsafe_allow_html=True)
    lb = df_f.nlargest(top_n, "composite_score").copy()
    lb["Rank"]       = range(1, len(lb) + 1)
    lb["Title"]      = lb["title"].str[:55] + "…"
    lb["Published"]  = lb["published_at"].dt.strftime("%Y-%m-%d")
    lb["Views"]      = (lb["view_count"] / 1e6).round(1).astype(str) + "M"
    lb["Views/Day"]  = (lb["views_per_day"] / 1e6).round(2).astype(str) + "M"
    lb["Engagement"] = (lb["engagement_rate"] * 100).round(2).astype(str) + "%"
    lb["Virality"]   = lb["virality_score"].astype(str) + "x"
    lb["Score"]      = lb["composite_score"]
    lb["Grade"]      = lb["grade"]
    lb["⚡"]          = lb["anomaly_type"].map(ANOMALY_EMOJI).fillna("")
    st.dataframe(
        lb[["Rank","Title","Published","Views","Views/Day","Engagement","Virality","Score","Grade","⚡"]],
        use_container_width=True, hide_index=True,
        column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100)},
    )

    st.markdown(f'<div class="sec-head">⚡ Anomaly Report — Spikes & Underperformers</div>',
                unsafe_allow_html=True)
    anom = df_f[df_f["anomaly_type"] != "normal"].sort_values("z_score", ascending=False)
    if anom.empty:
        st.info("No anomalies detected in the current filter range.")
    else:
        ad = anom[["title","published_at","view_count","views_per_day","z_score","anomaly_type"]].copy()
        ad["Title"]      = ad["title"].str[:60] + "…"
        ad["Published"]  = ad["published_at"].dt.strftime("%Y-%m-%d")
        ad["Views"]      = (ad["view_count"] / 1e6).round(1).astype(str) + "M"
        ad["Views/Day"]  = (ad["views_per_day"] / 1e6).round(2).astype(str) + "M"
        ad["Z-Score"]    = ad["z_score"]
        ad["Type"]       = ad.apply(anomaly_label, axis=1)
        st.dataframe(ad[["Type","Title","Published","Views","Views/Day","Z-Score"]],
                     use_container_width=True, hide_index=True)


# ── TAB 2: Performance Charts ─────────────────────────────────────────────────
with tab2:
    c1, c2 = st.columns(2)

    with c1:
        top_vpd = df_f.nlargest(top_n, "views_per_day").sort_values("views_per_day")
        top_vpd["label"] = top_vpd["title"].str[:40] + "…"
        fig = px.bar(top_vpd, x="views_per_day", y="label", orientation="h",
                     color="virality_score",
                     color_continuous_scale=[[0,"#222"],[0.5,"#553"],[1,AC]],
                     hover_data={"title":True,"views_per_day":":.2s",
                                 "virality_score":":.1f","label":False},
                     labels={"views_per_day":"Views/Day","label":"","virality_score":"Virality"})
        fig.update_layout(title=f"Top {top_n} — Views Per Day (coloured by virality)",
                          coloraxis_showscale=False, height=420, **CB)
        fig.update_xaxes(tickformat=".2s", gridcolor="#222")
        fig.update_yaxes(gridcolor="#222")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        top_score = df_f.nlargest(top_n, "composite_score").sort_values("composite_score")
        top_score["label"] = top_score["title"].str[:40] + "…"
        fig = px.bar(top_score, x="composite_score", y="label", orientation="h",
                     color="grade", color_discrete_map=GRADE_COLORS,
                     hover_data={"title":True,"composite_score":":.1f",
                                 "engagement_rate":":.3f","label":False},
                     labels={"composite_score":"Composite Score (0–100)","label":"","grade":"Grade"})
        fig.update_layout(title=f"Top {top_n} — Composite Score",
                          height=420, **CB)
        fig.update_xaxes(range=[0,100], gridcolor="#222")
        fig.update_yaxes(gridcolor="#222")
        st.plotly_chart(fig, use_container_width=True)

    df_sc = df_f.copy()
    df_sc["views_M"] = df_sc["view_count"] / 1e6
    fig = px.scatter(df_sc, x="views_per_day", y="engagement_rate",
                     color="format", size="views_M", hover_name="title",
                     hover_data={"published_at":True,"views_per_day":":.2s",
                                 "engagement_rate":":.3f","views_M":False,"format":False,
                                 "virality_score":":.1f","composite_score":":.0f"},
                     color_discrete_map={"Short-form (<2 min)":AC,"Long-form (≥2 min)":"#2979FF"},
                     labels={"views_per_day":"Views Per Day","engagement_rate":"Engagement Rate"})
    fig.update_layout(title="Views/Day vs Engagement — each bubble = one video (size = total views)",
                      height=440, **CB)
    fig.update_xaxes(tickformat=".2s", gridcolor="#222")
    fig.update_yaxes(tickformat=".1%", gridcolor="#222")
    st.plotly_chart(fig, use_container_width=True)

    top_eng = df_f.nlargest(top_n, "engagement_rate").sort_values("engagement_rate")
    top_eng["label"] = top_eng["title"].str[:40] + "…"
    top_eng["eng_pct"] = top_eng["engagement_rate"] * 100
    fig = px.bar(top_eng, x="eng_pct", y="label", orientation="h",
                 color="eng_pct", color_continuous_scale=["#222","#43A047"],
                 hover_data={"title":True,"eng_pct":":.2f","published_at":True,"label":False},
                 labels={"eng_pct":"Engagement %","label":""})
    fig.update_layout(title=f"Top {top_n} — Engagement Rate",
                      coloraxis_showscale=False, height=380, **CB)
    fig.update_xaxes(ticksuffix="%", gridcolor="#222")
    fig.update_yaxes(gridcolor="#222")
    st.plotly_chart(fig, use_container_width=True)


# ── TAB 3: Career Arc ─────────────────────────────────────────────────────────
def detect_inflection_points(df: pd.DataFrame, window: int = 20, top_n: int = 3) -> pd.DataFrame:
    # exclude videos < 60 days old to avoid recency bias (new videos have inflated views/day)
    d = df[df["video_age_days"] >= 60].sort_values("published_at").copy()
    if len(d) < window:
        return pd.DataFrame()
    d["roll_vpd"] = d["views_per_day"].rolling(window, center=True, min_periods=5).mean()
    d["slope"] = d["roll_vpd"].diff()
    d["slope_smooth"] = d["slope"].rolling(10, center=True, min_periods=3).mean()
    d["slope_delta"] = d["slope_smooth"].diff().abs()
    valid = d.dropna(subset=["slope_delta", "roll_vpd"])
    return valid.nlargest(top_n, "slope_delta").sort_values("published_at")


with tab3:
    traj_title = "🎵 Catalog View History — Total Views per MV" if is_music else "📈 Growth Trajectory — Views/Day Over Time"
    traj_caption = "Music catalog sorted by release date. Y-axis = total lifetime views (not views/day)." if is_music else ""
    st.markdown(f'<div class="sec-head">{traj_title}</div>', unsafe_allow_html=True)
    if traj_caption:
        st.caption(traj_caption)
    df_ts = df_f.sort_values("published_at").copy()
    df_ts["roll_vpd"] = df_ts["views_per_day"].rolling(20, center=True, min_periods=5).mean()
    inflection_pts = detect_inflection_points(df_f) if not is_music else pd.DataFrame()

    fig_ts = go.Figure()
    if is_music:
        # music: show total view_count per MV, full history, no rolling avg
        fig_ts.add_trace(go.Scatter(
            x=df_ts["published_at"], y=df_ts["view_count"] / 1e6,
            mode="markers", name="Each MV",
            marker=dict(size=5, color=AC, opacity=0.7),
            hovertemplate="%{customdata}<br>%{y:.1f}M total views<extra></extra>",
            customdata=df_ts["title"],
        ))
        fig_ts.update_layout(
            title="Catalog Total Views per MV (full history)",
            yaxis_title="Total Views (M)", height=440,
            xaxis_gridcolor="#222", yaxis_gridcolor="#222",
            **CB,
        )
    else:
        fig_ts.add_trace(go.Scatter(
            x=df_ts["published_at"], y=df_ts["views_per_day"] / 1e6,
            mode="markers", name="Each video",
            marker=dict(size=3, color="#3D3D50", opacity=0.5),
            hovertemplate="%{customdata}<br>%{y:.2f}M/day<extra></extra>",
            customdata=df_ts["title"],
        ))
        fig_ts.add_trace(go.Scatter(
            x=df_ts["published_at"], y=df_ts["roll_vpd"] / 1e6,
            mode="lines", name="20-video rolling avg",
            line=dict(color=AC, width=2.5),
        ))
        for i, (_, pt) in enumerate(inflection_pts.iterrows()):
            direction = "▲" if pt["slope_smooth"] > 0 else "▼"
            fig_ts.add_annotation(
                x=pt["published_at"], y=pt["roll_vpd"] / 1e6,
                text=f"{direction} {pt['published_at'].strftime('%b %Y')}",
                showarrow=True, arrowhead=2, arrowcolor="#FFD700", arrowwidth=1.5,
                font=dict(size=11, color="#FFD700", family="monospace"),
                bgcolor="#1A1A2E", bordercolor="#FFD700", borderwidth=1,
                ax=0, ay=-50 - i * 30,
            )
        fig_ts.update_layout(
            title="Views/Day — Growth Trajectory with Inflection Points",
            yaxis_title="Views/Day (M)", height=440,
            xaxis=dict(range=["2024-01-01", df_ts["published_at"].max()], gridcolor="#222"),
            yaxis_gridcolor="#222",
            legend=dict(orientation="h", y=1.05),
            **CB,
        )
    st.plotly_chart(fig_ts, use_container_width=True)

    if not inflection_pts.empty:
        cols_inf = st.columns(len(inflection_pts))
        for i, (_, pt) in enumerate(inflection_pts.iterrows()):
            with cols_inf[i]:
                direction = "▲" if pt["slope_smooth"] > 0 else "▼"
                st.metric(
                    label=f"{direction} Inflection {i+1} — {pt['published_at'].strftime('%b %Y')}",
                    value=f"{pt['roll_vpd']/1e6:.2f}M/day",
                    delta=f"{pt['slope_smooth']/1e3:+.0f}K/day trend shift",
                )

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        roll = df_f["view_count"].rolling(30, center=True, min_periods=5).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_f["published_at"], y=df_f["view_count"]/1e6,
                                 mode="markers", name="Each video",
                                 marker=dict(size=4, color="#3D3D50", opacity=0.6),
                                 hovertemplate="%{customdata}<br>%{y:.1f}M<extra></extra>",
                                 customdata=df_f["title"]))
        fig.add_trace(go.Scatter(x=df_f["published_at"], y=roll/1e6,
                                 mode="lines", name="30-video rolling avg",
                                 line=dict(color=AC, width=2.5)))
        fig.update_layout(title="Views Per Video — Career Arc", yaxis_title="Views (M)",
                          height=360, xaxis_gridcolor="#222", yaxis_gridcolor="#222", **CB)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        roll_eng = df_f["engagement_rate"].rolling(30, center=True, min_periods=5).mean() * 100
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_f["published_at"], y=df_f["engagement_rate"]*100,
                                 mode="markers", name="Each video",
                                 marker=dict(size=4, color="#3D3D50", opacity=0.6),
                                 hovertemplate="%{customdata}<br>%{y:.2f}%<extra></extra>",
                                 customdata=df_f["title"]))
        fig.add_trace(go.Scatter(x=df_f["published_at"], y=roll_eng,
                                 mode="lines", name="30-video rolling avg",
                                 line=dict(color="#43A047", width=2.5)))
        fig.update_layout(title="Engagement Rate — Career Arc",
                          yaxis_title="Engagement Rate (%)", yaxis_ticksuffix="%",
                          height=360, xaxis_gridcolor="#222", yaxis_gridcolor="#222", **CB)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        dur_q = df_f.groupby("quarter")["duration_sec"].median() / 60
        fig = px.area(x=dur_q.index, y=dur_q.values, markers=True,
                      labels={"x":"","y":"Median Duration (min)"})
        fig.update_traces(line_color="#FB8C00", marker_color="#FB8C00",
                          fillcolor="rgba(251,140,0,0.15)")
        fig.update_layout(title="Video Length — Quarterly Median",
                          height=300, xaxis_gridcolor="#222", yaxis_gridcolor="#222", **CB)
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        freq_q = df_f.groupby("quarter").size().reset_index(name="count")
        fig = px.bar(freq_q, x="quarter", y="count",
                     labels={"quarter":"","count":"Videos Uploaded"})
        fig.update_traces(marker_color=AC, opacity=0.85)
        fig.update_layout(title="Upload Frequency by Quarter",
                          height=300, xaxis_gridcolor="#222", yaxis_gridcolor="#222", **CB)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    lifecycle_title = "⏳ Catalog Longevity — Views by MV Age" if is_music else "⏳ Content Lifecycle — View Decay by Age"
    lifecycle_caption = ("How total views distribute across the catalog by MV age. Older MVs still pulling views = strong catalog longevity."
                         if is_music else
                         "How views/day changes as content ages. Flat curve = evergreen. Steep drop = algorithm-dependent.")
    st.markdown(f'<div class="sec-head">{lifecycle_title}</div>', unsafe_allow_html=True)
    st.caption(lifecycle_caption)

    AGE_BUCKETS = [
        (0,   30,  "0–30 days"),
        (31,  90,  "31–90 days"),
        (91,  365, "91–365 days"),
        (366, 730, "1–2 years"),
        (731, 9999,"2+ years"),
    ]
    bucket_rows = []
    for lo, hi, label in AGE_BUCKETS:
        mask = (df_f["video_age_days"] >= lo) & (df_f["video_age_days"] <= hi)
        if mask.sum() >= 3:
            bucket_rows.append({
                "Age Bucket": label,
                "avg_vpd": df_f[mask]["views_per_day"].mean(),
                "median_vpd": df_f[mask]["views_per_day"].median(),
                "n": int(mask.sum()),
            })
    if bucket_rows:
        bucket_df = pd.DataFrame(bucket_rows)
        fresh_vpd  = bucket_df.iloc[0]["avg_vpd"]
        oldest_vpd = bucket_df.iloc[-1]["avg_vpd"]
        decay_ratio = fresh_vpd / oldest_vpd if oldest_vpd > 0 else 0
        if decay_ratio > 5:
            decay_label, decay_color = "Front-Loaded", "#FF5252"
        elif decay_ratio > 2:
            decay_label, decay_color = "Moderate Decay", "#FB8C00"
        else:
            decay_label, decay_color = "Evergreen", "#43A047"

        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            st.metric("Fresh Content (0–30d) Avg Views/Day",
                      f"{fresh_vpd/1e6:.2f}M" if fresh_vpd >= 1e6 else f"{fresh_vpd/1e3:.0f}K")
        with lc2:
            st.metric("Aged Content (2y+) Avg Views/Day",
                      f"{oldest_vpd/1e6:.2f}M" if oldest_vpd >= 1e6 else f"{oldest_vpd/1e3:.0f}K")
        with lc3:
            st.metric("Decay Ratio", f"{decay_ratio:.1f}x",
                      delta=decay_label, delta_color="off")

        fig_decay = go.Figure()
        fig_decay.add_trace(go.Bar(
            x=bucket_df["Age Bucket"], y=bucket_df["avg_vpd"] / 1e6,
            name="Avg Views/Day",
            marker_color=[AC, "#CC3300", "#994400", "#665500", "#444422"][: len(bucket_df)],
            text=[f"{v/1e6:.2f}M<br>n={n}" if v >= 1e6 else f"{v/1e3:.0f}K<br>n={n}"
                  for v, n in zip(bucket_df["avg_vpd"], bucket_df["n"])],
            textposition="outside",
            hovertemplate="%{x}<br>Avg: %{y:.2f}M/day<extra></extra>",
        ))
        fig_decay.add_trace(go.Scatter(
            x=bucket_df["Age Bucket"], y=bucket_df["median_vpd"] / 1e6,
            mode="lines+markers", name="Median Views/Day",
            line=dict(color="#FFD700", width=2, dash="dot"),
            marker=dict(size=8),
        ))
        fig_decay.update_layout(
            title=f"View Decay Curve — {decay_label} ({decay_ratio:.1f}x fresh-to-aged ratio)",
            yaxis_title="Views/Day (M)", height=360,
            xaxis_gridcolor="#222", yaxis_gridcolor="#222",
            legend=dict(orientation="h", y=1.05),
            **CB,
        )
        st.plotly_chart(fig_decay, use_container_width=True)

    st.divider()
    st.markdown(f'<div class="sec-head">📉 Performance Dips — When Things Dropped</div>',
                unsafe_allow_html=True)
    st.caption("Quarters where avg views dropped >35% from rolling 4-quarter peak.")
    dips = detect_quarterly_dips(df_f)
    if dips.empty:
        st.info("No significant performance dips detected in this period.")
    else:
        for _, row in dips.iterrows():
            qstr = row["quarter_str"]
            sq   = urllib.parse.quote(f"{channel_info['name']} {qstr[:4]}")
            news_url = f"https://news.google.com/search?q={sq}&hl=en-US&gl=US&ceid=US:en"
            ci, cb2 = st.columns([5, 1])
            with ci:
                st.markdown(
                    f'<div class="dip-row"><span style="color:{AC};font-weight:700">{qstr}</span>'
                    f' — avg views dropped <b>{row["drop_pct"]*100:.0f}%</b> from peak</div>',
                    unsafe_allow_html=True)
            with cb2:
                st.markdown(
                    f'<a href="{news_url}" target="_blank">'
                    f'<button style="background:#1E1E2E;color:#E2E8F0;border:1px solid #333;'
                    f'padding:5px 14px;border-radius:6px;cursor:pointer;font-size:0.8rem;">'
                    f'🔍 News</button></a>', unsafe_allow_html=True)
            with st.expander(f"📰 Headlines — {qstr}"):
                q_end = pd.Timestamp(qstr) + pd.offsets.QuarterEnd()
                news = fetch_news(channel_info["name"], qstr, q_end.strftime("%Y-%m-%d"))
                if news:
                    for title, link, pub in news:
                        st.markdown(f"- [{title}]({link})  \n  *{pub[:16]}*")
                else:
                    st.caption("Click News above to search manually.")


# ── TAB 4: Content DNA ────────────────────────────────────────────────────────
with tab4:
    c1, c2 = st.columns(2)

    with c1:
        cat = df_f.groupby("category").agg(
            count=("video_id","count"),
            avg_views=("view_count","mean"),
            avg_eng=("engagement_rate","mean"),
        ).reset_index().sort_values("avg_views")
        cat["avg_views_M"]  = cat["avg_views"] / 1e6
        cat["avg_eng_pct"]  = cat["avg_eng"] * 100
        fig = px.bar(cat, x="avg_views_M", y="category", orientation="h",
                     color="avg_views_M", color_continuous_scale=["#222","#43A047"],
                     hover_data={"count":True,"avg_eng_pct":":.2f",
                                 "avg_views_M":":.1f","category":False},
                     labels={"avg_views_M":"Avg Views (M)","category":""})
        fig.update_layout(title="Avg Views by Content Category",
                          coloraxis_showscale=False, height=380,
                          xaxis_gridcolor="#222", yaxis_gridcolor="#222", **CB)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        kw_rows = []
        for kw in TITLE_KEYWORDS:
            mask = df_f["title"].str.contains(kw, case=False, regex=False, na=False)
            if mask.sum() >= 2:
                kw_rows.append({"keyword": f'"{kw}" (n={mask.sum()})',
                                "avg_views_M": df_f[mask]["view_count"].mean()/1e6})
        if kw_rows:
            kw_df = pd.DataFrame(kw_rows).sort_values("avg_views_M")
            fig = px.bar(kw_df, x="avg_views_M", y="keyword", orientation="h",
                         color="avg_views_M", color_continuous_scale=["#222",AC],
                         labels={"avg_views_M":"Avg Views (M)","keyword":""})
            fig.update_layout(title="Title Keywords vs Avg Views",
                              coloraxis_showscale=False, height=380,
                              xaxis_gridcolor="#222", yaxis_gridcolor="#222", **CB)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough keyword matches (need ≥2 per keyword).")

    st.markdown(f'<div class="sec-head">Short-form vs Long-form Breakdown</div>',
                unsafe_allow_html=True)
    grp = df_f.groupby("format").agg(
        Videos=("video_id","count"),
        avg_views=("view_count","mean"),
        avg_vpd=("views_per_day","mean"),
        avg_eng=("engagement_rate","mean"),
        avg_virality=("virality_score","mean"),
        avg_score=("composite_score","mean"),
    ).reset_index()
    grp["Avg Views (M)"]      = (grp["avg_views"]/1e6).round(1)
    grp["Avg Views/Day (M)"]  = (grp["avg_vpd"]/1e6).round(2)
    grp["Avg Engagement (%)"] = (grp["avg_eng"]*100).round(2)
    grp["Avg Virality"]       = grp["avg_virality"].round(2)
    grp["Avg Score"]          = grp["avg_score"].round(1)
    st.dataframe(
        grp[["format","Videos","Avg Views (M)","Avg Views/Day (M)",
             "Avg Engagement (%)","Avg Virality","Avg Score"]].rename(columns={"format":"Format"}),
        use_container_width=True, hide_index=True,
    )

    if df_f["format"].nunique() > 1:
        fig = px.histogram(df_f, x="composite_score", color="format",
                           nbins=20, barmode="overlay", opacity=0.75,
                           color_discrete_map={"Short-form (<2 min)":AC,"Long-form (≥2 min)":"#2979FF"},
                           labels={"composite_score":"Composite Score (0–100)","format":""})
        fig.update_layout(title="Score Distribution by Format",
                          height=300, xaxis_gridcolor="#222", yaxis_gridcolor="#222", **CB)
        st.plotly_chart(fig, use_container_width=True)


# ── TAB 5: Insights & Recommendations ─────────────────────────────────────────
with tab5:
    st.markdown(f'<div class="sec-head">🎯 So What — Executive Summary</div>',
                unsafe_allow_html=True)
    st.caption("Observation → Implication → Recommendation. Three things a PM can act on today.")
    if len(df_f) >= 10:
        st.markdown(generate_so_what(df_f, channel_info.get("name", creator), AC),
                    unsafe_allow_html=True)
    st.divider()
    col_ins, col_rec = st.columns([1, 1])

    with col_ins:
        st.markdown(f'<div class="sec-head">Executive Insights</div>', unsafe_allow_html=True)
        if len(df_f) >= 5:
            st.markdown(generate_creator_insights(df_f, channel_info.get("name", creator)),
                        unsafe_allow_html=True)
        else:
            st.info("Not enough data for insights. Adjust filters.")

    with col_rec:
        st.markdown(f'<div class="sec-head">Content Strategy Recommendations</div>',
                    unsafe_allow_html=True)
        if len(df_f) >= 5:
            recs = generate_recommendations(df_f, channel_info.get("name", creator))
            for rec in recs:
                st.markdown(rec_card(rec), unsafe_allow_html=True)
        else:
            st.info("Not enough data for recommendations.")


# ── TAB 6: Compare ────────────────────────────────────────────────────────────
with tab6:
    cc1, cc2, cc3 = st.columns([2, 2, 3])
    with cc1:
        creator_a = st.selectbox("Creator A", list(CREATORS.keys()), index=0, key="ca")
    with cc2:
        creator_b = st.selectbox("Creator B", list(CREATORS.keys()), index=2, key="cb")
    with cc3:
        cmp_date_str = st.text_input("Compare from (YYYY-MM-DD)", value="2020-01-01",
                                      help="Filters both creators to the same window.")
        try:
            cmp_start = pd.Timestamp(cmp_date_str)
        except Exception:
            cmp_start = pd.Timestamp("2020-01-01")

    @st.cache_data(show_spinner=False)
    def load_compare(slug_c: str):
        d = pd.read_csv(f"data/processed/{slug_c}_metrics.csv")
        d["published_at"] = pd.to_datetime(d["published_at"], utc=True).dt.tz_localize(None)
        d["duration_sec"] = d["duration"].apply(parse_sec)
        d["is_short"] = d["duration_sec"] < 120
        d["format"] = d["is_short"].map({True:"Short-form (<2 min)",False:"Long-form (≥2 min)"})
        d["category"] = d["title"].apply(categorize)
        d["quarter"] = d["published_at"].dt.to_period("Q").dt.to_timestamp()
        d["virality_score"] = calc_virality_score(d)
        d["composite_score"] = calc_composite_score(d)
        return d.sort_values("published_at").reset_index(drop=True)

    da = load_compare(CREATORS[creator_a]["slug"])
    db = load_compare(CREATORS[creator_b]["slug"])
    da = da[da["published_at"] >= cmp_start].reset_index(drop=True)
    db = db[db["published_at"] >= cmp_start].reset_index(drop=True)

    if len(da) < 3 or len(db) < 3:
        st.warning("Not enough data after date filter. Try an earlier date.")
    else:
        from src.metrics import calc_momentum as _mom, calc_hit_rate as _hr, calc_posting_cadence as _cad

        da["creator"] = creator_a
        db["creator"] = creator_b
        combined = pd.concat([da, db], ignore_index=True)
        cmp_music = CREATORS[creator_a]["slug"] in MUSIC_ARTISTS and CREATORS[creator_b]["slug"] in MUSIC_ARTISTS
        CA2, CB3 = ("#1DB954" if cmp_music else "#FF0000"), "#2979FF"
        CMAP = {creator_a: CA2, creator_b: CB3}
        cmp_CB = chart_cfg(cmp_music)

        # Head-to-head table
        st.markdown(f'<div class="sec-head">Head-to-Head KPIs</div>', unsafe_allow_html=True)
        def viral_hit_rate(d):
            threshold = d["views_per_day"].mean() * 2
            return (d["views_per_day"] >= threshold).mean()

        hth = pd.DataFrame({
            "Metric": ["Videos","Avg Views","Avg Views/Day","Avg Engagement",
                       "Momentum (90d)","Viral Hit Rate (>2x avg)","Cadence (vids/wk)","Avg Composite Score"],
            creator_a: [f"{len(da):,}", f"{da['view_count'].mean()/1e6:.1f}M",
                        f"{da['views_per_day'].mean()/1e6:.2f}M",
                        f"{da['engagement_rate'].mean()*100:.2f}%",
                        f"{_mom(da):.2f}x", f"{viral_hit_rate(da)*100:.0f}%",
                        f"{_cad(da):.1f}", f"{da['composite_score'].mean():.1f}"],
            creator_b: [f"{len(db):,}", f"{db['view_count'].mean()/1e6:.1f}M",
                        f"{db['views_per_day'].mean()/1e6:.2f}M",
                        f"{db['engagement_rate'].mean()*100:.2f}%",
                        f"{_mom(db):.2f}x", f"{viral_hit_rate(db)*100:.0f}%",
                        f"{_cad(db):.1f}", f"{db['composite_score'].mean():.1f}"],
        })
        st.dataframe(hth, use_container_width=True, hide_index=True)

        st.divider()
        c1, c2 = st.columns(2)

        with c1:
            fig = go.Figure()
            for label, d in [(creator_a, da), (creator_b, db)]:
                roll = d["view_count"].rolling(20, center=True, min_periods=5).mean()
                fig.add_trace(go.Scatter(x=d["published_at"], y=roll/1e6, mode="lines",
                                         name=label, line=dict(color=CMAP[label], width=2.5),
                                         hovertemplate=f"{label}<br>%{{x|%Y-%m}}<br>%{{y:.1f}}M<extra></extra>"))
            fig.update_layout(title="Views Per Video — Rolling Avg", yaxis_title="Views (M)",
                              height=360, xaxis_gridcolor="#222", yaxis_gridcolor="#222",
                              legend=dict(x=0.01,y=0.99), **cmp_CB)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig = go.Figure()
            for label, d in [(creator_a, da), (creator_b, db)]:
                roll = d["engagement_rate"].rolling(20, center=True, min_periods=5).mean()*100
                fig.add_trace(go.Scatter(x=d["published_at"], y=roll, mode="lines",
                                         name=label, line=dict(color=CMAP[label], width=2.5),
                                         hovertemplate=f"{label}<br>%{{x|%Y-%m}}<br>%{{y:.2f}}%<extra></extra>"))
            fig.update_layout(title="Engagement Rate — Rolling Avg",
                              yaxis_title="Engagement Rate (%)", yaxis_ticksuffix="%",
                              height=360, xaxis_gridcolor="#222", yaxis_gridcolor="#222",
                              legend=dict(x=0.01,y=0.99), **cmp_CB)
            st.plotly_chart(fig, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            fig = px.box(combined[combined["view_count"]>=500_000],
                         x="creator", y="views_per_day", color="creator",
                         color_discrete_map=CMAP, points="outliers", hover_name="title",
                         labels={"views_per_day":"Views Per Day","creator":""})
            fig.update_layout(title="Views/Day Distribution", height=360,
                              showlegend=False, yaxis_gridcolor="#222", **cmp_CB)
            fig.update_yaxes(tickformat=".2s")
            st.plotly_chart(fig, use_container_width=True)

        with c4:
            freq_rows = []
            for label, d in [(creator_a, da), (creator_b, db)]:
                freq = d.groupby("quarter").size().reset_index(name="count")
                freq["creator"] = label
                freq_rows.append(freq)
            freq_df = pd.concat(freq_rows)
            fig = px.line(freq_df, x="quarter", y="count", color="creator",
                          color_discrete_map=CMAP, markers=True,
                          labels={"quarter":"","count":"Videos Uploaded","creator":""})
            fig.update_layout(title="Upload Frequency by Quarter", height=360,
                              xaxis_gridcolor="#222", yaxis_gridcolor="#222", **cmp_CB)
            st.plotly_chart(fig, use_container_width=True)

        fmt_rows = []
        for label, d in [(creator_a, da), (creator_b, db)]:
            for fmt, mask in [("Short (<2min)", d["is_short"]), ("Long (≥2min)", ~d["is_short"])]:
                sub = d[mask & (d["view_count"]>=500_000)]
                if len(sub) >= 3:
                    fmt_rows.append({"creator":label,"format":fmt,
                                     "avg_views_M":sub["view_count"].mean()/1e6})
        if fmt_rows:
            fdf = pd.DataFrame(fmt_rows)
            fig = px.bar(fdf, x="format", y="avg_views_M", color="creator",
                         barmode="group", color_discrete_map=CMAP, text_auto=".1f",
                         labels={"avg_views_M":"Avg Views (M)","format":"","creator":""})
            fig.update_layout(title="Short vs Long Form — Avg Views", height=320,
                              yaxis_gridcolor="#222", legend=dict(x=0.01,y=0.99), **cmp_CB)
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown(f'<div class="sec-head">Analysis</div>', unsafe_allow_html=True)
        st.markdown(generate_comparison_insights(da, db, creator_a, creator_b),
                    unsafe_allow_html=True)


# ── TAB 7: Export ─────────────────────────────────────────────────────────────
with tab7:
    st.markdown(f'<div class="sec-head">Download Data & Reports</div>', unsafe_allow_html=True)

    kpis_ex   = kpi_summary(df_f)
    recs_ex   = generate_recommendations(df_f, channel_info.get("name", creator))
    dips_ex   = detect_quarterly_dips(df_f)

    ec1, ec2, ec3 = st.columns(3)

    with ec1:
        st.markdown("**📄 Full Dataset CSV**")
        st.caption(f"{len(df_f):,} videos · all metrics, scores, anomaly flags")
        export_df = df_f[[
            "video_id","title","published_at","view_count","like_count","comment_count",
            "duration","video_age_days","views_per_day","like_rate","comment_rate",
            "engagement_rate","duration_sec","format","category",
            "virality_score","composite_score","grade","z_score","anomaly_type",
        ]].copy()
        export_df["published_at"] = export_df["published_at"].dt.strftime("%Y-%m-%d")
        st.download_button("⬇ Download CSV", data=export_df.to_csv(index=False),
                           file_name=f"{slug}_analytics_{date.today()}.csv",
                           mime="text/csv", use_container_width=True)

    with ec2:
        st.markdown("**📋 Executive Summary Report**")
        st.caption("KPIs · top videos · anomalies · recommendations")
        report = generate_text_report(df_f, creator, channel_info, kpis_ex, recs_ex, dips_ex)
        st.download_button("⬇ Download Report (.txt)", data=report,
                           file_name=f"{slug}_report_{date.today()}.txt",
                           mime="text/plain", use_container_width=True)

    with ec3:
        st.markdown(f"**📊 Top {top_n} Leaderboard CSV**")
        st.caption("Ranked by composite score")
        lb_ex = df_f.nlargest(top_n, "composite_score")[
            ["title","published_at","view_count","views_per_day",
             "engagement_rate","virality_score","composite_score","grade"]
        ].copy()
        lb_ex["published_at"] = lb_ex["published_at"].dt.strftime("%Y-%m-%d")
        st.download_button("⬇ Download Leaderboard", data=lb_ex.to_csv(index=False),
                           file_name=f"{slug}_leaderboard_{date.today()}.csv",
                           mime="text/csv", use_container_width=True)

    st.divider()
    st.markdown("**Preview — Executive Summary**")
    st.code(report, language=None)
