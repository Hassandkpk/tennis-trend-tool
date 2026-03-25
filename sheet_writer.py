from datetime import datetime
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_gspread_client():
    service_account_info = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )
    return gspread.authorize(credentials)


def append_topic_row(sheet_name, topic_data, worksheet_name="Daily Topics"):
    """
    Matches sheet columns exactly:
    Date | Source | Type | Competitor | Keyword | Original Title | Generated Title | Channel | Views | Hours Since Upload | Velocity | Link | Variant 1 | Variant 2 | Variant 3 | Variant 4 | Picked? | Notes
    """
    client = get_gspread_client()
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(worksheet_name)

    row = [
        topic_data.get("date", datetime.now().strftime("%Y-%m-%d")),  # Date
        topic_data.get("source", ""),                                  # Source
        topic_data.get("type", "outlier"),                             # Type
        topic_data.get("channel", ""),                                 # Competitor/Channel
        topic_data.get("keyword", ""),                                 # Keyword
        topic_data.get("title", ""),                                   # Original Title
        topic_data.get("generated_title", ""),                         # Generated Title (Claude)
        topic_data.get("channel", ""),                                 # Channel
        topic_data.get("views", ""),                                   # Views
        topic_data.get("hours_since_upload", ""),                      # Hours Since Upload
        topic_data.get("velocity", ""),                                # Velocity
        topic_data.get("url", ""),                                     # Link
        "",                                                            # Variant 1
        "",                                                            # Variant 2
        "",                                                            # Variant 3
        "",                                                            # Variant 4
        "",                                                            # Picked?
        "",                                                            # Notes
    ]

    worksheet.append_row(row, value_input_option="USER_ENTERED")


def write_test_row(sheet_name="Tennis Sheet", worksheet_name="Topics"):
    topic = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": "test",
        "type": "outlier",
        "keyword": "alex eala",
        "title": "TEST TITLE",
        "generated_title": "",
        "channel": "Test Channel",
        "views": 12345,
        "hours_since_upload": 24,
        "velocity": 4.2,
        "url": "https://youtube.com",
    }
    append_topic_row(sheet_name, topic, worksheet_name)
