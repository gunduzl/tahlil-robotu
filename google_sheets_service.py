"""Google Sheets'ten tahlil verisi cekme yardimcilari."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from lab_parser import parse_lab_dataframe

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

GOOGLE_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_service_account_file() -> Path | None:
    """Servis hesabi json dosya yolunu dondurur."""
    value = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def extract_gid_from_url(sheet_url: str) -> str | None:
    """URL icinden gid degerini alir."""
    if "#gid=" in sheet_url:
        return sheet_url.split("#gid=")[-1].split("&")[0]

    parsed = urlparse(sheet_url)
    query = parse_qs(parsed.query)
    gid_values = query.get("gid")
    return gid_values[0] if gid_values else None


def build_google_csv_export_url(sheet_url: str, gid: str | None = None) -> str:
    """Google Sheet URL'sini csv export URL'sine cevirir."""
    gid_value = gid or extract_gid_from_url(sheet_url) or "0"
    base_match = re.search(r"(https://docs\.google\.com/spreadsheets/d/[^/]+)", sheet_url)
    if not base_match:
        raise ValueError("Gecersiz Google Sheets URL'si.")
    return f"{base_match.group(1)}/export?format=csv&gid={gid_value}"


def load_public_sheet_dataframe(sheet_url: str, gid: str | None = None) -> pd.DataFrame:
    """Yayinlanmis veya paylasilabilir Google Sheet'i csv olarak okur."""
    csv_url = build_google_csv_export_url(sheet_url, gid=gid)
    return pd.read_csv(csv_url)


def get_gspread_client() -> gspread.Client:
    """Servis hesabi ile gspread istemcisi olusturur."""
    service_account_file = get_service_account_file()
    if not service_account_file or not service_account_file.exists():
        raise ValueError(
            "Google Sheets servis hesabi bulunamadi. .env icine GOOGLE_SERVICE_ACCOUNT_FILE ekleyin."
        )

    credentials = Credentials.from_service_account_file(
        str(service_account_file),
        scopes=GOOGLE_SHEETS_SCOPES,
    )
    return gspread.authorize(credentials)


def load_private_sheet_dataframe(sheet_url: str, worksheet_name: str | None = None) -> pd.DataFrame:
    """Servis hesabi ile paylasilmis Google Sheet'i okur."""
    client = get_gspread_client()
    spreadsheet = client.open_by_url(sheet_url)
    worksheet = spreadsheet.worksheet(worksheet_name) if worksheet_name else spreadsheet.sheet1
    values = worksheet.get_all_records()
    return pd.DataFrame(values)


def load_google_sheet_lab_data(
    sheet_url: str,
    worksheet_name: str | None = None,
    gid: str | None = None,
    access_mode: str = "public",
) -> pd.DataFrame:
    """Google Sheets'ten gelen veriyi standart tahlil formatina cevirir."""
    if access_mode == "service_account":
        raw_df = load_private_sheet_dataframe(sheet_url, worksheet_name=worksheet_name)
        source_name = "Google Sheets (Service Account)"
    else:
        raw_df = load_public_sheet_dataframe(sheet_url, gid=gid)
        source_name = "Google Sheets"

    return parse_lab_dataframe(raw_df, source=source_name)
