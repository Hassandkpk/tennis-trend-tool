import streamlit as st

from competitors import EALA_COMPETITOR_CHANNELS, ALCARAZ_COMPETITOR_CHANNELS
from scanner import get_youtube_client, scan_keyword, scan_competitors
from sheet_writer import append_topic_row, write_test_row

st.set_page_config(page_title="Pipeline Tester", page_icon="🧪", layout="wide")

st.title("🧪 Tennis Topic Radar")
st.write("Scan Alex Eala or Carlos Alcaraz topics from keywords and competitor channels.")

API_KEY = st.secrets.get("YOUTUBE_API_KEY", None)

if not API_KEY:
    st.error("Missing YOUTUBE_API_KEY in Streamlit secrets.")
    st.stop()

youtube = get_youtube_client(API_KEY)


PLAYER_CONFIG = {
    "Alex Eala": {
        "keywords": ["Alex Eala"],
        "competitors": EALA_COMPETITOR_CHANNELS,
        "sheet_tab": "Topics",
        "player_name": "Alex Eala",
    },
    "Carlos Alcaraz": {
        "keywords": ["Carlos Alcaraz", "Alcaraz"],
        "competitors": ALCARAZ_COMPETITOR_CHANNELS,
        "sheet_tab": "Alcaraz Topics",
        "player_name": "Carlos Alcaraz",
    },
}


def filter_titles(results):
    filtered = []

    for r in results:
        title = r.get("title", "").lower()

        if " vs " in title:
            continue
        if " vs." in title:
            continue
        if "vs " in title:
            continue
        if " vs" in title:
            continue

        filtered.append(r)

    return filtered


selected_player = st.selectbox(
    "Choose topic radar",
    ["Alex Eala", "Carlos Alcaraz"]
)

config = PLAYER_CONFIG[selected_player]
KEYWORDS_TO_SCAN = config["keywords"]
COMPETITOR_CHANNELS = config["competitors"]
SHEET_NAME = "Tennis Sheet"
SHEET_TAB = config["sheet_tab"]
PLAYER_NAME = config["player_name"]


st.subheader("Pipeline Scanner")

if st.button("Run Test Pipeline"):
    all_results = []

    st.subheader("Keyword Results")
    for keyword in KEYWORDS_TO_SCAN:
        keyword_results = scan_keyword(youtube, keyword, max_results=25, max_hours=72)
        keyword_results = filter_titles(keyword_results)

        top_keyword_results = keyword_results[:5]
        all_results.extend(top_keyword_results)

        if top_keyword_results:
            st.write(f"Top results for: {keyword}")
            st.dataframe(top_keyword_results, use_container_width=True)

    st.subheader("Competitor Results")
    competitor_results = scan_competitors(
        youtube,
        COMPETITOR_CHANNELS,
        max_results_per_channel=8,
        max_hours=72
    )
    competitor_results = filter_titles(competitor_results)

    top_competitor_results = competitor_results[:10]
    all_results.extend(top_competitor_results)

    if top_competitor_results:
        st.dataframe(top_competitor_results, use_container_width=True)

    st.subheader("Top Combined Results")
    all_results = sorted(all_results, key=lambda x: x["velocity"], reverse=True)
    st.dataframe(all_results[:10], use_container_width=True)


st.subheader("Google Sheets Test")

if st.button("Write Simple Test Row"):
    try:
        write_test_row(SHEET_NAME, SHEET_TAB)
        st.success(f"Simple test row written to Google Sheet tab: {SHEET_TAB}")
    except Exception as e:
        st.error(f"Failed to write test row: {e}")


st.subheader("Write Real Topics to Sheet")

if st.button("Write Top 10 Highest Velocity Topics"):
    try:
        all_results = []

        for keyword in KEYWORDS_TO_SCAN:
            keyword_results = scan_keyword(youtube, keyword, max_results=25, max_hours=72)
            keyword_results = filter_titles(keyword_results)
            all_results.extend(keyword_results[:10])

        competitor_results = scan_competitors(
            youtube,
            COMPETITOR_CHANNELS,
            max_results_per_channel=8,
            max_hours=72
        )
        competitor_results = filter_titles(competitor_results)
        all_results.extend(competitor_results[:15])

        all_results = sorted(all_results, key=lambda x: x["velocity"], reverse=True)

        if not all_results:
            st.warning("No topics found.")
        else:
            top_topics = all_results[:10]
            written_count = 0

            for topic in top_topics:
                topic_data = {
                    "source": topic.get("source_type", ""),
                    "keyword": topic.get("keyword", ""),
                    "player": PLAYER_NAME,
                    "title": topic.get("title", ""),
                    "channel": topic.get("channel", ""),
                    "views": topic.get("views", ""),
                    "velocity": topic.get("velocity", ""),
                    "subscribers": topic.get("subscribers", ""),
                    "url": topic.get("link", ""),
                }

                append_topic_row(SHEET_NAME, topic_data, SHEET_TAB)
                written_count += 1

            st.success(f"{written_count} highest velocity topics written to {SHEET_TAB} successfully.")
            st.dataframe(top_topics, use_container_width=True)

    except Exception as e:
        st.error(f"Failed to write top topics: {e}")
