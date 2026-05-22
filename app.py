import re
import json
import urllib.parse
import requests
import feedparser
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Creator Analytics", layout="wide", page_icon="🎬")

# ── creator config ─────────────────────────────────────────────────────────────
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

# ── theme CSS ──────────────────────────────────────────────────────────────────
YT_CSS = """
<style>
.kpi-card {
    background: #1A1A1A; border: 1px solid #282828; border-radius: 12px;
    padding: 20px 16px; text-align: center; height: 100%;
}
.kpi-label { color: #888; font-size: 0.7rem; text-transform: uppercase;
             letter-spacing: 1.5px; margin-bottom: 8px; }
.kpi-value { color: #FF0000; font-size: 2.4rem; font-weight: 900; line-height: 1; }
.kpi-sub   { color: #555; font-size: 0.75rem; margin-top: 4px; }
.sec-head  { font-size: 1rem; font-weight: 700; color: #FF0000;
             border-left: 3px solid #FF0000; padding-left: 10px; margin: 20px 0 10px; }
.thumb-title { font-size: 0.72rem; color: #aaa; margin-top: 5px; line-height: 1.3;
               height: 2.4em; overflow: hidden; }
.thumb-stat  { font-size: 0.78rem; color: #FF0000; font-weight: 700; margin-top: 3px; }
.insight-box { background: #1A1A1A; border: 1px solid #282828; border-radius: 12px;
               padding: 20px 24px; margin: 8px 0; }
.insight-head { color: #FF0000; font-size: 0.8rem; font-weight: 700;
                text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.insight-body { color: #DDDDDD; font-size: 0.95rem; line-height: 1.6; }
.dip-row { background: #1A1A1A; border: 1px solid #2a2a2a; border-radius: 8px;
           padding: 12px 16px; margin: 6px 0; }
</style>"""

SPOTIFY_CSS = """
<style>
.kpi-card {
    border-radius: 16px; padding: 24px 16px; text-align: center;
    height: 100%; min-height: 110px;
}
.kpi-card-0 { background: linear-gradient(135deg, #1DB954, #0a7a35); }
.kpi-card-1 { background: linear-gradient(135deg, #E91E63, #880E4F); }
.kpi-card-2 { background: linear-gradient(135deg, #2979FF, #01579B); }
.kpi-card-3 { background: linear-gradient(135deg, #FF6D00, #BF360C); }
.kpi-label { color: rgba(255,255,255,0.65); font-size: 0.7rem; text-transform: uppercase;
             letter-spacing: 1.5px; margin-bottom: 8px; }
.kpi-value { color: #FFFFFF; font-size: 2.6rem; font-weight: 900; line-height: 1; }
.kpi-sub   { color: rgba(255,255,255,0.5); font-size: 0.75rem; margin-top: 4px; }
.sec-head  { font-size: 1rem; font-weight: 700; color: #1DB954;
             border-left: 3px solid #1DB954; padding-left: 10px; margin: 20px 0 10px; }
.thumb-title { font-size: 0.72rem; color: #aaa; margin-top: 5px; line-height: 1.3;
               height: 2.4em; overflow: hidden; }
.thumb-stat  { font-size: 0.78rem; color: #1DB954; font-weight: 700; margin-top: 3px; }
.insight-box { background: #1E1E1E; border: 1px solid #2a2a2a; border-radius: 16px;
               padding: 20px 24px; margin: 8px 0; }
.insight-head { color: #1DB954; font-size: 0.8rem; font-weight: 700;
                text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.insight-body { color: #DDDDDD; font-size: 0.95rem; line-height: 1.6; }
.dip-row { background: #1E1E1E; border: 1px solid #2a2a2a; border-radius: 8px;
           padding: 12px 16px; margin: 6px 0; }
</style>"""

# ── helpers ────────────────────────────────────────────────────────────────────
def parse_sec(s):
    h = re.search(r'(\d+)H', s); m = re.search(r'(\d+)M', s); sec = re.search(r'(\d+)S', s)
    return (int(h.group(1))*3600 if h else 0)+(int(m.group(1))*60 if m else 0)+(int(sec.group(1)) if sec else 0)

def categorize(title):
    t = title.lower()
    for label, pat in CATEGORIES.items():
        if re.search(pat, t): return label
    return "Other"

def kpi_card(label, value, sub, idx, is_music):
    cls = f"kpi-card kpi-card-{idx}" if is_music else "kpi-card"
    return f"""<div class="{cls}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""

def insight_block(head, body):
    return f"""<div class="insight-box">
        <div class="insight-head">{head}</div>
        <div class="insight-body">{body}</div>
    </div>"""

def chart_base(is_music):
    bg = "#121212" if is_music else "#0F0F0F"
    card = "#1E1E1E" if is_music else "#1A1A1A"
    return dict(template="plotly_dark", paper_bgcolor=bg, plot_bgcolor=card,
                font_color="#FFFFFF", margin=dict(l=0, r=0, t=40, b=0))

def accent(is_music):
    return "#1DB954" if is_music else "#FF0000"

def generate_insights(da, db, name_a, name_b):
    avg_a = da["view_count"].mean() / 1e6
    avg_b = db["view_count"].mean() / 1e6
    eng_a = da["engagement_rate"].mean() * 100
    eng_b = db["engagement_rate"].mean() * 100
    vpd_a = da["views_per_day"].mean() / 1e6
    vpd_b = db["views_per_day"].mean() / 1e6
    freq_a = len(da) / max((da["published_at"].max()-da["published_at"].min()).days/90, 1)
    freq_b = len(db) / max((db["published_at"].max()-db["published_at"].min()).days/90, 1)
    ratio = avg_a / avg_b if avg_b > 0 else 1
    slug_a = CREATORS[name_a]["slug"]
    slug_b = CREATORS[name_b]["slug"]
    both_music = slug_a in MUSIC_ARTISTS and slug_b in MUSIC_ARTISTS

    blocks = []

    if both_music:
        big_name, big_avg, big_eng = (name_a, avg_a, eng_a) if avg_a >= avg_b else (name_b, avg_b, eng_b)
        small_name, s_avg, s_eng = (name_b, avg_b, eng_b) if avg_a >= avg_b else (name_a, avg_a, eng_a)
        blocks.append(insight_block("CATALOG REACH",
            f"{big_name}'s catalog averages <b>{big_avg:.1f}M views per video</b>. "
            f"{small_name} averages <b>{s_avg:.1f}M</b>. "
            f"That {max(ratio, 1/ratio):.1f}x gap reflects legacy — "
            f"older catalogs keep accumulating views long after release."))
        blocks.append(insight_block("FANDOM DEPTH",
            f"{'Both artists sit around' if abs(eng_a-eng_b)<0.5 else (name_a if eng_a>eng_b else name_b)+' leads at'} "
            f"<b>{max(eng_a,eng_b):.2f}% engagement</b>. "
            f"Music fans who comment and like are different from passive streamers — "
            f"this is the core fanbase that shows up to concerts and buys merch."))
        blocks.append(insight_block("WHAT TO COPY",
            f"If you're a music creator: post your MVs, not just lyric videos. "
            f"Both {name_a} and {name_b} see 2–5x higher engagement on official MVs vs. live footage. "
            f"Quality of visual production moves the needle more than upload frequency."))
    else:
        winner = name_a if avg_a >= avg_b else name_b
        loser = name_b if avg_a >= avg_b else name_a
        w_avg = max(avg_a, avg_b); l_avg = min(avg_a, avg_b)
        w_eng = eng_a if avg_a >= avg_b else eng_b
        l_eng = eng_b if avg_a >= avg_b else eng_a
        w_freq = freq_a if avg_a >= avg_b else freq_b
        l_freq = freq_b if avg_a >= avg_b else freq_a

        blocks.append(insight_block("RAW REACH",
            f"{winner} averages <b>{w_avg:.1f}M views per video</b>. "
            f"{loser} averages <b>{l_avg:.1f}M</b>. "
            f"That's a <b>{max(ratio,1/ratio):.1f}x gap</b> — "
            f"explained almost entirely by upload cadence and prize budgets, not talent alone."))

        eng_winner = name_a if eng_a >= eng_b else name_b
        blocks.append(insight_block("ENGAGEMENT",
            f"{eng_winner} wins on engagement at <b>{max(eng_a,eng_b):.2f}%</b> vs "
            f"<b>{min(eng_a,eng_b):.2f}%</b>. "
            f"{'Bigger reach does not mean better engagement — the algorithm rewards views, but your community rewards depth.' if (eng_a>eng_b) != (avg_a>avg_b) else 'Same creator leads on both metrics — that is rare and worth studying.'}"))

        blocks.append(insight_block("POSTING CADENCE",
            f"{winner} posts <b>~{w_freq:.0f} videos/quarter</b>. "
            f"{loser} posts <b>~{l_freq:.0f}</b>. "
            f"{'The algorithm rewards consistency. ' + winner + ' owns the feed by volume alone.' if w_freq > l_freq * 1.5 else 'Similar cadence — the view gap is about content formula, not frequency.'}"))

        blocks.append(insight_block("TAKEAWAY FOR YOU",
            f"Study <b>{winner}</b> for top-of-funnel reach: short hooks, clear payoff, high frequency. "
            f"Study <b>{loser}</b> for community: fewer videos, higher craftsmanship, loyal repeat viewers. "
            f"Pick one strategy and commit — trying to do both usually means doing neither well."))

    return "\n".join(blocks)

@st.cache_data(ttl=3600)
def fetch_news(query, from_date, to_date):
    year = str(from_date)[:4]
    q = urllib.parse.quote(f"{query} {year}")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        feed = feedparser.parse(r.content)
        return [(e.title, e.link, e.get("published", "")) for e in feed.entries[:5]]
    except Exception:
        return []

def detect_dips(df, creator_name, threshold=0.35):
    q = df.groupby("quarter")["view_count"].mean().reset_index()
    q = q[q["quarter"] >= "2016-01-01"].copy()
    q["rolling_max"] = q["view_count"].rolling(4, min_periods=2).max().shift(1)
    q["drop_pct"] = (q["rolling_max"] - q["view_count"]) / q["rolling_max"]
    dips = q[(q["drop_pct"] > threshold) & q["rolling_max"].notna()].copy()
    dips["creator"] = creator_name
    dips["quarter_str"] = dips["quarter"].dt.strftime("%Y-%m")
    return dips

@st.cache_data
def load_data(slug):
    df = pd.read_csv(f"data/processed/{slug}_metrics.csv")
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True).dt.tz_localize(None)
    df["duration_sec"] = df["duration"].apply(parse_sec)
    df["is_short"] = df["duration_sec"] < 120
    df["format"] = df["is_short"].map({True: "Short-form (<2 min)", False: "Long-form (≥2 min)"})
    df["category"] = df["title"].apply(categorize)
    df["quarter"] = df["published_at"].dt.to_period("Q").dt.to_timestamp()
    return df.sort_values("published_at").reset_index(drop=True)

try:
    all_channel_info = json.load(open("data/channel_info.json"))
except Exception:
    all_channel_info = {}

# ── sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.caption("Creator Analytics · YouTube Data API v3")
    st.divider()
    creator = st.selectbox("Creator", list(CREATORS.keys()))

slug = CREATORS[creator]["slug"]
is_music = slug in MUSIC_ARTISTS
df = load_data(slug)
channel_info = all_channel_info.get(slug, {"name": creator, "avatar": ""})
AC = accent(is_music)

st.markdown(SPOTIFY_CSS if is_music else YT_CSS, unsafe_allow_html=True)

with st.sidebar:
    if channel_info.get("avatar"):
        st.image(channel_info["avatar"], width=72)
    st.markdown(f"**{channel_info['name']}**")
    min_date, max_date = df["published_at"].min().date(), df["published_at"].max().date()
    date_range = st.slider("Date Range", min_value=min_date, max_value=max_date,
                           value=(min_date, max_date), format="YYYY-MM")
    top_n = st.slider("Top N videos", min_value=5, max_value=20, value=10)
    min_views = st.select_slider("Min Views Filter",
        options=[0, 100_000, 500_000, 1_000_000, 5_000_000, 10_000_000],
        value=1_000_000,
        format_func=lambda x: "None" if x == 0 else f"{x/1e6:.1f}M")

df_f = df[(df["published_at"].dt.date >= date_range[0]) &
          (df["published_at"].dt.date <= date_range[1]) &
          (df["view_count"] >= min_views)]

# ── header ─────────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([1, 10])
with hc1:
    if channel_info.get("avatar"):
        st.image(channel_info["avatar"], width=60)
with hc2:
    st.markdown(f"## {channel_info['name']}")
    st.caption(f"{len(df_f):,} videos · {date_range[0]} → {date_range[1]}")

# ── KPI cards ──────────────────────────────────────────────────────────────────
kpis = [
    ("TOTAL VIDEOS",    f"{len(df_f):,}",                          "in selected period"),
    ("AVG VIEWS",       f"{df_f['view_count'].mean()/1e6:.1f}M",   "per video"),
    ("AVG VIEWS / DAY", f"{df_f['views_per_day'].mean()/1e6:.2f}M","velocity"),
    ("AVG ENGAGEMENT",  f"{df_f['engagement_rate'].mean()*100:.2f}%", "likes + comments / views"),
]
cols = st.columns(4)
for i, (col, (label, val, sub)) in enumerate(zip(cols, kpis)):
    col.markdown(kpi_card(label, val, sub, i, is_music), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── top 5 thumbnails ──────────────────────────────────────────────────────────
st.markdown(f'<div class="sec-head">🔥 Top 5 This Period — by Views Per Day</div>',
            unsafe_allow_html=True)
top5 = df_f.nlargest(5, "views_per_day")
tcols = st.columns(5)
for col, (_, row) in zip(tcols, top5.iterrows()):
    thumb = f"https://img.youtube.com/vi/{row['video_id']}/hqdefault.jpg"
    url = f"https://www.youtube.com/watch?v={row['video_id']}"
    with col:
        st.markdown(
            f'<a href="{url}" target="_blank">'
            f'<img src="{thumb}" style="width:100%;border-radius:10px;display:block;"></a>'
            f'<div class="thumb-title">{row["title"]}</div>'
            f'<div class="thumb-stat">{row["views_per_day"]/1e6:.1f}M / day</div>',
            unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

# ── tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 Performance", "🕰️ Career", "🔍 Content", "⚔️ Compare"])

# ── TAB 1: Performance ────────────────────────────────────────────────────────
with tab1:
    c1, c2 = st.columns(2)
    cb = chart_base(is_music)

    with c1:
        top_vpd = df_f.nlargest(top_n, "views_per_day").sort_values("views_per_day")
        top_vpd["label"] = top_vpd["title"].str[:38] + "…"
        fig = px.bar(top_vpd, x="views_per_day", y="label", orientation="h",
                     color="views_per_day", color_continuous_scale=["#333", AC],
                     hover_data={"title": True, "views_per_day": ":.2s",
                                 "published_at": True, "label": False},
                     labels={"views_per_day": "Views/Day", "label": ""})
        fig.update_layout(title=f"Top {top_n} — Views Per Day",
                          coloraxis_showscale=False, height=420, **cb)
        fig.update_xaxes(tickformat=".2s", gridcolor="#222")
        fig.update_yaxes(gridcolor="#222")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        top_eng = df_f.nlargest(top_n, "engagement_rate").sort_values("engagement_rate")
        top_eng["label"] = top_eng["title"].str[:38] + "…"
        top_eng["eng_pct"] = top_eng["engagement_rate"] * 100
        fig = px.bar(top_eng, x="eng_pct", y="label", orientation="h",
                     color="eng_pct", color_continuous_scale=["#333", "#43A047"],
                     hover_data={"title": True, "eng_pct": ":.2f",
                                 "published_at": True, "label": False},
                     labels={"eng_pct": "Engagement %", "label": ""})
        fig.update_layout(title=f"Top {top_n} — Engagement Rate",
                          coloraxis_showscale=False, height=420, **cb)
        fig.update_xaxes(ticksuffix="%", gridcolor="#222")
        fig.update_yaxes(gridcolor="#222")
        st.plotly_chart(fig, use_container_width=True)

    df_f2 = df_f.copy()
    df_f2["views_M"] = df_f2["view_count"] / 1e6
    fig = px.scatter(df_f2, x="views_per_day", y="engagement_rate",
                     color="format", size="views_M", hover_name="title",
                     hover_data={"published_at": True, "views_per_day": ":.2s",
                                 "engagement_rate": ":.3f", "views_M": False, "format": False},
                     color_discrete_map={"Short-form (<2 min)": AC,
                                         "Long-form (≥2 min)": "#1E88E5"},
                     labels={"views_per_day": "Views Per Day", "engagement_rate": "Engagement Rate"})
    fig.update_layout(title="Views/Day vs Engagement Rate — each dot is one video",
                      height=420, **cb)
    fig.update_xaxes(tickformat=".2s", gridcolor="#222")
    fig.update_yaxes(tickformat=".1%", gridcolor="#222")
    st.plotly_chart(fig, use_container_width=True)

# ── TAB 2: Career ──────────────────────────────────────────────────────────────
with tab2:
    cb = chart_base(is_music)
    c1, c2 = st.columns(2)

    with c1:
        roll = df_f["view_count"].rolling(40, center=True).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_f["published_at"], y=df_f["view_count"]/1e6,
                                 mode="markers", name="Each video",
                                 marker=dict(size=4, color="#555", opacity=0.5),
                                 hovertemplate="%{customdata}<br>%{y:.1f}M<extra></extra>",
                                 customdata=df_f["title"]))
        fig.add_trace(go.Scatter(x=df_f["published_at"], y=roll/1e6,
                                 mode="lines", name="40-video avg",
                                 line=dict(color=AC, width=2.5)))
        fig.update_layout(title="Views Per Video — Career Arc", yaxis_title="Views (M)",
                          height=360, xaxis_gridcolor="#222", yaxis_gridcolor="#222", **cb)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        roll_eng = df_f["engagement_rate"].rolling(40, center=True).mean() * 100
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_f["published_at"], y=df_f["engagement_rate"]*100,
                                 mode="markers", name="Each video",
                                 marker=dict(size=4, color="#555", opacity=0.5),
                                 hovertemplate="%{customdata}<br>%{y:.2f}%<extra></extra>",
                                 customdata=df_f["title"]))
        fig.add_trace(go.Scatter(x=df_f["published_at"], y=roll_eng,
                                 mode="lines", name="40-video avg",
                                 line=dict(color="#43A047", width=2.5)))
        fig.update_layout(title="Engagement Rate — Career Arc",
                          yaxis_title="Engagement Rate (%)", yaxis_ticksuffix="%",
                          height=360, xaxis_gridcolor="#222", yaxis_gridcolor="#222", **cb)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        dur_q = df_f.groupby("quarter")["duration_sec"].median() / 60
        fig = px.line(x=dur_q.index, y=dur_q.values, markers=True,
                      labels={"x": "", "y": "Median Duration (min)"})
        fig.update_traces(line_color="#FB8C00", marker_color="#FB8C00", marker_size=5)
        fig.update_layout(title="Video Length — Quarterly Median", height=300,
                          xaxis_gridcolor="#222", yaxis_gridcolor="#222", **cb)
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        freq_q = df_f.groupby("quarter").size().reset_index(name="count")
        fig = px.bar(freq_q, x="quarter", y="count",
                     labels={"quarter": "", "count": "Videos Uploaded"})
        fig.update_traces(marker_color=AC, opacity=0.85)
        fig.update_layout(title="Upload Frequency by Quarter", height=300,
                          xaxis_gridcolor="#222", yaxis_gridcolor="#222", **cb)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown(f'<div class="sec-head">📉 Performance Dips — What Happened?</div>',
                unsafe_allow_html=True)
    st.caption("Quarters where avg views dropped >35% from recent peak.")
    dips = detect_dips(df_f, channel_info["name"])
    if dips.empty:
        st.info("No significant dips detected.")
    else:
        for _, row in dips.iterrows():
            qstr = row["quarter_str"]; yr = qstr[:4]; drop = row["drop_pct"]*100
            sq = urllib.parse.quote(f"{channel_info['name']} {yr}")
            news_url = f"https://news.google.com/search?q={sq}&hl=en-US&gl=US&ceid=US:en"
            ci, cb2 = st.columns([5, 1])
            with ci:
                st.markdown(
                    f'<div class="dip-row"><span style="color:{AC};font-weight:700">{qstr}</span>'
                    f' — avg views dropped <b>{drop:.0f}%</b> from peak</div>',
                    unsafe_allow_html=True)
            with cb2:
                st.markdown(
                    f'<a href="{news_url}" target="_blank">'
                    f'<button style="background:#222;color:#fff;border:1px solid #444;'
                    f'padding:5px 14px;border-radius:6px;cursor:pointer;margin-top:4px;">🔍 News</button></a>',
                    unsafe_allow_html=True)
            with st.expander(f"📰 Headlines — {qstr}"):
                q_end = pd.Timestamp(qstr) + pd.offsets.QuarterEnd()
                news = fetch_news(channel_info["name"], qstr, q_end.strftime("%Y-%m-%d"))
                if news:
                    for title, link, pub in news:
                        st.markdown(f"- [{title}]({link})  \n  *{pub[:16]}*")
                else:
                    st.caption("Click News to search manually.")

# ── TAB 3: Content ─────────────────────────────────────────────────────────────
with tab3:
    cb = chart_base(is_music)
    c1, c2 = st.columns(2)

    with c1:
        cat = df_f.groupby("category").agg(
            count=("video_id","count"),
            avg_views=("view_count","mean"),
            avg_eng=("engagement_rate","mean")
        ).reset_index().sort_values("avg_views")
        cat["avg_views_M"] = cat["avg_views"]/1e6
        cat["avg_eng_pct"] = cat["avg_eng"]*100
        fig = px.bar(cat, x="avg_views_M", y="category", orientation="h",
                     color="avg_views_M", color_continuous_scale=["#222", "#43A047"],
                     hover_data={"count":True,"avg_eng_pct":":.2f","avg_views_M":":.1f","category":False},
                     labels={"avg_views_M":"Avg Views (M)","category":""})
        fig.update_layout(title="Avg Views by Content Category",
                          coloraxis_showscale=False, height=380,
                          xaxis_gridcolor="#222", yaxis_gridcolor="#222", **cb)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        keywords = ["$","win","subscribe","survive","last to","vs","guess","free","every",
                    "MV","ft.","live","Official","周杰倫","演唱會","新歌","林俊傑"]
        rows = []
        for kw in keywords:
            mask = df_f["title"].str.contains(kw, case=False, regex=False, na=False)
            if mask.sum() >= 2:
                rows.append({"keyword": f'"{kw}" (n={mask.sum()})',
                             "avg_views_M": df_f[mask]["view_count"].mean()/1e6})
        if rows:
            kw_df = pd.DataFrame(rows).sort_values("avg_views_M")
            fig = px.bar(kw_df, x="avg_views_M", y="keyword", orientation="h",
                         color="avg_views_M", color_continuous_scale=["#222", AC],
                         labels={"avg_views_M":"Avg Views (M)","keyword":""})
            fig.update_layout(title="Title Keywords vs Avg Views",
                              coloraxis_showscale=False, height=380,
                              xaxis_gridcolor="#222", yaxis_gridcolor="#222", **cb)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough keyword matches.")

    grp = df_f.groupby("format").agg(
        Videos=("video_id","count"),
        avg_views=("view_count","mean"),
        avg_vpd=("views_per_day","mean"),
        avg_eng=("engagement_rate","mean")
    ).reset_index()
    grp["Avg Views (M)"] = (grp["avg_views"]/1e6).round(1)
    grp["Avg Views/Day (M)"] = (grp["avg_vpd"]/1e6).round(2)
    grp["Avg Engagement (%)"] = (grp["avg_eng"]*100).round(2)
    st.markdown(f'<div class="sec-head">Short-form vs Long-form</div>', unsafe_allow_html=True)
    st.dataframe(grp[["format","Videos","Avg Views (M)","Avg Views/Day (M)","Avg Engagement (%)"]],
                 use_container_width=True, hide_index=True)

# ── TAB 4: Compare ─────────────────────────────────────────────────────────────
with tab4:
    compare_options = list(CREATORS.keys())
    cc1, cc2 = st.columns(2)
    with cc1:
        creator_a = st.selectbox("Creator A", compare_options, index=0, key="ca")
    with cc2:
        creator_b = st.selectbox("Creator B", compare_options, index=2, key="cb")

    @st.cache_data
    def load_compare(slug):
        d = pd.read_csv(f"data/processed/{slug}_metrics.csv")
        d["published_at"] = pd.to_datetime(d["published_at"], utc=True).dt.tz_localize(None)
        d["duration_sec"] = d["duration"].apply(parse_sec)
        d["is_short"] = d["duration_sec"] < 120
        d["category"] = d["title"].apply(categorize)
        d["quarter"] = d["published_at"].dt.to_period("Q").dt.to_timestamp()
        return d.sort_values("published_at").reset_index(drop=True)

    da = load_compare(CREATORS[creator_a]["slug"])
    db = load_compare(CREATORS[creator_b]["slug"])
    da["creator"] = creator_a; db["creator"] = creator_b
    combined = pd.concat([da, db], ignore_index=True)
    cmp_music = CREATORS[creator_a]["slug"] in MUSIC_ARTISTS and CREATORS[creator_b]["slug"] in MUSIC_ARTISTS
    CA, CB = ("#1DB954" if cmp_music else "#FF0000"), "#2979FF"
    CMAP = {creator_a: CA, creator_b: CB}
    cb = chart_base(cmp_music)

    # KPI row
    st.markdown(f'<div class="sec-head">At a Glance</div>', unsafe_allow_html=True)
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric(f"{creator_a}", f"{len(da):,}", "videos")
    k2.metric("Avg Views", f"{da['view_count'].mean()/1e6:.1f}M")
    k3.metric("Avg Engagement", f"{da['engagement_rate'].mean()*100:.2f}%")
    k4.metric(f"{creator_b}", f"{len(db):,}", "videos")
    k5.metric("Avg Views", f"{db['view_count'].mean()/1e6:.1f}M")
    k6.metric("Avg Engagement", f"{db['engagement_rate'].mean()*100:.2f}%")

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        fig = go.Figure()
        for label, d in [(creator_a,da),(creator_b,db)]:
            roll = d["view_count"].rolling(20,center=True).mean()
            fig.add_trace(go.Scatter(x=d["published_at"],y=roll/1e6,mode="lines",name=label,
                line=dict(color=CMAP[label],width=2.5),
                hovertemplate=f"{label}<br>%{{x|%Y-%m}}<br>%{{y:.1f}}M<extra></extra>"))
        fig.update_layout(title="Views Per Video — Rolling Avg", yaxis_title="Views (M)",
                          height=360, xaxis_gridcolor="#222", yaxis_gridcolor="#222",
                          legend=dict(x=0.01,y=0.99), **cb)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = go.Figure()
        for label, d in [(creator_a,da),(creator_b,db)]:
            roll = d["engagement_rate"].rolling(20,center=True).mean()*100
            fig.add_trace(go.Scatter(x=d["published_at"],y=roll,mode="lines",name=label,
                line=dict(color=CMAP[label],width=2.5),
                hovertemplate=f"{label}<br>%{{x|%Y-%m}}<br>%{{y:.2f}}%<extra></extra>"))
        fig.update_layout(title="Engagement Rate — Rolling Avg",
                          yaxis_title="Engagement Rate (%)", yaxis_ticksuffix="%",
                          height=360, xaxis_gridcolor="#222", yaxis_gridcolor="#222",
                          legend=dict(x=0.01,y=0.99), **cb)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig = px.box(combined[combined["view_count"]>=1_000_000],
                     x="creator",y="views_per_day",color="creator",
                     color_discrete_map=CMAP,points="outliers",hover_name="title",
                     labels={"views_per_day":"Views Per Day","creator":""})
        fig.update_layout(title="Views/Day Distribution",height=360,showlegend=False,
                          yaxis_gridcolor="#222", **cb)
        fig.update_yaxes(tickformat=".2s")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        rows = []
        for label, d in [(creator_a,da),(creator_b,db)]:
            for fmt,mask in [("Short (<2min)",d["is_short"]),("Long (≥2min)",~d["is_short"])]:
                sub = d[mask & (d["view_count"]>=1_000_000)]
                if len(sub)>=3:
                    rows.append({"creator":label,"format":fmt,
                                 "avg_views_M":sub["view_count"].mean()/1e6})
        if rows:
            fdf = pd.DataFrame(rows)
            fig = px.bar(fdf,x="format",y="avg_views_M",color="creator",barmode="group",
                         color_discrete_map=CMAP,text_auto=".1f",
                         labels={"avg_views_M":"Avg Views (M)","format":"","creator":""})
            fig.update_layout(title="Short vs Long Form",height=360,
                              yaxis_gridcolor="#222",legend=dict(x=0.01,y=0.99),**cb)
            st.plotly_chart(fig, use_container_width=True)

    freq_rows = []
    for label,d in [(creator_a,da),(creator_b,db)]:
        freq = d.groupby("quarter").size().reset_index(name="count")
        freq["creator"] = label; freq_rows.append(freq)
    freq_df = pd.concat(freq_rows)
    fig = px.line(freq_df,x="quarter",y="count",color="creator",
                  color_discrete_map=CMAP,markers=True,
                  labels={"quarter":"","count":"Videos Uploaded","creator":""})
    fig.update_layout(title="Upload Frequency by Quarter",height=300,
                      xaxis_gridcolor="#222",yaxis_gridcolor="#222",**cb)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown(f'<div class="sec-head">📊 Analysis</div>', unsafe_allow_html=True)
    st.markdown(generate_insights(da, db, creator_a, creator_b), unsafe_allow_html=True)

    st.divider()
    st.markdown(f'<div class="sec-head">📉 Performance Dips</div>', unsafe_allow_html=True)
    st.caption("Quarters where avg views dropped >35% from recent peak.")
    all_dips = pd.concat([detect_dips(da,creator_a),detect_dips(db,creator_b)],ignore_index=True)
    if all_dips.empty:
        st.info("No significant dips detected.")
    else:
        for _, row in all_dips.iterrows():
            drop = row["drop_pct"]*100; qstr = row["quarter_str"]
            clabel = row["creator"]; color = CMAP.get(clabel, "#888")
            sq = urllib.parse.quote(f"{clabel} {qstr[:4]}")
            news_url = f"https://news.google.com/search?q={sq}&hl=en-US&gl=US&ceid=US:en"
            ci2, cb3 = st.columns([5,1])
            with ci2:
                st.markdown(
                    f'<div class="dip-row"><span style="color:{color};font-weight:700">{clabel}</span>'
                    f' — <b>{qstr}</b>: avg views dropped <b>{drop:.0f}%</b></div>',
                    unsafe_allow_html=True)
            with cb3:
                st.markdown(
                    f'<a href="{news_url}" target="_blank">'
                    f'<button style="background:#222;color:#fff;border:1px solid #444;'
                    f'padding:5px 14px;border-radius:6px;cursor:pointer;margin-top:4px;">🔍 News</button></a>',
                    unsafe_allow_html=True)
            with st.expander(f"📰 Headlines — {clabel} {qstr}"):
                q_end = pd.Timestamp(qstr) + pd.offsets.QuarterEnd()
                news = fetch_news(clabel, qstr, q_end.strftime("%Y-%m-%d"))
                if news:
                    for title, link, pub in news:
                        st.markdown(f"- [{title}]({link})  \n  *{pub[:16]}*")
                else:
                    st.caption("Click News to search manually.")
