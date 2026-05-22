import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch

INPUT_PATH = "data/processed/mrbeast_metrics.csv"
OUTPUT_PATH = "outputs/figures/mrbeast_dashboard.png"

def parse_duration_seconds(s):
    h = re.search(r'(\d+)H', s)
    m = re.search(r'(\d+)M', s)
    sec = re.search(r'(\d+)S', s)
    return (int(h.group(1)) * 3600 if h else 0) + \
           (int(m.group(1)) * 60 if m else 0) + \
           (int(sec.group(1)) if sec else 0)

def trim(title, n=32):
    return title if len(title) <= n else title[:n-1] + "…"

def main():
    df = pd.read_csv(INPUT_PATH)
    df["published_at"] = pd.to_datetime(df["published_at"])
    df["duration_sec"] = df["duration"].apply(parse_duration_seconds)
    df["is_short"] = df["duration_sec"] < 120
    df["label"] = df["title"].apply(trim)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle("MrBeast YouTube Performance Analysis (May 2026)", fontsize=15, fontweight="bold")

    RED, GREEN, BLUE = "#E53935", "#43A047", "#1E88E5"

    # 1. Top 10 by views per day
    ax = axes[0, 0]
    top = df.nlargest(10, "views_per_day").sort_values("views_per_day")
    ax.barh(top["label"], top["views_per_day"] / 1e6, color=RED)
    ax.set_xlabel("Views Per Day (M)")
    ax.set_title("Top 10 Videos by Views Per Day")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}M"))

    # 2. Top 10 by engagement rate
    ax = axes[0, 1]
    top = df.nlargest(10, "engagement_rate").sort_values("engagement_rate")
    ax.barh(top["label"], top["engagement_rate"] * 100, color=GREEN)
    ax.set_xlabel("Engagement Rate (%)")
    ax.set_title("Top 10 Videos by Engagement Rate")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))

    # 3. Views per day vs engagement rate scatter (bubble = view_count)
    ax = axes[1, 0]
    colors = [RED if s else BLUE for s in df["is_short"]]
    sizes = (df["view_count"] / df["view_count"].max() * 400 + 40).values
    ax.scatter(df["views_per_day"] / 1e6, df["engagement_rate"] * 100,
               c=colors, s=sizes, alpha=0.75, edgecolors="white", linewidths=0.5)
    ax.set_xlabel("Views Per Day (M)")
    ax.set_ylabel("Engagement Rate (%)")
    ax.set_title("Views Per Day vs Engagement Rate")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}M"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    ax.legend(handles=[Patch(facecolor=RED, label="Short-form (<2 min)"),
                       Patch(facecolor=BLUE, label="Long-form (≥2 min)")], loc="upper right")

    # 4. Short vs long form avg comparison (dual axis)
    ax = axes[1, 1]
    grp = df.groupby("is_short").agg(
        vpd=("views_per_day", "mean"),
        eng=("engagement_rate", "mean")
    ).reset_index()
    grp["fmt"] = grp["is_short"].map({True: "Short-form\n(<2 min)", False: "Long-form\n(≥2 min)"})
    x = range(len(grp))
    w = 0.35
    ax.bar([i - w/2 for i in x], grp["vpd"] / 1e6, w, label="Avg Views/Day (M)", color=RED, alpha=0.85)
    ax2 = ax.twinx()
    ax2.bar([i + w/2 for i in x], grp["eng"] * 100, w, label="Avg Engagement (%)", color=GREEN, alpha=0.85)
    ax.set_xticks(list(x))
    ax.set_xticklabels(grp["fmt"])
    ax.set_ylabel("Avg Views Per Day (M)", color=RED)
    ax2.set_ylabel("Avg Engagement Rate (%)", color=GREEN)
    ax.set_title("Short-form vs Long-form: Views & Engagement")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right")

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Saved: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
