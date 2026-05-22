import pandas as pd
from datetime import datetime, timezone

INPUT_PATH = "data/raw/mrbeast_recent_videos.csv"
OUTPUT_PATH = "data/processed/mrbeast_metrics.csv"

def main():
    df = pd.read_csv(INPUT_PATH)

    df["view_count"] = pd.to_numeric(df["view_count"], errors="coerce")
    df["like_count"] = pd.to_numeric(df["like_count"], errors="coerce")
    df["comment_count"] = pd.to_numeric(df["comment_count"], errors="coerce")

    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)

    today = datetime.now(timezone.utc)
    df["video_age_days"] = (today - df["published_at"]).dt.days
    df["video_age_days"] = df["video_age_days"].replace(0, 1)

    df["views_per_day"] = df["view_count"] / df["video_age_days"]
    df["like_rate"] = df["like_count"] / df["view_count"]
    df["comment_rate"] = df["comment_count"] / df["view_count"]
    df["engagement_rate"] = (df["like_count"] + df["comment_count"]) / df["view_count"]

    df = df.sort_values("views_per_day", ascending=False)

    print("\nTop videos by views per day:")
    print(df[["title", "view_count", "video_age_days", "views_per_day", "engagement_rate"]].head(10))

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved processed data to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()