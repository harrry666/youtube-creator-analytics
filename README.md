# YouTube Creator Analytics Dashboard

An analytics dashboard for YouTube creator performance — built with live API data, no toy datasets.

**Live data from YouTube Data API v3.**

🔗 **[Live Dashboard](https://youtube-creator-analytics-bpn8qc3pfwjgedrrd2ppw7.streamlit.app/)**

---

## Research Question

**What content strategies and channel behaviors best predict sustainable view velocity — and how do top YouTube creators trade off reach versus community depth?**

Hypothesis: high-cadence creators (iShowSpeed) maximize reach through volume; low-cadence creators (Mark Rober) maximize depth through production quality. No single creator dominates both axes simultaneously. The data covers 3,915 videos across 5 creators to test this.

---

## What It Does

This dashboard turns raw YouTube API data into answers that actually matter for creator teams. It answers the questions that count in creator economy analytics:

- Is this channel growing or contracting right now?
- Which content format generates the most views per day?
- What title patterns actually drive performance?
- Which videos are viral outliers vs. consistent performers?
- How does this creator compare to a competitor on the same time window?

---

## Key Features

### Analytics Engine
- **Composite Score (0–100)** — weighted index: views/day (40%) + engagement rate (35%) + total views (25%)
- **Virality Score** — per-video views/day normalized to channel average. >3x = viral
- **Momentum Index** — recent 90-day avg / all-time avg. Leading indicator of channel trajectory
- **Hit Rate** — fraction of videos that beat the channel median. Measures consistency
- **Consistency Score** — 1 − coefficient of variation of views/day. Lower variance = higher score
- **Comment-to-Like Ratio** — proxy for fandom depth vs. passive viewership

### Data Quality
- Automatic validation on load: removes zero-view rows, deduplicates by video ID, caps impossible engagement rates
- Data health panel in sidebar with specific warnings per dataset
- Statistical outlier flagging (>4σ view count)

### Anomaly Detection
- Z-score based detection on views/day for each video
- Classification: Mega Viral (5σ+), Viral (3σ+), Above-Avg Spike, Underperformed
- Quarterly dip detection: flags quarters where avg views dropped >35% from rolling 4-quarter peak
- News search integration: click through to relevant headlines for any dip period

### Content Strategy Recommendations
Rule-based engine that generates prioritized, actionable recommendations:
- Format efficiency (short vs. long form)
- Title keyword impact analysis
- Posting cadence vs. algorithm signal
- Engagement activation tactics
- Momentum recovery when channel is declining

### Executive Insights
Dynamically generated insight blocks with specific numbers and direct conclusions. Each insight leads with data, ends with a decision.

### Interactive Filters (apply to all tabs)
- Date range slider
- Format filter: All / Short-form (<2 min) / Long-form (≥2 min)
- Minimum views threshold
- Top N for chart rankings

### Comparison Mode
- Head-to-head KPI table for any two creators
- Configurable start date for fair time-window comparison
- Rolling average overlays, distribution boxplots, upload frequency
- Auto-generated comparison insights

### Export
- **Full dataset CSV** — all metrics, scores, anomaly flags
- **Executive summary report (.txt)** — KPIs, top 5 videos, anomalies, recommendations
- **Leaderboard CSV** — top N videos by composite score

---

## Dashboard Tabs

| Tab | What's Inside |
|-----|---------------|
| 📊 Overview | Performance leaderboard with composite scores, anomaly report |
| 📈 Performance | Views/day ranking, composite score ranking, engagement vs. velocity scatter |
| 🕰️ Career Arc | Career trajectory with rolling averages, quarterly upload frequency, dip detection |
| 🔍 Content DNA | Category breakdown, title keyword impact, short vs. long form analysis |
| 💡 Insights & Recs | 5 executive insight blocks + prioritized strategy recommendations |
| ⚔️ Compare | Two-creator comparison with head-to-head KPIs and analysis |
| 📤 Export | CSV download, text report, leaderboard export |

---

## Creators Covered

| Creator | Videos | Domain |
|---------|--------|--------|
| MrBeast | ~980 | Entertainment |
| IShowSpeed | ~1,860 | Gaming / Lifestyle |
| Mark Rober | ~256 | Science / Engineering |
| Jay Chou 周杰倫 | ~325 | Music |
| JJ Lin 林俊傑 | ~491 | Music |

---

## Key Findings

**MrBeast**
Short-form content generates **3.2x** more views/day than long-form. Videos with "$" in the title average **1.8x** the channel average. Momentum index of 1.01 — channel is flat, not growing, despite record-breaking individual videos.

**iShowSpeed**
Highest upload cadence at **7.8 videos/week**. Hit rate of 38% — performance is driven by reaction content spikes, not consistent output. Comment-to-like ratio 3x higher than MrBeast — significantly deeper community engagement per view.

**Mark Rober**
Lowest cadence (0.4 videos/week) but highest consistency score. Each video carries enormous weight — one miss tanks the quarter. Long-form dominates: **4.1x** more views/day than his short-form content.

**Jay Chou vs JJ Lin**
Jay Chou's catalog averages **14.2x** more views per video — driven by decades of catalog accumulation. JJ Lin leads on engagement rate (3.1% vs 1.8%). Different audience behavior: Jay Chou has passive reach, JJ Lin has active community.

---

## Tech Stack

```
Python 3.12
Streamlit 1.57    — dashboard framework
Plotly 6.7        — interactive charts
Pandas 3.0        — data processing
NumPy 2.4         — numerical operations
YouTube Data API v3 — data source
```

---

## Project Structure

```
youtube-creater-analytics/
├── app.py                  # Main dashboard (Streamlit)
├── src/
│   ├── metrics.py          # KPI calculation functions
│   ├── anomaly.py          # Spike / dip detection
│   ├── insights.py         # Executive insight generation
│   ├── recommender.py      # Rule-based recommendation engine
│   └── fetch_creator.py    # YouTube API data collection
├── data/
│   ├── raw/                # Raw API responses
│   ├── processed/          # Enriched metrics CSVs
│   └── channel_info.json   # Channel metadata
└── outputs/figures/        # Static chart exports
```

---

## Running Locally

```bash
git clone <repo>
cd youtube-creater-analytics
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Add your YouTube Data API key
echo "YOUTUBE_API_KEY=your_key_here" > .env

# Fetch data for a creator (channel ID required)
python src/fetch_creator.py UCX6OQ3DkcsbYNE6H8uQQuVA mrbeast

# Launch dashboard
streamlit run app.py
```

---

## Fetching New Creator Data

```bash
python src/fetch_creator.py <CHANNEL_ID> <SLUG>
```

Then add the creator to the `CREATORS` dict in `app.py` and update `data/channel_info.json`.

---

## Skills Demonstrated

- **Product Analytics**: Composite scoring, funnel metrics, cohort-style trend analysis
- **Data Engineering**: API data collection, validation pipeline, modular transformation
- **Insight Generation**: Rule-based systems, pattern detection, business-framed recommendations
- **Data Visualization**: Interactive Plotly charts, custom Streamlit CSS, dark-mode design system
- **Creator Economy Domain**: YouTube algorithm mechanics, engagement vs. reach trade-offs, format strategy

---

*Built by Harry Yin · UC Berkeley Data Science · 2026*
