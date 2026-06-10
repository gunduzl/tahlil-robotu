"""Streamlit arayuzu icin tekrar kullanilan yardimci bilesenler."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def inject_global_styles() -> None:
    """Daha kompakt ve modern bir gorunum icin CSS uygular."""
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(20, 184, 166, 0.08), transparent 26%),
                    linear-gradient(180deg, #f7f9fc 0%, #eef3f7 100%);
            }
            .block-container {
                max-width: 1160px;
                padding-top: 1rem;
                padding-bottom: 2rem;
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0f172a 0%, #134e4a 100%);
            }
            [data-testid="stSidebar"] * {
                color: #f8fafc;
            }
            [data-testid="stSegmentedControl"] {
                background: transparent;
                margin: 0.15rem 0 1.1rem 0;
            }
            [data-testid="stSegmentedControl"] > div {
                display: grid !important;
                grid-template-columns: repeat(5, minmax(0, 1fr));
                gap: 1rem;
                background: transparent !important;
                border: none !important;
                padding: 0 !important;
                box-shadow: none !important;
            }
            [data-testid="stSegmentedControl"] label {
                background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%) !important;
                border: 1px solid rgba(203, 213, 225, 0.55) !important;
                border-radius: 999px !important;
                min-height: 62px;
                padding: 0.05rem 0.25rem !important;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
                transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
            }
            [data-testid="stSegmentedControl"] label:hover {
                transform: translateY(-1px);
                box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
            }
            [data-testid="stSegmentedControl"] label p {
                color: #516178 !important;
                font-size: 0.95rem !important;
                font-weight: 500 !important;
            }
            [data-testid="stSegmentedControl"] label:has(input:checked) {
                background: linear-gradient(135deg, #14908d 0%, #19a5a5 100%) !important;
                border-color: transparent !important;
                box-shadow: 0 18px 34px rgba(20, 144, 141, 0.28);
            }
            [data-testid="stSegmentedControl"] label:has(input:checked) p {
                color: #ffffff !important;
                font-weight: 700 !important;
            }
            .soft-card {
                background: rgba(255,255,255,0.86);
                border: 1px solid rgba(15,23,42,0.08);
                border-radius: 24px;
                padding: 1.05rem 1.15rem;
                box-shadow: 0 18px 40px rgba(15,23,42,0.08);
                backdrop-filter: blur(6px);
                margin-bottom: 1rem;
            }
            .hero-title {
                font-size: 2.1rem;
                font-weight: 800;
                color: #0f172a;
                margin-bottom: 0.2rem;
            }
            .hero-subtitle {
                color: #475569;
                margin-bottom: 0;
            }
            .metric-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 1rem;
                margin: 0.2rem 0 1.1rem 0;
            }
            .metric-chip {
                background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
                border: 1px solid rgba(203, 213, 225, 0.45);
                border-radius: 24px;
                padding: 1rem 1.2rem;
                min-height: 108px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            }
            .metric-chip small {
                display: block;
                color: #6b7a90;
                font-size: 0.76rem;
                margin-bottom: 0.6rem;
            }
            .metric-chip strong {
                color: #0f172a;
                font-size: 1.12rem;
                letter-spacing: 0.01em;
            }
            .report-box {
                background: linear-gradient(180deg, #ffffff 0%, #f7fffd 100%);
                border-left: 6px solid #0f766e;
                border-radius: 18px;
                padding: 1rem 1.1rem;
                box-shadow: 0 12px 30px rgba(15,23,42,0.08);
            }
            .section-note {
                color: #64748b;
                margin-top: -0.25rem;
                margin-bottom: 0.75rem;
            }
            @media (max-width: 900px) {
                [data-testid="stSegmentedControl"] > div {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
                .metric-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(selected_user: dict | None) -> None:
    """Sayfa basligi ve aktif kullanici ozetini gosterir."""
    if selected_user:
        st.markdown(
            f"""
            <div class="metric-grid">
                <div class="metric-chip"><small>Secili Kullanici</small><strong>{selected_user['name']}</strong></div>
                <div class="metric-chip"><small>Yas</small><strong>{selected_user['age']}</strong></div>
                <div class="metric-chip"><small>Cinsiyet</small><strong>{selected_user['gender']}</strong></div>
                <div class="metric-chip"><small>Durum</small><strong>Hazir</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="soft-card">
                <div class="hero-title">Tahlil Robotu</div>
                <p class="hero-subtitle">
                    Kullaniciyi secin, tahlili ekleyin ve DeepSeek destekli yorumu
                    daha akici bir adim akisi icinde inceleyin.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_stepper(current_page: str) -> str:
    """Ustte tiklanabilir adim navigasyonu gosterir."""
    page_labels = {
        "Kullanici Kaydi/Secimi": "Kullanici",
        "Tahlil Girisi": "Tahlil Girisi",
        "Sonuc Analizi ve Rapor": "Analiz",
        "DR. Yapay Zeka": "DR. Yapay Zeka",
        "Gecmis Tahliller": "Gecmis",
    }
    reverse_map = {label: page for page, label in page_labels.items()}
    current_label = page_labels.get(current_page, "Kullanici")
    selected_label = st.segmented_control(
        "Adimlar",
        options=list(page_labels.values()),
        selection_mode="single",
        default=current_label,
        label_visibility="collapsed",
    )
    return reverse_map.get(selected_label or current_label, current_page)


def render_report_box(report_markdown: str) -> None:
    """LLM raporunu vurgulu kutuda gosterir."""
    st.markdown('<div class="report-box">', unsafe_allow_html=True)
    st.markdown(report_markdown)
    st.markdown("</div>", unsafe_allow_html=True)


def style_results_dataframe(df: pd.DataFrame):
    """Duruma gore satir renklendirir."""
    def row_style(row: pd.Series) -> list[str]:
        status = row.get("Durum", "")
        if status == "Dusuk":
            return ["background-color: #fff1c2"] * len(row)
        if status == "Yuksek":
            return ["background-color: #ffd9dd"] * len(row)
        if status == "Bilinmiyor":
            return ["background-color: #eef2f7"] * len(row)
        return [""] * len(row)

    return df.style.apply(row_style, axis=1)
