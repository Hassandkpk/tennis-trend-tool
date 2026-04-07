from datetime import datetime, timezone
import isodate
from googleapiclient.discovery import build


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

    # Primary: use forHandle — the correct API param for @handle lookups
    try:
        response = youtube.channels().list(
            part="id,snippet",
            forHandle=clean_handle
        ).execute()

        items = response.get("items", [])
        if items:
            return items[0]["id"]
    except Exception:
        pass

    # Fallback: search-based resolution
    try:
        response = youtube.search().list(
            q=clean_handle,
            part="snippet",
            type="channel",
            maxResults=5
        ).execute()

        for item in response.get("items", []):
            custom = item["snippet"].get("customUrl", "").lower()
            if clean_handle.lower() in custom:
                return item["snippet"]["channelId"]

        if response.get("items"):
            return response["items"][0]["snippet"]["channelId"]
    except Exception:
        pass

    return None


def get_uploads_playlist_id(youtube, channel_id: str):
    response = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    ).execute()

    items = response.get("items", [])
    if not items:
        return None

    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_recent_videos_from_channel(youtube, channel_id: str, max_results: int = 10):
    uploads_playlist_id = get_uploads_playlist_id(youtube, channel_id)
    if not uploads_playlist_id:
        return []

    playlist_response = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist_id,
        maxResults=max_results
    ).execute()

    video_ids = []
    for item in playlist_response.get("items", []):
        resource = item.get("snippet", {}).get("resourceId", {})
        if resource.get("kind") == "youtube#video":
            video_ids.append(resource.get("videoId"))

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


def get_subscriber_counts(youtube, channel_ids):
    if not channel_ids:
        return {}

    unique_ids = list(set(channel_ids))
    subscriber_map = {}

    chunk_size = 50
    for i in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[i:i + chunk_size]

        response = youtube.channels().list(
            part="statistics,snippet",
            id=",".join(chunk),
            maxResults=len(chunk)
        ).execute()

        for item in response.get("items", []):
            cid = item["id"]
            subs = int(item.get("statistics", {}).get("subscriberCount", 0))
            title = item.get("snippet", {}).get("title", "")
            subscriber_map[cid] = {
                "subscribers": subs,
                "channel_title": title
            }

    return subscriber_map


def scan_keyword(youtube, keyword: str, max_results: int = 25):
    videos = search_videos(youtube, keyword, max_results=max_results)
    videos = filter_long_videos(videos)

    channel_ids = [video["snippet"]["channelId"] for video in videos]
    subscriber_map = get_subscriber_counts(youtube, channel_ids)

    rows = []
    for video in videos:
        title = video["snippet"]["title"]
        channel = video["snippet"]["channelTitle"]
        channel_id = video["snippet"]["channelId"]
        video_id = video["id"]
        link = f"https://www.youtube.com/watch?v={video_id}"

        views, hours_since_upload, velocity = calculate_velocity(video)
        subscribers = subscriber_map.get(channel_id, {}).get("subscribers", 0)

        rows.append({
            "source_type": "keyword",
            "competitor": "",
            "keyword": keyword,
            "title": title,
            "channel": channel,
            "channel_id": channel_id,
            "views": views,
            "hours_since_upload": hours_since_upload,
            "velocity": velocity,
            "subscribers": subscribers,
            "link": link,
        })

    return sorted(rows, key=lambda x: x["velocity"], reverse=True)


def scan_competitors(youtube, competitor_channels, max_results_per_channel: int = 8):
    all_rows = []

    for competitor in competitor_channels:
        name = competitor.get("name", "")

        if "channel_id" in competitor:
            channel_id = competitor["channel_id"]
        else:
            handle = competitor["handle"]
            channel_id = get_channel_id_from_handle(youtube, handle)

        if not channel_id:
            continue

        videos = get_recent_videos_from_channel(youtube, channel_id, max_results=max_results_per_channel)
        videos = filter_long_videos(videos)

        subscriber_map = get_subscriber_counts(youtube, [channel_id])
        channel_subscribers = subscriber_map.get(channel_id, {}).get("subscribers", 0)

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
                "channel_id": channel_id,
                "views": views,
                "hours_since_upload": hours_since_upload,
                "velocity": velocity,
                "subscribers": channel_subscribers,
                "link": link,
            })

    return sorted(all_rows, key=lambda x: x["velocity"], reverse=True)
