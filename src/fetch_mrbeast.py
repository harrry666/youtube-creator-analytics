import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

CHANNEL_ID = "UCX6OQ3DkcsbYNE6H8uQQuVA"
CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"
PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

def get_uploads_playlist_id(channel_id):
    params = {
        "part": "contentDetails",
        "id": channel_id,
        "key": API_KEY
    }

    response = requests.get(CHANNEL_URL, params=params)
    response.raise_for_status()
    data = response.json()

    return data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

def get_all_video_ids(playlist_id):
    video_ids = []
    page_token = None

    while True:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
            "key": API_KEY
        }
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(PLAYLIST_ITEMS_URL, params=params)
        response.raise_for_status()
        data = response.json()

        for item in data.get("items", []):
            video_ids.append(item["snippet"]["resourceId"]["videoId"])

        page_token = data.get("nextPageToken")
        if not page_token:
            break

        print(f"  fetched {len(video_ids)} so far...", end="\r")

    return video_ids

def get_video_details(video_ids):
    rows = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(batch),
            "key": API_KEY
        }
        response = requests.get(VIDEOS_URL, params=params)
        response.raise_for_status()
        for item in response.json().get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            cd = item.get("contentDetails", {})
            rows.append({
                "video_id": item.get("id"),
                "title": snippet.get("title"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "category_id": snippet.get("categoryId"),
                "view_count": stats.get("viewCount"),
                "like_count": stats.get("likeCount"),
                "comment_count": stats.get("commentCount"),
                "duration": cd.get("duration")
            })
    return pd.DataFrame(rows)

def main():
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY not found. Please check your .env file.")

    uploads_playlist_id = get_uploads_playlist_id(CHANNEL_ID)
    print("Fetching all video IDs...")
    video_ids = get_all_video_ids(uploads_playlist_id)
    print(f"\nTotal video IDs: {len(video_ids)}")
    print("Fetching video details...")
    df = get_video_details(video_ids)

    output_path = "data/raw/mrbeast_recent_videos.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} videos to {output_path}")

if __name__ == "__main__":
    main()