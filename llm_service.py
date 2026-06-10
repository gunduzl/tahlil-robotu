"""DeepSeek LLM entegrasyonu."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# .env dosyasini calisma klasorunden bagimsiz olarak proje kokunden yukle.
load_dotenv(dotenv_path=ENV_PATH, override=True)

SYSTEM_PROMPT = """
Sen uzman bir saglik danismanisin. Kullanicinin referans araligi disinda cikan test
sonuclarini analiz edip tibbi tavsiyeler vermek, beslenme onerilerinde bulunmak ve
hangi durumlarda doktora gitmesi gerektigini soylemekle gorevlisin.

Kurallar:
- Sadece paylasilan anormal sonuclari yorumla.
- Yaniti Turkce ver.
- Kisa ama anlasilir basliklar kullan.
- Panik olusturma; dengeli ve ihtiyatli ol.
- Mutlaka su uyariyi ekle:
  "Bu bir yapay zeka tavsiyesidir, kesin teshis icin hekime basvurun."
""".strip()


def get_deepseek_api_key() -> str:
    """DeepSeek API anahtarini env, Streamlit Secrets veya session'dan okur."""
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if api_key:
        return api_key

    try:
        api_key = str(st.secrets.get("DEEPSEEK_API_KEY", "")).strip()
        if api_key:
            return api_key
    except Exception:
        pass

    return str(st.session_state.get("deepseek_api_key", "")).strip()


def get_deepseek_client() -> OpenAI:
    """DeepSeek icin OpenAI uyumlu istemciyi olusturur."""
    api_key = get_deepseek_api_key()
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY bulunamadi. Sol menuden API anahtarini girin veya "
            "Streamlit Cloud Secrets icinde tanimlayin."
        )

    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def build_abnormal_results_prompt(
    user: dict[str, Any], abnormal_results: list[dict[str, Any]]
) -> str:
    """Anormal sonuclari modele gonderilecek metne cevirir."""
    lines = [
        f"Kullanici: {user['name']}",
        f"Yas: {user['age']}",
        f"Cinsiyet: {user['gender']}",
        "",
        "Referans disi test sonuclari:",
    ]

    for result in abnormal_results:
        lines.append(
            "- {test_name}: {value} {unit} | Durum: {status} | Referans: {reference}".format(
                test_name=result["test_name"],
                value=result["test_value"],
                unit=result["unit"],
                status=result["status"],
                reference=result["reference_text"],
            )
        )

    lines.extend(
        [
            "",
            "Lutfen her sonuc icin:",
            "1. Olasi anlamini acikla.",
            "2. Beslenme/yasam tarzi onerisi ver.",
            "3. Hangi belirtilerde doktora gidilmesi gerektigini yaz.",
            "4. Sonda genel bir uyari ekle.",
        ]
    )
    return "\n".join(lines)


def generate_medical_comment(
    user: dict[str, Any], abnormal_results: list[dict[str, Any]]
) -> str:
    """DeepSeek uzerinden yorum uretir."""
    if not abnormal_results:
        return (
            "Tum sonuclar referans araliginda gorunuyor. "
            "Bu nedenle DeepSeek'e gonderilecek referans disi bir sonuc bulunmadi."
        )

    client = get_deepseek_client()
    prompt = build_abnormal_results_prompt(user=user, abnormal_results=abnormal_results)

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content or "Yorum uretilemedi."
