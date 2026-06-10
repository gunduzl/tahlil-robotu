"""PDF ve Excel laboratuvar dosyalarini ayrisma yardimcilari."""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any

import pandas as pd
import pdfplumber
from pypdf import PdfReader

from reference_engine import (
    evaluate_against_reference_text,
    get_test_unit,
    normalize_test_name,
)


DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})")


def normalize_whitespace(value: str) -> str:
    """Bosluklari temizler ve satir kirilimlarini sadeleştirir."""
    return re.sub(r"\s+", " ", value or "").strip()


def parse_float(value: Any) -> float | None:
    """Sayisal degeri float'a cevirir."""
    if value is None:
        return None

    cleaned = str(value).strip().replace(",", ".")
    cleaned = cleaned.replace("µ", "").replace(">", "").replace("<", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group())


def extract_patient_info_from_pdf(file_bytes: bytes) -> dict[str, Any]:
    """PDF ust bilgisinden temel hasta bilgilerini alir."""
    reader = PdfReader(BytesIO(file_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages[:1])

    name_match = re.search(r"Adı/Soyadı:\s*(.*?)\s+Cinsiyet:", text)
    gender_match = re.search(r"Cinsiyet:\s*(Kadın|Erkek|Kadin)", text)
    birth_match = re.search(r"Doğum Tarihi:\s*(\d{2}\.\d{2}\.\d{4})", text)

    return {
        "name": normalize_whitespace(name_match.group(1)) if name_match else "",
        "gender": (
            normalize_whitespace(gender_match.group(1)).replace("Kadın", "Kadin")
            if gender_match
            else ""
        ),
        "birth_date": birth_match.group(1) if birth_match else "",
    }


def parse_enabiz_pdf(file_bytes: bytes) -> pd.DataFrame:
    """e-Nabiz benzeri tahlil PDF'lerini satirlara ayirir."""
    rows: list[dict[str, Any]] = []
    current_date = ""
    pending_note = ""

    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for raw_row in table[1:]:
                    row = [normalize_whitespace(str(cell or "")) for cell in raw_row]
                    if not any(row):
                        continue

                    first_col = row[0]
                    test_name = row[1] if len(row) > 1 else ""
                    value_text = row[2] if len(row) > 2 else ""
                    unit = row[3] if len(row) > 3 else ""
                    reference_text = row[4] if len(row) > 4 else ""

                    if DATE_RE.search(first_col) and not test_name:
                        current_date = DATE_RE.search(first_col).group(1)
                        continue

                    if (
                        "Karar Sınır Değeri" in first_col
                        or "Karar Sinir Degeri" in first_col
                        or first_col.startswith("0 - ")
                    ) and rows:
                        pending_note = first_col.lstrip("- ").strip()
                        if not rows[-1]["reference_text"]:
                            rows[-1]["reference_text"] = pending_note
                            rows[-1]["status"] = evaluate_against_reference_text(
                                rows[-1]["test_value"], pending_note
                            )
                            rows[-1]["is_out_of_range"] = rows[-1]["status"] in {
                                "Dusuk",
                                "Yuksek",
                            }
                        continue

                    if not test_name or not value_text:
                        continue

                    normalized_name = normalize_test_name(test_name)
                    value = parse_float(value_text)
                    if value is None:
                        continue

                    final_reference = reference_text or pending_note
                    status = evaluate_against_reference_text(value, final_reference)
                    pending_note = ""

                    rows.append(
                        {
                            "test_date": current_date or "",
                            "test_name": normalized_name,
                            "test_value": value,
                            "unit": unit or get_test_unit(normalized_name),
                            "reference_text": final_reference,
                            "status": status,
                            "is_out_of_range": status in {"Dusuk", "Yuksek"},
                            "source": "PDF",
                        }
                    )

    return pd.DataFrame(rows)


def match_column(columns: list[str], candidates: list[str]) -> str | None:
    """Eslesen kolon adini bulur."""
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        for lower_name, original_name in lowered.items():
            if candidate in lower_name:
                return original_name
    return None


def parse_lab_dataframe(sheet_df: pd.DataFrame, source: str) -> pd.DataFrame:
    """DataFrame yapisindaki tahlil satirlarini standart sekle cevirir."""
    if sheet_df.empty:
        return pd.DataFrame(
            columns=[
                "test_date",
                "test_name",
                "test_value",
                "unit",
                "reference_text",
                "status",
                "is_out_of_range",
                "source",
            ]
        )

    columns = [str(col) for col in sheet_df.columns]
    test_col = match_column(columns, ["test", "tahlil", "analiz", "parametre"])
    value_col = match_column(columns, ["sonuc", "deger", "value"])
    unit_col = match_column(columns, ["birim", "unit"])
    ref_col = match_column(columns, ["referans", "reference"])
    date_col = match_column(columns, ["tarih", "date"])

    if not test_col or not value_col:
        return pd.DataFrame(
            columns=[
                "test_date",
                "test_name",
                "test_value",
                "unit",
                "reference_text",
                "status",
                "is_out_of_range",
                "source",
            ]
        )

    normalized = pd.DataFrame()
    normalized["test_name"] = sheet_df[test_col].astype(str).map(normalize_test_name)
    normalized["test_value"] = sheet_df[value_col].map(parse_float)
    normalized["unit"] = (
        sheet_df[unit_col].astype(str).fillna("")
        if unit_col
        else normalized["test_name"].map(get_test_unit)
    )
    normalized["reference_text"] = sheet_df[ref_col].astype(str).fillna("") if ref_col else ""
    normalized["test_date"] = (
        pd.to_datetime(sheet_df[date_col], errors="coerce").dt.strftime("%d.%m.%Y")
        if date_col
        else ""
    )
    normalized["source"] = source
    normalized = normalized.dropna(subset=["test_value"])
    normalized["status"] = normalized.apply(
        lambda row: evaluate_against_reference_text(
            float(row["test_value"]), str(row["reference_text"])
        ),
        axis=1,
    )
    normalized["is_out_of_range"] = normalized["status"].isin(["Dusuk", "Yuksek"])
    return normalized


def parse_excel_file(file_bytes: bytes) -> pd.DataFrame:
    """Excel dosyasindaki tahlil kayitlarini standart sekle cevirir."""
    excel_file = pd.ExcelFile(BytesIO(file_bytes))
    all_rows: list[pd.DataFrame] = []

    for sheet_name in excel_file.sheet_names:
        sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
        normalized = parse_lab_dataframe(sheet_df, source="Excel")
        if normalized.empty:
            continue
        all_rows.append(normalized)

    if not all_rows:
        return pd.DataFrame(
            columns=[
                "test_date",
                "test_name",
                "test_value",
                "unit",
                "reference_text",
                "status",
                "is_out_of_range",
                "source",
            ]
        )

    return pd.concat(all_rows, ignore_index=True)


def parse_uploaded_lab_file(file_name: str, file_bytes: bytes) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Uzantıya gore uygun parser'i calistirir."""
    extension = file_name.lower().rsplit(".", maxsplit=1)[-1]

    if extension == "pdf":
        df = parse_enabiz_pdf(file_bytes)
        patient_info = extract_patient_info_from_pdf(file_bytes)
        return df, patient_info

    if extension in {"xlsx", "xls"}:
        df = parse_excel_file(file_bytes)
        return df, {}

    raise ValueError("Desteklenmeyen dosya formati. PDF veya Excel yukleyin.")
