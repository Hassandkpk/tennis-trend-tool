import os
from datetime import datetime

from scanner import get_youtube_client, scan_keyword, scan_competitors


KEYWORDS_TO_SCAN = [
    "Alex Eala",
]


def run_daily_pipeline():
    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        raise ValueError("Missing YOUTUBE_API_KEY environment variable")

    youtube = get_youtube_client(api_key)

    print("Daily pipeline started")
    print("Current time:", datetime.now())
    print("-" * 50)

    all_results = []

    for keyword in KEYWORDS_TO_SCAN:
        print(f"Scanning keyword: {keyword}")
        keyword_results = scan_keyword(youtube, keyword, max_results=25)
        top_keyword_results = keyword_results[:5]
        all_results.extend(top_keyword_results)

        for row in top_keyword_results:
            print(f"[KEYWORD] {row['title']} | Velocity: {row['velocity']}")

    print("-" * 50)
    print("Scanning competitors...")
    competitor_results = scan_competitors(youtube, max_results_per_channel=8)
    top_competitor_results = competitor_results[:10]
    all_results.extend(top_competitor_results)

    for row in top_competitor_results:
        print(f"[COMPETITOR] {row['title']} | Velocity: {row['velocity']}")

    print("-" * 50)

    all_results = sorted(all_results, key=lambda x: x["velocity"], reverse=True)

    print("Top combined results:")
    for row in all_results[:10]:
        print(f"{row['title']} | Source: {row['source_type']} | Velocity: {row['velocity']}")

    print("Pipeline finished")


if __name__ == "__main__":
    run_daily_pipeline()
