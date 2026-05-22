import os
import re
import requests
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"
PLAYLIST_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

def get_channel_info(channel_id):
    r = requests.get(CHANNEL_URL, params={
        "part": "snippet,contentDetails,statistics",
        "id": channel_id, "key": API_KEY
    })
    r.raise_for_status()
    item = r.json()["items"][0]
    return {
        "name": item["snippet"]["title"],
        "avatar": item["snippet"]["thumbnails"]["high"]["url"],
        "uploads_playlist": item["contentDetails"]["relatedPlaylists"]["uploads"],
        "subscriber_count": item["statistics"].get("subscriberCount"),
        "video_count": item["statistics"].get("videoCount"),
    }

def get_all_video_ids(playlist_id):
    video_ids, page_token = [], None
    while True:
        params = {"part": "snippet", "playlistId": playlist_id,
                  "maxResults": 50, "key": API_KEY}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(PLAYLIST_URL, params=params)
        r.raise_for_status()
        data = r.json()
        for item in data.get("items", []):
            video_ids.append(item["snippet"]["resourceId"]["videoId"])
        page_token = data.get("nextPageToken")
        print(f"  fetched {len(video_ids)} video IDs...", end="\r")
        if not page_token:
            break
    return video_ids

def get_video_details(video_ids):
    rows = []
    now = datetime.now(timezone.utc)
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        r = requests.get(VIDEOS_URL, params={
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(batch), "key": API_KEY
        })
        r.raise_for_status()
        for item in r.json().get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            cd = item.get("contentDetails", {})
            published = snippet.get("publishedAt")
            try:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                age_days = max((now - pub_dt).days, 1)
            except Exception:
                pub_dt, age_days = None, 1
            view_count = int(stats.get("viewCount") or 0)
            like_count = int(stats.get("likeCount") or 0)
            comment_count = int(stats.get("commentCount") or 0)
            rows.append({
                "video_id": item.get("id"),
                "title": snippet.get("title"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": pub_dt,
                "category_id": snippet.get("categoryId"),
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "duration": cd.get("duration"),
                "video_age_days": age_days,
                "views_per_day": round(view_count / age_days, 2),
                "like_rate": like_count / view_count if view_count else 0,
                "comment_rate": comment_count / view_count if view_count else 0,
                "engagement_rate": (like_count + comment_count) / view_count if view_count else 0,
            })
    return pd.DataFrame(rows)

def fetch_creator(channel_id, slug):
    print(f"Fetching channel info for {slug}...")
    info = get_channel_info(channel_id)
    print(f"Channel: {info['name']}")

    print("Fetching all video IDs...")
    video_ids = get_all_video_ids(info["uploads_playlist"])
    print(f"\nTotal: {len(video_ids)} videos")

    print("Fetching video details...")
    df = get_video_details(video_ids)

    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    raw_path = f"data/raw/{slug}_videos.csv"
    processed_path = f"data/processed/{slug}_metrics.csv"
    df.to_csv(raw_path, index=False)
    df.to_csv(processed_path, index=False)
    print(f"Saved {len(df)} videos → {processed_path}")
    return df

if __name__ == "__main__":
    import sys
    channel_id = sys.argv[1] if len(sys.argv) > 1 else "UCKUlsqazP-4QmxdEtUPlxOA"
    slug = sys.argv[2] if len(sys.argv) > 2 else "jaychou"
    fetch_creator(channel_id, slug)
