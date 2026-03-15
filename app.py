import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timezone
import isodate

from competitors import COMPETITOR_CHANNELS

st.set_page_config(page_title="Tennis Trend Tool", page_icon="🎾", layout="wide")

st.title("🎾 Tennis Trend Tool")
st.write("Track fast-growing tennis videos by keyword and competitor channels.")

API_KEY = st.secrets.get("YOUTUBE_API_KEY", None)

if not API_KEY:
    st.error("YouTube API key not found. Add it in Streamlit secrets.")
    st.stop()

youtube = build("youtube", "v3", developerKey=API_KEY)


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


def search_videos(query: str, max_results: int = 25):
    search_response = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        order="date",
        maxResults=max_results
    ).execute()

    video_ids = []
    for item in search_response.get("items", []):
        video_ids.append(item["id"]["videoId"])

    if not video_ids:
        return []

    video_response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    ).execute()

    return video_response.get("items", [])


def get_channel_id_from_handle(handle: str):
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


def get_recent_videos_from_channel(channel_id: str, max_results: int = 10):
    search_response = youtube.search().list(
        channelId=channel_id,
        part="snippet",
        type="video",
        order="date",
        maxResults=max_results
    ).execute()

    video_ids = []
    for item in search_response.get("items", []):
        video_ids.append(item["id"]["videoId"])

    if not video_ids:
        return []

    video_response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    ).execute()

    return video_response.get("items", [])


tab1, tab2 = st.tabs(["Keyword Scanner", "Competitor Scanner"])

with tab1:
    st.subheader("Keyword Scanner")
    keyword = st.text_input("Enter player name or tennis topic", value="Alex Eala")
    max_results = st.slider("Number of videos to analyze", min_value=10, max_value=50, value=25, step=5, key="kw_slider")

    if st.button("Find Viral Videos"):
        with st.spinner("Searching YouTube..."):
            videos = search_videos(keyword, max_results=max_results)

        if not videos:
            st.warning("No videos found.")
        else:
            rows = []

            for video in videos:
                duration_seconds = get_duration_seconds(video)

                if duration_seconds <= 60:
                    continue

                title = video["snippet"]["title"]
                channel = video["snippet"]["channelTitle"]
                video_id = video["id"]
                link = f"https://www.youtube.com/watch?v={video_id}"

                views, hours_since_upload, velocity = calculate_velocity(video)

                rows.append({
                    "Title": title,
                    "Channel": channel,
                    "Views": views,
                    "Hours Since Upload": hours_since_upload,
                    "Velocity": velocity,
                    "Link": link
                })

            if not rows:
                st.warning("No non-Shorts videos found.")
            else:
                df = pd.DataFrame(rows)
                df = df.sort_values(by="Velocity", ascending=False).reset_index(drop=True)

                st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        "Link": st.column_config.LinkColumn("Video Link")
                    }
                )

with tab2:
    st.subheader("Competitor Scanner")
    st.write("Scanning saved competitor channels.")

    if st.button("Scan Competitor Channels"):
        all_rows = []

        with st.spinner("Checking competitors..."):
            for competitor in COMPETITOR_CHANNELS:
                handle = competitor["handle"]
                name = competitor["name"]

                channel_id = get_channel_id_from_handle(handle)

                if not channel_id:
                    continue

                videos = get_recent_videos_from_channel(channel_id, max_results=8)

                for video in videos:
                    duration_seconds = get_duration_seconds(video)

                    if duration_seconds <= 60:
                        continue

                    title = video["snippet"]["title"]
                    channel = video["snippet"]["channelTitle"]
                    video_id = video["id"]
                    link = f"https://www.youtube.com/watch?v={video_id}"

                    views, hours_since_upload, velocity = calculate_velocity(video)

                    all_rows.append({
                        "Competitor": name,
                        "Title": title,
                        "Channel": channel,
                        "Views": views,
                        "Hours Since Upload": hours_since_upload,
                        "Velocity": velocity,
                        "Link": link
                    })

        if not all_rows:
            st.warning("No competitor videos found.")
        else:
            df = pd.DataFrame(all_rows)
            df = df.sort_values(by="Velocity", ascending=False).reset_index(drop=True)

            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Link": st.column_config.LinkColumn("Video Link")
                }
            )
