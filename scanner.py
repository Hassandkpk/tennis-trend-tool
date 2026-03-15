from datetime import datetime, timezone
import isodate
from googleapiclient.discovery import build

from competitors import COMPETITOR_CHANNELS


def get_youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)


def calculate_velocity(video: dict):
    views = int(video.get("statistics", {}).get("viewCount", 0))
    published_at = video["snippet"]["publishedAt"]
    published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

    hours_since_upload = (datetime.now(timezone.utc) - published_dt).total_seconds() / 3600
    if hours_since_upload < 1:
        hours_since_upload = 1

    velocity = views / hours_since_upload
    return views, round(hours_since_upload, 2), int(velocity)


def get_duration_seconds(video: dict):
    duration_str = video.get("contentDetails", {}).get("duration", "PT0S")
    return int(isodate.parse_duration(duration_str).total_seconds())


def search_videos(youtube, query: str, max_results: int = 25):
    search_response = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        order="date",
        maxResults=max_results
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

    if not video_ids:
        return []

    video_response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    ).execute()

    return video_response.get("items", [])


def get_channel_id_from_handle(youtube, handle: str):
    clean_handle = handle.replace("@", "")
    response = youtube.search().list(
        q=clean_handle,
        part="snippet",
        type="channel",
        maxResults=5
    ).execute()

    for item in response.get("items", []):
        title = item["snippet"]["title"].lower()
        custom = item["snippet"].get("customUrl", "").lower()
        if clean_handle.lower() in custom or clean_handle.lower() in title:
            return item["snippet"]["channelId"]

    if response.get("items"):
        return response["items"][0]["snippet"]["channelId"]

    return None


def get_recent_videos_from_channel(youtube, channel_id: str, max_results: int = 10):
    search_response = youtube.search().list(
        channelId=channel_id,
        part="snippet",
        type="video",
        order="date",
        maxResults=max_results
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

    if not video_ids:
        return []

    video_response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    ).execute()

    return video_response.get("items", [])


def filter_long_videos(videos, min_seconds: int = 70):
    filtered = []
    for video in videos:
        duration_seconds = get_duration_seconds(video)
        if duration_seconds > min_seconds:
            filtered.append(video)
    return filtered


def scan_keyword(youtube, keyword: str, max_results: int = 25):
    videos = search_videos(youtube, keyword, max_results=max_results)
    videos = filter_long_videos(videos)

    rows = []
    for video in videos:
        title = video["snippet"]["title"]
        channel = video["snippet"]["channelTitle"]
        video_id = video["id"]
        link = f"https://www.youtube.com/watch?v={video_id}"

        views, hours_since_upload, velocity = calculate_velocity(video)

        rows.append({
            "source_type": "keyword",
            "competitor": "",
            "keyword": keyword,
            "title": title,
            "channel": channel,
            "views": views,
            "hours_since_upload": hours_since_upload,
            "velocity": velocity,
            "link": link,
        })

    return sorted(rows, key=lambda x: x["velocity"], reverse=True)


def scan_competitors(youtube, max_results_per_channel: int = 8):
    all_rows = []

    for competitor in COMPETITOR_CHANNELS:
        handle = competitor["handle"]
        name = competitor["name"]

        channel_id = get_channel_id_from_handle(youtube, handle)
        if not channel_id:
            continue

        videos = get_recent_videos_from_channel(youtube, channel_id, max_results=max_results_per_channel)
        videos = filter_long_videos(videos)

        for video in videos:
            title = video["snippet"]["title"]
            channel = video["snippet"]["channelTitle"]
            video_id = video["id"]
            link = f"https://www.youtube.com/watch?v={video_id}"

            views, hours_since_upload, velocity = calculate_velocity(video)

            all_rows.append({
                "source_type": "competitor",
                "competitor": name,
                "keyword": "",
                "title": title,
                "channel": channel,
                "views": views,
                "hours_since_upload": hours_since_upload,
                "velocity": velocity,
                "link": link,
            })

    return sorted(all_rows, key=lambda x: x["velocity"], reverse=True)
