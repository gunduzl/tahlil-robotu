"""Streamlit tabanli kan tahlili takip uygulamasi."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from database import (
    create_test_result,
    create_user,
    delete_test_result,
    delete_user,
    get_test_results_by_user,
    get_user,
    get_users,
    init_db,
    update_user,
)
from google_sheets_service import load_google_sheet_lab_data
from lab_parser import parse_uploaded_lab_file
from llm_service import generate_medical_comment, get_deepseek_api_key
from reference_engine import evaluate_result, get_available_tests, get_test_unit
from ui_components import (
    inject_global_styles,
    render_hero,
    render_report_box,
    render_stepper,
    style_results_dataframe,
)

PAGES = [
    "Kullanici Kaydi/Secimi",
    "Tahlil Girisi",
    "Sonuc Analizi ve Rapor",
    "DR. Yapay Zeka",
    "Gecmis Tahliller",
]

st.set_page_config(page_title="Tahlil Robotu", page_icon=":bar_chart:", layout="wide")


def initialize_session() -> None:
    """Streamlit session state anahtarlarini hazirlar."""
    if "selected_user_id" not in st.session_state:
        st.session_state.selected_user_id = None
    if "llm_report" not in st.session_state:
        st.session_state.llm_report = ""
    if "uploaded_results_df" not in st.session_state:
        st.session_state.uploaded_results_df = pd.DataFrame()
    if "uploaded_file_name" not in st.session_state:
        st.session_state.uploaded_file_name = ""
    if "parsed_patient_info" not in st.session_state:
        st.session_state.parsed_patient_info = {}
    if "current_page" not in st.session_state:
        st.session_state.current_page = PAGES[0]


def go_to_page(page: str) -> None:
    """Aktif sayfayi degistirir."""
    st.session_state.current_page = page


def get_selected_user() -> dict | None:
    """Secili kullaniciyi dondurur."""
    user_id = st.session_state.get("selected_user_id")
    if not user_id:
        return None
    return get_user(user_id)


def make_results_dataframe(results: list[dict]) -> pd.DataFrame:
    """Tahlil kayitlarini DataFrame'e cevirir."""
    if not results:
        return pd.DataFrame(
            columns=[
                "id",
                "test_date",
                "test_name",
                "test_value",
                "unit",
                "status",
                "reference_text",
            ]
        )

    df = pd.DataFrame(results)
    return df[
        [
            "id",
            "test_date",
            "test_name",
            "test_value",
            "unit",
            "status",
            "reference_text",
        ]
    ].rename(
        columns={
            "id": "Kayit ID",
            "test_date": "Tarih",
            "test_name": "Test",
            "test_value": "Deger",
            "unit": "Birim",
            "status": "Durum",
            "reference_text": "Referans",
        }
    )


def get_result_dates(results: list[dict]) -> list[str]:
    """Kayitlarda bulunan tarihleri yeniden eskiye siralar."""
    return sorted(
        {str(result.get("test_date", "")) for result in results if result.get("test_date")},
        reverse=True,
    )


def render_results_by_date_tabs(results: list[dict], key_prefix: str) -> None:
    """Tahlil kayitlarini tarih bazli sekmelerde gosterir."""
    result_dates = get_result_dates(results)
    if not result_dates:
        st.info("Tarih bilgisi olan tahlil sonucu bulunmuyor.")
        return

    tab_labels = []
    for result_date in result_dates:
        date_results = [result for result in results if result["test_date"] == result_date]
        abnormal_count = sum(1 for result in date_results if result["is_out_of_range"])
        suffix = f" - {abnormal_count} referans disi" if abnormal_count else ""
        tab_labels.append(f"{result_date} ({len(date_results)}){suffix}")

    for result_date, tab in zip(result_dates, st.tabs(tab_labels)):
        with tab:
            date_results = [result for result in results if result["test_date"] == result_date]
            total_count = len(date_results)
            abnormal_count = sum(1 for result in date_results if result["is_out_of_range"])
            normal_count = total_count - abnormal_count

            metric_col1, metric_col2, metric_col3 = st.columns(3)
            metric_col1.metric("Bu Rapordaki Sonuc", total_count)
            metric_col2.metric("Referans Disi", abnormal_count)
            metric_col3.metric("Normal", normal_count)

            st.dataframe(
                style_results_dataframe(make_results_dataframe(date_results)),
                use_container_width=True,
                hide_index=True,
                key=f"{key_prefix}_{result_date}",
            )


def make_history_dataframe(results: list[dict]) -> pd.DataFrame:
    """Gecmis ve grafik ekranlari icin normalize edilmis DataFrame olusturur."""
    df = pd.DataFrame(results)
    if df.empty:
        return df

    df["test_date"] = pd.to_datetime(df["test_date"], errors="coerce")
    df["date_label"] = df["test_date"].dt.date.astype(str)
    df["test_value"] = pd.to_numeric(df["test_value"], errors="coerce")
    df["unit"] = df["unit"].fillna("").astype(str)
    df["test_label"] = df.apply(
        lambda row: f"{row['test_name']} ({row['unit']})" if row["unit"] else row["test_name"],
        axis=1,
    )
    return df.dropna(subset=["test_date", "test_value"])


def render_test_trend_chart(df: pd.DataFrame) -> None:
    """Secilen test icin gecmis deger trendini cizer."""
    if df.empty:
        st.info("Grafik icin kullanilabilir sayisal gecmis sonuc bulunmuyor.")
        return

    test_options = sorted(df["test_label"].unique())
    selected_test = st.selectbox("Trend icin test secin", options=test_options)
    selected_df = (
        df[df["test_label"] == selected_test]
        .sort_values(["test_date", "id"])
        .drop_duplicates(subset=["date_label"], keep="last")
    )

    chart_df = selected_df[["test_date", "test_value"]].rename(
        columns={"test_date": "Tarih", "test_value": "Deger"}
    )

    latest = selected_df.iloc[-1]
    previous = selected_df.iloc[-2] if len(selected_df) > 1 else None
    delta_value = None
    trend_text = "Karsilastirma icin en az iki farkli tarih gerekir."
    if previous is not None:
        delta_value = float(latest["test_value"]) - float(previous["test_value"])
        if delta_value > 0:
            trend_text = "Son kayitta onceki olcume gore artis var."
        elif delta_value < 0:
            trend_text = "Son kayitta onceki olcume gore azalis var."
        else:
            trend_text = "Son kayit onceki olcumle ayni seviyede."

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    unit_text = f" {latest['unit']}" if latest["unit"] else ""
    metric_col1.metric(
        "Son Deger",
        f"{latest['test_value']:g}{unit_text}",
        f"{delta_value:g}" if delta_value is not None else None,
    )
    metric_col2.metric("Olcum Sayisi", len(selected_df))
    metric_col3.metric("Son Tarih", str(latest["date_label"]))

    st.caption(trend_text)
    st.line_chart(chart_df, x="Tarih", y="Deger")

    st.dataframe(
        selected_df[
            [
                "date_label",
                "test_name",
                "test_value",
                "unit",
                "status",
                "reference_text",
            ]
        ].rename(
            columns={
                "date_label": "Tarih",
                "test_name": "Test",
                "test_value": "Deger",
                "unit": "Birim",
                "status": "Durum",
                "reference_text": "Referans",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_sidebar() -> str:
    """Sidebar'i bilgi paneli olarak kullanir."""
    st.sidebar.title("Tahlil Robotu")
    st.sidebar.caption("Gecis icin ustteki sekmeleri kullanin")

    if not get_deepseek_api_key():
        st.sidebar.text_input(
            "DeepSeek API Key",
            type="password",
            key="deepseek_api_key",
            placeholder="sk-...",
            help="Streamlit Secrets tanimli degilse bu oturum icin kullanilir.",
        )

    selected_user = get_selected_user()
    if selected_user:
        st.sidebar.markdown(
            f"**Secili Kullanici**\n\n{selected_user['name']}\n\n"
            f"Yas: {selected_user['age']}\n\nCinsiyet: {selected_user['gender']}"
        )
    else:
        st.sidebar.info("Baslamak icin bir kullanici secin veya yeni kullanici olusturun.")
    return st.session_state.get("current_page", PAGES[0])


def persist_uploaded_results(user: dict, upload_df: pd.DataFrame) -> int:
    """Yuklenen tahlil kayitlarini veritabanina yazar."""
    inserted_count = 0
    for _, row in upload_df.iterrows():
        raw_date = str(row.get("test_date", "")).strip()
        parsed_date = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
        iso_date = (
            parsed_date.date().isoformat()
            if not pd.isna(parsed_date)
            else date.today().isoformat()
        )
        create_test_result(
            user_id=user["id"],
            test_date=iso_date,
            test_name=str(row["test_name"]),
            test_value=float(row["test_value"]),
            unit=str(row.get("unit", "")),
            status=str(row.get("status", "Bilinmiyor")),
            reference_text=str(row.get("reference_text", "")),
            is_out_of_range=bool(row.get("is_out_of_range", False)),
        )
        inserted_count += 1
    return inserted_count


def render_import_preview(user: dict, parsed_df: pd.DataFrame, patient_info: dict | None = None) -> None:
    """Yuklenen kaynagin onizlemesini ve aksiyonlarini gosterir."""
    if patient_info:
        info_line = " | ".join(
            filter(
                None,
                [
                    f"Belgede Ad: {patient_info.get('name', '')}",
                    f"Cinsiyet: {patient_info.get('gender', '')}",
                    f"Dogum Tarihi: {patient_info.get('birth_date', '')}",
                ],
            )
        )
        if info_line:
            st.info(info_line)

    if parsed_df.empty:
        st.warning("Kaynak okundu ancak kaydedilebilir tahlil satiri bulunamadi.")
        return

    st.success(f"{len(parsed_df)} satir tahlil verisi algilandi.")
    preview_df = parsed_df.rename(
        columns={
            "test_date": "Tarih",
            "test_name": "Test",
            "test_value": "Deger",
            "unit": "Birim",
            "reference_text": "Referans",
            "status": "Durum",
            "source": "Kaynak",
        }
    )
    st.dataframe(
        style_results_dataframe(preview_df),
        use_container_width=True,
        hide_index=True,
    )

    button_col1, button_col2 = st.columns(2)
    with button_col1:
        save_clicked = st.button(
            "Kaydet ve Analize Gec",
            use_container_width=True,
            type="primary",
            key=f"save_{len(parsed_df)}_{str(preview_df.columns.tolist())}",
        )
    with button_col2:
        analyze_clicked = st.button(
            "Kaydet ve DR. Yapay Zeka ile Rapor Olustur",
            use_container_width=True,
            key=f"ai_{len(parsed_df)}_{str(preview_df.columns.tolist())}",
        )

    if save_clicked:
        persist_uploaded_results(user, parsed_df)
        go_to_page("Sonuc Analizi ve Rapor")
        st.rerun()

    if analyze_clicked:
        persist_uploaded_results(user, parsed_df)
        abnormal_results = parsed_df[parsed_df["is_out_of_range"]].to_dict("records")
        try:
            with st.spinner("DR. Yapay Zeka raporu uretiliyor..."):
                st.session_state.llm_report = generate_medical_comment(
                    user,
                    abnormal_results,
                )
            go_to_page("DR. Yapay Zeka")
            st.rerun()
        except Exception as exc:
            st.error(f"DR. Yapay Zeka yorumu alinamadi: {exc}")


def render_upload_panel(user: dict) -> None:
    """PDF, Excel veya Google Sheets yukleme alanini gosterir."""
    st.subheader("Tahlil Kaynagi Bagla")
    st.markdown(
        '<p class="section-note">PDF, Excel veya Google Sheets kaynagindan tahlil verisini iceri alin.</p>',
        unsafe_allow_html=True,
    )

    import_mode = st.radio(
        "Kaynak Turu",
        options=["Dosya Yukle", "Google Sheets Bagla"],
        horizontal=True,
    )

    if import_mode == "Dosya Yukle":
        uploaded_file = st.file_uploader(
            "Tahlil PDF veya Excel dosyasi",
            type=["pdf", "xlsx", "xls"],
            help="PDF, XLSX veya XLS formatlari desteklenir.",
        )

        if uploaded_file is None:
            return

        try:
            file_bytes = uploaded_file.getvalue()
            parsed_df, patient_info = parse_uploaded_lab_file(uploaded_file.name, file_bytes)
            st.session_state.uploaded_results_df = parsed_df
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.parsed_patient_info = patient_info
            render_import_preview(user, parsed_df, patient_info)
        except Exception as exc:
            st.error(f"Dosya okunamadi: {exc}")
        return

    with st.form("google_sheets_form"):
        access_mode = st.selectbox(
            "Erisim Turu",
            options=["Public Sheet URL", "Service Account ile Ozel Sheet"],
        )
        sheet_url = st.text_input(
            "Google Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/...",
        )
        worksheet_name = st.text_input("Sayfa Adi (Opsiyonel)", placeholder="Orn: Sheet1")
        gid = st.text_input("gid (Opsiyonel, public mod icin)", placeholder="Orn: 0")
        submitted = st.form_submit_button("Google Sheets'ten Veriyi Getir", use_container_width=True)

    st.caption(
        "Public mod icin sheet link erisimi acik olmalidir. Ozel sheet icin .env icinde GOOGLE_SERVICE_ACCOUNT_FILE tanimlanmali ve sheet servis hesabiyla paylasilmalidir."
    )

    if not submitted:
        return
    if not sheet_url.strip():
        st.error("Lutfen Google Sheet URL'si girin.")
        return

    try:
        parsed_df = load_google_sheet_lab_data(
            sheet_url=sheet_url.strip(),
            worksheet_name=worksheet_name.strip() or None,
            gid=gid.strip() or None,
            access_mode="service_account" if "Service Account" in access_mode else "public",
        )
        render_import_preview(user, parsed_df)
    except Exception as exc:
        st.error(f"Google Sheets verisi alinamadi: {exc}")


def render_user_page() -> None:
    """Kullanici olusturma ve secme ekrani."""
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.subheader("Kullanici Kaydi ve Secimi")
    st.markdown(
        '<p class="section-note">Ilk adimda kullaniciyi secin veya yeni bir profil olusturun.</p>',
        unsafe_allow_html=True,
    )

    users = get_users()
    user_options = {
        f"{user['name']} ({user['gender']}, {user['age']})": user["id"] for user in users
    }

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        with st.container(border=True):
            st.markdown("#### Var Olan Kullanici")
            if user_options:
                selected_label = st.selectbox("Kullanici Listesi", options=list(user_options.keys()))
                if st.button("Kullanici Seciniz", use_container_width=True):
                    st.session_state.selected_user_id = user_options[selected_label]
                    go_to_page("Tahlil Girisi")
                    st.rerun()
            else:
                st.info("Henuz kayitli kullanici yok.")

    with col2:
        with st.container(border=True):
            st.markdown("#### Yeni Kullanici")
            with st.form("new_user_form", clear_on_submit=True):
                name = st.text_input("Ad Soyad")
                age = st.number_input("Yas", min_value=0, max_value=120, value=30, step=1)
                gender = st.selectbox("Cinsiyet", options=["Kadin", "Erkek"])
                submitted = st.form_submit_button("Kullanici Kaydet", use_container_width=True)

            if submitted:
                if not name.strip():
                    st.error("Lutfen ad soyad girin.")
                else:
                    user_id = create_user(name=name, age=int(age), gender=gender)
                    st.session_state.selected_user_id = user_id
                    go_to_page("Tahlil Girisi")
                    st.rerun()

    selected_user = get_selected_user()
    if selected_user:
        st.markdown(
            f"**Secili Kullanici:** {selected_user['name']} | Yas: {selected_user['age']} | Cinsiyet: {selected_user['gender']}"
        )
        with st.expander("Kullaniciyi duzenle veya sil"):
            with st.form("edit_user_form"):
                new_name = st.text_input("Ad Soyad", value=selected_user["name"])
                new_age = st.number_input(
                    "Yas",
                    min_value=0,
                    max_value=120,
                    value=int(selected_user["age"]),
                    step=1,
                )
                new_gender = st.selectbox(
                    "Cinsiyet",
                    options=["Kadin", "Erkek"],
                    index=0 if selected_user["gender"] == "Kadin" else 1,
                )
                save_user = st.form_submit_button("Bilgileri Guncelle")

            if save_user:
                update_user(
                    user_id=selected_user["id"],
                    name=new_name,
                    age=int(new_age),
                    gender=new_gender,
                )
                st.rerun()

            if st.button("Bu Kullaniciyi Sil", type="secondary"):
                delete_user(selected_user["id"])
                st.session_state.selected_user_id = None
                go_to_page("Kullanici Kaydi/Secimi")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_entry_page() -> None:
    """Manual ve dosya tabanli tahlil giris ekrani."""
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.subheader("Tahlil Girisi")
    st.markdown(
        '<p class="section-note">Ikinci adimda dosya yukleyin veya tek bir sonucu manuel ekleyin.</p>',
        unsafe_allow_html=True,
    )

    user = get_selected_user()
    if not user:
        st.warning("Devam etmek icin once bir kullanici secin veya olusturun.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    upload_col, manual_col = st.columns([1.2, 0.8], gap="large")
    with upload_col:
        render_upload_panel(user)

    with manual_col:
        st.markdown(
            """
            <div style="background: linear-gradient(180deg, #ffffff 0%, #f7fffd 100%);
                        border: 1px solid rgba(15,23,42,0.08);
                        border-radius: 22px;
                        padding: 1rem;">
            """,
            unsafe_allow_html=True,
        )
        st.markdown("#### Hizli Manuel Giris")
        st.caption("Tek bir parametre eklemeniz gerekiyorsa bu formu kullanin.")
        with st.form("test_entry_form", clear_on_submit=True):
            test_date = st.date_input("Tahlil Tarihi", value=date.today())
            test_name = st.selectbox("Test Adi", options=get_available_tests())
            test_value = st.number_input("Sonuc Degeri", value=0.0, step=0.1, format="%.2f")
            unit = st.text_input("Birim", value=get_test_unit(test_name), disabled=True)
            submitted = st.form_submit_button("Tahlili Kaydet ve Analize Gec", use_container_width=True)

        if submitted:
            evaluation = evaluate_result(
                test_name=test_name,
                value=float(test_value),
                age=int(user["age"]),
                gender=user["gender"],
            )
            create_test_result(
                user_id=user["id"],
                test_date=test_date.isoformat(),
                test_name=test_name,
                test_value=float(test_value),
                unit=evaluation["unit"],
                status=evaluation["status"],
                reference_text=evaluation["reference_text"],
                is_out_of_range=evaluation["is_out_of_range"],
            )
            go_to_page("Sonuc Analizi ve Rapor")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_analysis_page() -> None:
    """Tahlil tablosu ve ozet ekrani."""
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.subheader("Sonuc Analizi ve Rapor")
    st.markdown(
        '<p class="section-note">Ucuncu adimda tum sonuclari tablo uzerinden inceleyin.</p>',
        unsafe_allow_html=True,
    )

    user = get_selected_user()
    if not user:
        st.warning("Analiz icin once bir kullanici secin.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    results = get_test_results_by_user(user["id"])
    if not results:
        st.info("Bu kullanici icin kayitli tahlil sonucu bulunmuyor.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    total_count = len(results)
    abnormal_count = sum(1 for result in results if result["is_out_of_range"])
    normal_count = total_count - abnormal_count
    latest_date = results[0]["test_date"] if results else "-"

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-chip"><small>Toplam Sonuc</small><strong>{total_count}</strong></div>
            <div class="metric-chip"><small>Referans Disi</small><strong>{abnormal_count}</strong></div>
            <div class="metric-chip"><small>Normal</small><strong>{normal_count}</strong></div>
            <div class="metric-chip"><small>Son Tahlil</small><strong>{latest_date}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Tahlil Raporlari")
    render_results_by_date_tabs(results, key_prefix="analysis_results")

    if st.button("DR. Yapay Zeka ile Rapor Olustur", type="primary", use_container_width=True):
        abnormal_results = [result for result in results if result["is_out_of_range"]]
        try:
            with st.spinner("DR. Yapay Zeka raporu hazirlaniyor..."):
                st.session_state.llm_report = generate_medical_comment(user, abnormal_results)
            go_to_page("DR. Yapay Zeka")
            st.rerun()
        except Exception as exc:
            st.session_state.llm_report = ""
            st.error(f"DR. Yapay Zeka yorumu alinamadi: {exc}")

    st.markdown("</div>", unsafe_allow_html=True)


def render_ai_doctor_page() -> None:
    """DeepSeek destekli yorum ekrani."""
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.subheader("DR. Yapay Zeka")
    st.markdown(
        '<p class="section-note">Referans disi sonuclar icin yapay zeka destekli yorum bu sekmede yer alir.</p>',
        unsafe_allow_html=True,
    )

    user = get_selected_user()
    if not user:
        st.warning("Devam etmek icin once bir kullanici secin.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    results = get_test_results_by_user(user["id"])
    if not results:
        st.info("Bu kullanici icin henuz kayitli sonuc yok.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    abnormal_results = [result for result in results if result["is_out_of_range"]]
    summary_col1, summary_col2 = st.columns(2)
    with summary_col1:
        st.metric("Referans Disi Sonuc", len(abnormal_results))
    with summary_col2:
        st.metric("Kayitli Toplam Sonuc", len(results))

    if not abnormal_results:
        st.success("Tum sonuclar referans araliginda. DR. Yapay Zeka icin yorum gerektiren bulgu yok.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if st.button("DR. Yapay Zeka ile Raporu Yenile", type="primary", use_container_width=True):
        try:
            with st.spinner("DR. Yapay Zeka raporu hazirlaniyor..."):
                st.session_state.llm_report = generate_medical_comment(user, abnormal_results)
            st.rerun()
        except Exception as exc:
            st.session_state.llm_report = ""
            st.error(f"DR. Yapay Zeka yorumu alinamadi: {exc}")

    if st.session_state.llm_report:
        render_report_box(st.session_state.llm_report)
    else:
        st.info("Henüz uretilmis bir rapor yok. DR. Yapay Zeka ile Raporu Yenile butonuyla yorum olusturabilirsiniz.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_history_page() -> None:
    """Gecmis tahlil kayitlari ve trend ekrani."""
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.subheader("Gecmis Tahliller")
    st.markdown(
        '<p class="section-note">Son adimda onceki sonuclari ve trendleri inceleyin.</p>',
        unsafe_allow_html=True,
    )

    user = get_selected_user()
    if not user:
        st.warning("Gecmis kayitlari gormek icin once bir kullanici secin.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    results = get_test_results_by_user(user["id"])
    if not results:
        st.info("Gosterilecek gecmis tahlil bulunmuyor.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = make_history_dataframe(results)

    st.subheader("Tarih Bazli Raporlar")
    render_results_by_date_tabs(results, key_prefix="history_results")

    st.subheader("Gecmis Deger Trendi")
    render_test_trend_chart(df)

    with st.expander("Kayit Silme"):
        result_id = st.number_input("Silmek istediginiz Kayit ID", min_value=1, step=1)
        if st.button("Kaydi Sil"):
            deleted = delete_test_result(int(result_id))
            if deleted:
                st.rerun()
            else:
                st.error("Belirtilen ID ile kayit bulunamadi.")

    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    """Uygulama giris noktasi."""
    init_db()
    initialize_session()
    inject_global_styles()

    selected_user = get_selected_user()
    render_hero(selected_user)
    render_sidebar()
    page = st.session_state.get("current_page", PAGES[0])
    stepper_page = render_stepper(page)
    if stepper_page != page:
        go_to_page(stepper_page)
        page = stepper_page

    if page == "Kullanici Kaydi/Secimi":
        render_user_page()
    elif page == "Tahlil Girisi":
        render_entry_page()
    elif page == "Sonuc Analizi ve Rapor":
        render_analysis_page()
    elif page == "DR. Yapay Zeka":
        render_ai_doctor_page()
    else:
        render_history_page()


if __name__ == "__main__":
    main()
