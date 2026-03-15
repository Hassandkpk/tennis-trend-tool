import streamlit as st

from scanner import get_youtube_client, scan_keyword, scan_competitors
from sheet_writer import append_topic_row, write_test_row

st.set_page_config(page_title="Pipeline Tester", page_icon="🧪", layout="wide")

st.title("🧪 Daily Pipeline Tester")
st.write("Run the keyword scan and competitor scan manually before full automation.")

API_KEY = st.secrets.get("YOUTUBE_API_KEY", None)

if not API_KEY:
    st.error("Missing YOUTUBE_API_KEY in Streamlit secrets.")
    st.stop()

youtube = get_youtube_client(API_KEY)

KEYWORDS_TO_SCAN = [
    "Alex Eala",
]

st.subheader("Pipeline Scanner")

if st.button("Run Test Pipeline"):
    all_results = []

    st.subheader("Keyword Results")
    for keyword in KEYWORDS_TO_SCAN:
        keyword_results = scan_keyword(youtube, keyword, max_results=25)
        top_keyword_results = keyword_results[:5]
        all_results.extend(top_keyword_results)

        if top_keyword_results:
            st.write(f"Top results for: {keyword}")
            st.dataframe(top_keyword_results, use_container_width=True)

    st.subheader("Competitor Results")
    competitor_results = scan_competitors(youtube, max_results_per_channel=8)
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
        write_test_row("Tennis Sheet", "Topics")
        st.success("Simple test row written to Google Sheet successfully.")
    except Exception as e:
        st.error(f"Failed to write test row: {e}")

st.subheader("Write Real Topics to Sheet")

if st.button("Write Top 10 Highest Velocity Topics"):
    try:
        all_results = []

        for keyword in KEYWORDS_TO_SCAN:
            keyword_results = scan_keyword(youtube, keyword, max_results=25)
            all_results.extend(keyword_results[:10])

        competitor_results = scan_competitors(youtube, max_results_per_channel=8)
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
                    "player": "Alex Eala",
                    "title": topic.get("title", ""),
                    "channel": topic.get("channel", ""),
                    "views": topic.get("views", ""),
                    "velocity": topic.get("velocity", ""),
                    "subscribers": "",
                    "url": topic.get("link", ""),
                }

                append_topic_row("Tennis Sheet", topic_data, "Topics")
                written_count += 1

            st.success(f"{written_count} highest velocity topics written to Google Sheet successfully.")
            st.dataframe(top_topics, use_container_width=True)

    except Exception as e:
        st.error(f"Failed to write top topics: {e}")
