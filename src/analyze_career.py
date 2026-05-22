import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates

INPUT_PATH = "data/processed/mrbeast_metrics.csv"
OUTPUT_PATH = "outputs/figures/mrbeast_career_analysis.png"

CATEGORIES = {
    "Subscribe Bait": r"\bsubscribe\b",
    "Survive/Stranded": r"surviv|strand|island|wilderness",
    "Last To": r"last to",
    "Guess Challenge": r"\bguess\b",
    "Vs/Race": r"\bvs\b|\bracer?d?\b",
    "Win \$": r"win \$|,000",
}

def categorize(title):
    t = title.lower()
    for label, pat in CATEGORIES.items():
        if re.search(pat, t):
            return label
    return "Other"

def parse_sec(s):
    h = re.search(r'(\d+)H', s)
    m = re.search(r'(\d+)M', s)
    sec = re.search(r'(\d+)S', s)
    return (int(h.group(1)) * 3600 if h else 0) + \
           (int(m.group(1)) * 60 if m else 0) + \
           (int(sec.group(1)) if sec else 0)

def main():
    df = pd.read_csv(INPUT_PATH)
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    df["duration_sec"] = df["duration"].apply(parse_sec)
    df["category"] = df["title"].apply(categorize)
    df = df.sort_values("published_at").reset_index(drop=True)

    quarter_idx = df["published_at"].dt.to_period("Q").dt.to_timestamp()

    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(18, 14))
    fig.suptitle("MrBeast Career Analysis — 981 Videos", fontsize=16, fontweight="bold")

    RED, BLUE, GREEN, ORANGE = "#E53935", "#1E88E5", "#43A047", "#FB8C00"

    # 1. Views per video over career (scatter + rolling avg)
    ax1 = fig.add_subplot(3, 2, 1)
    ax1.scatter(df["published_at"], df["view_count"] / 1e6, alpha=0.25, s=6, color=BLUE)
    roll = df["view_count"].rolling(40, center=True).mean()
    ax1.plot(df["published_at"], roll / 1e6, color=RED, linewidth=2, label="40-video rolling avg")
    ax1.set_ylabel("Views (M)")
    ax1.set_title("Views Per Video Over Career")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.legend(fontsize=8)

    # 2. Avg views by content category
    ax2 = fig.add_subplot(3, 2, 2)
    cat_avg = df.groupby("category")["view_count"].mean().sort_values() / 1e6
    ax2.barh(cat_avg.index, cat_avg.values, color=GREEN)
    ax2.set_xlabel("Avg Views (M)")
    ax2.set_title("Avg Views by Content Category")
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}M"))

    # 3. Video duration trend by quarter
    ax3 = fig.add_subplot(3, 2, 3)
    dur_trend = df.groupby(quarter_idx)["duration_sec"].median() / 60
    ax3.plot(dur_trend.index, dur_trend.values, color=ORANGE, marker="o", markersize=3, linewidth=2)
    ax3.set_ylabel("Median Duration (min)")
    ax3.set_title("Video Duration Trend by Quarter")
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax3.xaxis.set_major_locator(mdates.YearLocator())

    # 4. Upload frequency by quarter
    ax4 = fig.add_subplot(3, 2, 4)
    upload_freq = df.groupby(quarter_idx).size()
    ax4.bar(upload_freq.index, upload_freq.values, width=60, color=BLUE, alpha=0.8)
    ax4.set_ylabel("Videos Uploaded")
    ax4.set_title("Upload Frequency by Quarter")
    ax4.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax4.xaxis.set_major_locator(mdates.YearLocator())

    # 5. Engagement rate trend over career (rolling avg)
    ax5 = fig.add_subplot(3, 2, 5)
    roll_eng = df["engagement_rate"].rolling(40, center=True).mean() * 100
    ax5.scatter(df["published_at"], df["engagement_rate"] * 100, alpha=0.2, s=6, color=GREEN)
    ax5.plot(df["published_at"], roll_eng, color=GREEN, linewidth=2)
    ax5.set_ylabel("Engagement Rate (%)")
    ax5.set_title("Engagement Rate Trend Over Career")
    ax5.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax5.xaxis.set_major_locator(mdates.YearLocator())
    ax5.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))

    # 6. Title keywords vs avg views
    ax6 = fig.add_subplot(3, 2, 6)
    keywords = ["$", "win", "subscribe", "survive", "last to", "vs", "guess", "free", "every", "i "]
    rows = []
    for kw in keywords:
        mask = df["title"].str.lower().str.contains(kw, regex=False)
        if mask.sum() >= 3:
            rows.append({"keyword": f'"{kw.strip()}" (n={mask.sum()})',
                         "avg_views": df[mask]["view_count"].mean() / 1e6})
    kw_df = pd.DataFrame(rows).sort_values("avg_views")
    ax6.barh(kw_df["keyword"], kw_df["avg_views"], color=RED)
    ax6.set_xlabel("Avg Views (M)")
    ax6.set_title("Title Keywords vs Avg Views")
    ax6.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}M"))

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Saved: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
