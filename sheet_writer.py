from datetime import datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_gspread_client():
    """
    Authenticate with Google using Streamlit secrets
    """
    service_account_info = dict(st.secrets["gcp_service_account"])

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )

    return gspread.authorize(credentials)


def append_topic_row(sheet_name, topic_data, worksheet_name="Daily Topics"):
    """
    Write a topic row into the Google Sheet
    """

    client = get_gspread_client()
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(worksheet_name)

    row = [
        topic_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        topic_data.get("source", ""),
        topic_data.get("keyword", ""),
        topic_data.get("player", ""),
        topic_data.get("title", ""),
        topic_data.get("channel", ""),
        topic_data.get("views", ""),
        topic_data.get("velocity", ""),
        topic_data.get("subscribers", ""),
        topic_data.get("url", ""),
        "",  # Claude title variation 1
        "",  # Claude title variation 2
        "",  # Claude title variation 3
        "",  # Claude title variation 4
        "",  # chosen title
        "new"  # status
    ]

    worksheet.append_row(row, value_input_option="USER_ENTERED")


def write_test_row(sheet_name="Tennis Outlier Tracker", worksheet_name="Daily Topics"):
    """
    Simple test function to confirm sheet writing works
    """

    topic = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": "test",
        "keyword": "alex eala",
        "player": "Alex Eala",
        "title": "TEST TITLE",
        "channel": "Test Channel",
        "views": 12345,
        "velocity": 4.2,
        "subscribers": 2939,
        "url": "https://youtube.com"
    }

    append_topic_row(sheet_name, topic, worksheet_name)
