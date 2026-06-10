# Tahlil Robotu

Kullanicilarin laboratuvar sonuclarini manuel girebildigi veya PDF/Excel/Google Sheets olarak yukleyebildigi, SQLite veritabanina kaydedebildigi, referans araliklariyla karsilastirabildigi ve referans disi sonuclari DeepSeek ile yorumlayabildigi Streamlit uygulamasidir.

## Dosya Yapisi

- `app.py`: Streamlit arayuzu
- `database.py`: SQLite tablo ve CRUD islemleri
- `reference_engine.py`: Referans araligi motoru
- `lab_parser.py`: PDF/Excel tahlil ayrisma modulu
- `google_sheets_service.py`: Google Sheets entegrasyonu
- `llm_service.py`: DeepSeek API entegrasyonu
- `ui_components.py`: Modern ve kompakt arayuz yardimcilari
- `requirements.txt`: Gerekli Python paketleri

## Kurulum

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

`.env` dosyasina kendi DeepSeek API anahtarinizi yazin:

```env
DEEPSEEK_API_KEY=your_real_key
# Opsiyonel: ozel Google Sheet okumak icin servis hesabi json yolu
# GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
```

## Calistirma

```bash
streamlit run app.py
```

## Notlar

- Veritabani ilk calistirmada ayni klasorde `tahlil.db` olarak olusturulur.
- Kullanici kaydi ekraninda PDF, Excel veya Google Sheets tahlil kaynagi yuklenebilir.
- e-Nabiz benzeri PDF raporlari tablo yapisindan okunur.
- Google Sheets icin iki mod vardir:
- Public mod: Google Sheet URL'si ve gerekirse `gid` ile dogrudan okunur.
- Service Account mod: `.env` icindeki `GOOGLE_SERVICE_ACCOUNT_FILE` ile ozel sheet okunur.
- DeepSeek yorumu sadece referans disi sonuclar icin uretilir.
- Uygulama tibbi tani koymaz; ekrandaki uyarilar ve LLM cevabi bilgilendirme amaclidir.
