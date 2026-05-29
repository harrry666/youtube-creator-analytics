# Beyond Subscriber Counts: What 3,900+ YouTube Videos Actually Tell You About Creator Performance

*A data-driven breakdown of MrBeast, iShowSpeed, Mark Rober, Jay Chou, and JJ Lin — built with Python, Streamlit, and the YouTube Data API v3*

---

Subscriber counts are a vanity metric. They tell you who showed up once. They tell you nothing about whether a creator is growing, or whether that one viral video last month was a signal or a fluke.

I wanted to answer harder questions. So I built an analytics dashboard that pulled 3,912 videos across five creators, engineered six performance metrics from scratch, and ran them through the same analytical framework. The results push back on a lot of assumptions about who the "best" creators actually are.

---

## What the Project Does

The dashboard connects to the YouTube Data API v3 and pulls every public video for a given channel — metadata, view counts, like counts, comment counts, publish dates, duration.

From that raw data, I built six metrics that measure what subscriber counts can't:

**Composite Score (0–100)** weights views-per-day at 40%, engagement rate at 35%, and total views at 25%. Views-per-day captures current momentum. Engagement rate captures community depth. Total views anchors it to scale. Each component is normalized across all creators in the dataset so the scores are directly comparable.

**Virality Score** computes per-video views-per-day normalized to the channel average. Any video exceeding 3x the channel average qualifies as viral.

**Momentum Index** divides a creator's recent 90-day average by their all-time average. A score above 1.0 means the creator is currently outperforming their historical baseline. A score below 1.0 means the channel is declining — regardless of what the absolute view count looks like.

**Hit Rate** measures what fraction of videos beat the channel's own median. A 60% hit rate means consistently above average. A 35% hit rate means swinging for the fences and missing more than hitting.

**Consistency Score** is defined as 1 minus the coefficient of variation of views-per-day. High consistency means reliable, predictable performance. Low consistency means a few massive hits are carrying a long tail of underperformers.

**Comment-to-Like Ratio** is a proxy for fandom depth. Passive viewers watch and leave. Active communities comment. A high ratio means viewers feel invested enough to participate.

---

## The Findings

### MrBeast: Maximum Reach, Shallow Roots

MrBeast is the most-viewed creator in this dataset. He's also the one whose numbers reveal the most tension between surface success and structural risk.

Short-form content generates **3.2x more views-per-day** than his long-form videos. His best-performing short — "Subscribe for an iPhone" — accumulated **1.22 billion views in 127 days**, which works out to **9.59 million views per day**.

Titles containing the "$" sign average **1.8x the channel average** in views. The money-prize format is the single most reliable performance driver in his catalog.

The number that matters most: **Momentum Index of 1.01**. Essentially flat. Despite record-breaking individual videos, MrBeast's channel is not accelerating. The ceiling is high. The trajectory is horizontal.

His engagement rate sits around **0.7%** — lowest in the dataset. Hundreds of millions of people watch MrBeast. A fraction of a percent hit like. Massive reach, shallow community.

The implication: MrBeast has built the world's largest YouTube distribution machine. But distribution and community are different assets. If YouTube's algorithm shifts, or if a platform migration becomes necessary, the passive audience doesn't follow.

---

### iShowSpeed: The Volatility Play

iShowSpeed uploads at **7.8 videos per week** — highest cadence in the dataset by far. Volume is the strategy. The question is whether it works.

The hit rate answers that: **38%**. Fewer than 4 in 10 videos beat the channel's own median. Speed floods the zone and waits for the spikes. Consistency is secondary.

The metric where Speed separates himself is comment-to-like ratio — **3x higher than MrBeast's**. The same viewer who passively clicks play on a MrBeast short is actively typing in Speed's comment section. That's a fundamentally different relationship between creator and audience.

The model is high-cadence, high-variance output with a community that stays engaged through the misses. Different risk profile from MrBeast. Different, period.

---

### Mark Rober: The Precision Manufacturer

Mark Rober uploads **0.4 videos per week** — one video every 2.5 weeks. By conventional platform logic, that cadence should hurt algorithmic distribution.

It doesn't. Rober has the highest consistency score in the dataset. Long-form content outperforms short-form by **4.1x in views-per-day** — the inverse of MrBeast.

The risk is visible in the data: one underperforming video tanks the quarter. There's no high-cadence buffer. Rober's output is concentrated, so each release carries disproportionate weight.

This is the creator-as-auteur model. High production value, low frequency. The audience gets trained to wait. It works until it doesn't.

---

### Jay Chou vs. JJ Lin: Reach vs. Community

Jay Chou averages **14.2x more views per video** than JJ Lin. By raw scale, there's no comparison.

JJ Lin leads on engagement rate: **3.1% versus 1.8%**. Lin's audience is proportionally more active and more likely to interact with every upload.

Jay Chou's catalog earns passively. Music accumulates views without requiring anyone to show up regularly. JJ Lin's audience has a higher floor of engagement per view. Both work — Jay Chou scales through reach, JJ Lin scales through community density.

---

## The Bigger Takeaways

**Views-per-day is a better performance signal than total views.** A video published in 2015 with 50 million total views is not the same asset as a video published last month with 5 million. Views-per-day normalizes for time and shows what's actually working right now.

**Consistency and reach are almost never optimized at the same time.** MrBeast has massive reach and low consistency. Mark Rober has high consistency and concentrated risk. iShowSpeed has volume and community. The tradeoffs are structural, not accidental.

**The Momentum Index is the metric that most creators aren't tracking.** A channel can be posting record-breaking videos while the underlying growth trajectory is flat. MrBeast's 1.01 momentum index is exactly that — the individual hits look like growth, the 90-day rolling average tells you otherwise.

**Comment-to-like ratio predicts community durability better than view counts.** Advertisers buy reach. Platforms reward engagement. Creators building the next decade are building comment sections. View counts follow. iShowSpeed's 3x ratio advantage over MrBeast is a structural difference in what each audience is willing to do.

---

## What This Shows About the Creator Economy

Three distinct viable models exist here. High-frequency volatility (iShowSpeed). Low-frequency precision (Mark Rober). High-scale distribution (MrBeast). Each model has a different cost structure and a different audience contract.

The creators building durable businesses understand which model they're in — and engineer their output accordingly. The ones who don't end up with MrBeast's reach and none of iShowSpeed's community, or Mark Rober's quality and none of the consistency.

Data doesn't tell you what content to make. It tells you whether what you're making is doing what you think it is. For most creators operating at scale, there's a significant gap between those two things.

---

**Tech stack:** Python · Pandas · Streamlit · Plotly · YouTube Data API v3

**Data:** 3,912 videos across 5 channels, pulled May 2026

*Built as part of a creator economy analytics portfolio. Full dashboard, metric definitions, and methodology available on GitHub.*

---

*Harry Yin is a Data Science junior at UC Berkeley focused on product analytics and creator economy research.*
