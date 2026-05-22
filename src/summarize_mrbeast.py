import pandas as pd

INPUT_PATH = "data/processed/mrbeast_metrics.csv"

def main():
    df = pd.read_csv(INPUT_PATH)

    print("MrBeast Recent Video Performance Summary")
    print("---------------------------------------")
    print(f"Number of videos analyzed: {len(df)}")
    print(f"Average views: {df['view_count'].mean():,.0f}")
    print(f"Average views per day: {df['views_per_day'].mean():,.0f}")
    print(f"Average engagement rate: {df['engagement_rate'].mean():.2%}")

    top_views = df.sort_values("view_count", ascending=False).iloc[0]
    top_growth = df.sort_values("views_per_day", ascending=False).iloc[0]
    top_engagement = df.sort_values("engagement_rate", ascending=False).iloc[0]

    print("\nTop video by total views:")
    print(f"{top_views['title']} - {top_views['view_count']:,.0f} views")

    print("\nTop video by views per day:")
    print(f"{top_growth['title']} - {top_growth['views_per_day']:,.0f} views/day")

    print("\nTop video by engagement rate:")
    print(f"{top_engagement['title']} - {top_engagement['engagement_rate']:.2%}")

if __name__ == "__main__":
    main()