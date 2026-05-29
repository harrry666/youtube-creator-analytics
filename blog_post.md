# Beyond Subscriber Counts: What 3,900+ YouTube Videos Actually Tell You

*A data breakdown of MrBeast, iShowSpeed, Mark Rober, Jay Chou, and JJ Lin, built with Python, Streamlit, and the YouTube Data API v3*

---

Subscriber counts tell you who showed up once. They don't tell you if a creator is growing, or if that viral video last month was a real signal or just luck.

I wanted to answer harder questions. So I built an analytics dashboard that pulled 3,912 videos across five creators, built six performance metrics from scratch, and ran them through the same framework. Some of what I found pushed back on assumptions I had going in.

---

## What the Project Does

The dashboard connects to the YouTube Data API v3 and pulls every public video for a given channel, including metadata, view counts, like counts, comment counts, publish dates, and duration.

From that raw data, I built six metrics that measure what subscriber counts can't.

**Composite Score (0-100)** weights views-per-day at 40%, engagement rate at 35%, and total views at 25%. Views-per-day captures current momentum. Engagement rate captures community depth. Total views anchors it to scale. Each component is log-normalized across the dataset so the scores are meaningful across channels with very different sizes.

**Virality Score** computes per-video views-per-day normalized to the channel average. Any video exceeding 3x the channel average qualifies as viral.

**Momentum Index** divides a creator's recent 90-day average by their all-time average. A score above 1.0 means the creator is outperforming their own history. A score below 1.0 means the channel is contracting, regardless of what the absolute view count looks like.

**Viral Hit Rate** measures what fraction of videos exceed 2x the channel's own average views/day. It captures how consistently a creator produces standout content.

**Comment-to-Like Ratio** is a proxy for fandom depth. Passive viewers watch and leave. Active communities comment. A high ratio means the audience is actually invested.

---

## The Findings

### MrBeast: Big Reach, Flat Trajectory

MrBeast is the most-viewed creator in this dataset. He's also the one whose numbers reveal the most tension between surface success and what's actually happening underneath.

Short-form content generates 3.2x more views-per-day than his long-form videos. "Subscribe for an iPhone" accumulated 1.22 billion views in 127 days. That's 9.59 million views per day.

Titles with a "$" sign average 1.8x the channel average. The money-prize format is the single most reliable driver in his catalog.

The number that tells the real story: Momentum Index of 1.01. Essentially flat. Despite record-breaking individual videos, MrBeast's channel isn't growing. The ceiling is high. The trajectory is horizontal.

His engagement rate sits around 2.96%. Hundreds of millions of people watch. A fraction of a percent hit like. Massive reach, but the community isn't particularly deep.

If YouTube's algorithm shifts or a platform migration becomes necessary, a passive audience is a fragile asset.

### iShowSpeed: Volume as Strategy

iShowSpeed uploads at 7.8 videos per week, which is the highest cadence in the dataset by far. Volume is the strategy. The question is whether it works.

The viral hit rate answers that: 41%. Fewer than half his videos beat 2x the channel average. He floods the zone and waits for the spikes. Consistency is secondary.

Where Speed separates himself is comment-to-like ratio. It's 3x higher than MrBeast's. The same viewer who passively clicks play on a MrBeast short is typing in Speed's comment section. That's a fundamentally different relationship.

High-cadence, high-variance output with a community that stays engaged through the misses. It's a different model.

### Mark Rober: One Video at a Time

Mark Rober uploads 0.4 videos per week. One video every 2.5 weeks. By conventional platform logic, that cadence should hurt algorithmic distribution.

It doesn't. Rober has the highest consistency score in the dataset. Long-form content outperforms short-form by 4.1x in views-per-day. That's the inverse of what MrBeast sees.

His content decay ratio is also the flattest in this dataset. Fresh uploads (0-30 days) pull about 7.9x more views/day than his 2-year-old catalog. For comparison, iShowSpeed's ratio is over 200x. Rober's old videos are still getting watched. Most YouTube content isn't.

The risk: one underperforming video tanks the quarter. There's no buffer. Each release carries disproportionate weight.

### Jay Chou vs JJ Lin: Two Different Catalog Plays

Jay Chou averages 14.2x more views per video than JJ Lin. By raw scale, there's no comparison.

JJ Lin leads on engagement rate: 3.1% versus 1.8%. His audience is proportionally more active and more likely to interact with every upload.

Neither artist has uploaded anything significant recently. Jay Chou's catalog earns passively. Music MVs accumulate views over decades without anyone needing to do anything. JJ Lin's audience has a higher floor of engagement per view. His "謝幕 Hero" teaser hit 9.59% engagement with virtually zero views. The fans showed up regardless.

Both work as catalog plays. Jay Chou scales through reach. JJ Lin scales through community density.

---

## What the Data Actually Shows

**Views-per-day is a better signal than total views.** A video published in 2015 with 50 million total views is not the same asset as a video published last month with 5 million. Views-per-day normalizes for time and shows what's working right now.

**Consistency and reach are almost never optimized at the same time.** MrBeast has massive reach and moderate consistency. Mark Rober has high consistency and concentrated risk. iShowSpeed has volume and community. The trade-offs are structural, not accidental.

**The Momentum Index is the metric most creators aren't tracking.** A channel can post record-breaking individual videos while the underlying 90-day trajectory is flat. MrBeast's 1.01 Momentum Index is exactly that situation. The individual hits look like growth. The rolling average tells you otherwise.

**Comment-to-like ratio predicts community durability better than view counts.** iShowSpeed's 3x ratio advantage over MrBeast is a structural difference in what each audience is willing to do. Advertisers buy reach. Creators building something durable are building comment sections.

---

## The Bigger Picture

Three distinct viable models show up in this data. High-frequency volatility (iShowSpeed). Low-frequency precision (Mark Rober). High-scale distribution (MrBeast). Each has a different cost structure and a different audience contract.

Data doesn't tell you what content to make. It tells you whether what you're making is doing what you think it is. For most creators at scale, there's a real gap between those two things.

---

**Tech stack:** Python, Pandas, Streamlit, Plotly, YouTube Data API v3

**Data:** 3,912 videos across 5 channels, pulled May 2026

*Built as part of a creator economy analytics portfolio. Full dashboard and methodology on GitHub.*

*Harry Yin is a Data Science junior at UC Berkeley focused on product analytics and creator economy research.*
