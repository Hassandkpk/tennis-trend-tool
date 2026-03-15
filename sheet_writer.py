import json
from datetime import datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_gspread_client():
    service_account_info = json.loads(
        st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    )

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )

    return gspread.authorize(credentials)


def append_test_row(sheet_name: str, worksheet_name: str = "Daily Topics"):
    client = get_gspread_client()
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(worksheet_name)

    test_row = [
        datetime.now().strftime("%Y-%m-%d"),
        "test",
        "",
        "Alex Eala",
        "TEST TITLE",
        "Test Channel",
        12345,
        4.2,
        2939,
        "https://www.youtube.com/watch?v=test",
        "",
        "",
        "",
        "",
        "",
        "test row"
    ]

    worksheet.append_row(test_row, value_input_option="USER_ENTERED")
