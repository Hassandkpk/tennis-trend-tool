from datetime import datetime

def run_daily_pipeline():
    print("Daily pipeline started")
    print("Current time:", datetime.now())
    print("Step 1: Scan topics")
    print("Step 2: Write top topics to Google Sheet")
    print("Step 3: Rewrite titles with Claude")
    print("Step 4: Save 4 title variations back to sheet")
    print("Pipeline finished")


if __name__ == "__main__":
    run_daily_pipeline()
