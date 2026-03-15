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
        write_test_row("Tennis Outlier Tracker", "Daily Topics")
        st.success("Simple test row written to Google Sheet successfully.")
    except Exception as e:
        st.error(f"Failed to write test row: {e}")

st.subheader("Write Real Top Topic to Sheet")

if st.button("Write Highest Velocity Topic"):
    try:
        all_results = []

        for keyword in KEYWORDS_TO_SCAN:
            keyword_results = scan_keyword(youtube, keyword, max_results=25)
            all_results.extend(keyword_results[:5])

        competitor_results = scan_competitors(youtube, max_results_per_channel=8)
        all_results.extend(competitor_results[:10])

        all_results = sorted(all_results, key=lambda x: x["velocity"], reverse=True)

        if not all_results:
            st.warning("No topics found.")
        else:
            top_topic = all_results[0]

            topic_data = {
                "source": top_topic.get("source_type", ""),
                "keyword": top_topic.get("keyword", ""),
                "player": "Alex Eala",
                "title": top_topic.get("title", ""),
                "channel": top_topic.get("channel", ""),
                "views": top_topic.get("views", ""),
                "velocity": top_topic.get("velocity", ""),
                "subscribers": "",
                "url": top_topic.get("link", ""),
            }

            append_topic_row("Tennis Outlier Tracker", topic_data, "Daily Topics")
            st.success("Highest velocity topic written to Google Sheet successfully.")
            st.write(topic_data)

    except Exception as e:
        st.error(f"Failed to write highest velocity topic: {e}")
