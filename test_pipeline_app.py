import os
import streamlit as st
from sheet_writer import append_test_row
from scanner import get_youtube_client, scan_keyword, scan_competitors

st.set_page_config(page_title="Pipeline Tester", page_icon="🧪", layout="wide")

st.title("🧪 Daily Pipeline Tester")
st.write("Run the keyword scan and competitor scan manually before connecting Google Sheets.")

API_KEY = st.secrets.get("YOUTUBE_API_KEY", None)

if not API_KEY:
    st.error("Missing YOUTUBE_API_KEY in Streamlit secrets.")
    st.stop()

youtube = get_youtube_client(API_KEY)

KEYWORDS_TO_SCAN = [
    "Alex Eala",
]

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

if st.button("Write Test Row to Sheet"):
    try:
        append_test_row("Tennis Outlier Tracker", "Daily Topics")
        st.success("Test row written to Google Sheet successfully.")
    except Exception as e:
        st.error(f"Failed to write test row: {e}")
