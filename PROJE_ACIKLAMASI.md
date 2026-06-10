# Tahlil Robotu - Proje Aciklamasi

## Genel Bakis

Tahlil Robotu, laboratuvar sonuclarini tek bir yerde toplamak, referans araliklariyla karsilastirmak ve referans disi bulgular icin yapay zeka destekli yorum uretmek amaciyla gelistirilmis bir Streamlit uygulamasidir.

Uygulama uc temel ihtiyaci cozer:

1. Kullanici ve tahlil verisini kolayca sisteme almak
2. Sonuclari normal / dusuk / yuksek olarak siniflandirmak
3. Anormal sonuclari daha anlasilir hale getirmek

Bu proje bir hastane bilgi sistemi degil; daha cok kucuk olcekli bir takip, inceleme ve demo urunudur.

## Projenin Amaci

Projede kullanici:

- Yeni bir profil olusturabilir veya mevcut bir profili secebilir
- Tahlil sonucunu manuel girebilir
- PDF, Excel veya Google Sheets uzerinden toplu veri ice aktarabilir
- Sonuclari tablo halinde gorebilir
- Gecmis testleri icin trend grafigi inceleyebilir
- Referans disi sonuc varsa DeepSeek tabanli aciklayici yorum alabilir

## Kullanilan Teknolojiler

- `Streamlit`: Arayuz ve sayfa akislarini olusturmak icin
- `SQLite`: Kullanici ve test sonuc kayitlarini saklamak icin
- `pandas`: Tablo verisini islemek icin
- `pdfplumber` ve `pypdf`: PDF tahlil belgelerini okumak icin
- `openpyxl`: Excel dosyalarini ayrismak icin
- `gspread` ve `google-auth`: Google Sheets verisi cekmek icin
- `OpenAI SDK`: DeepSeek'in OpenAI uyumlu API'sine baglanmak icin
- `python-dotenv`: `.env` ayarlarini yuklemek icin

## Uygulama Mimarisi

Proje moduler bir yapida kurulmus. Her dosya belirli bir sorumluluk tasiyor:

### `app.py`

Uygulamanin ana giris noktasi. Tum sayfa akislarini ve Streamlit ekranlarini yonetir.

Sorumluluklari:

- Veritabanini baslatmak
- Session state anahtarlarini olusturmak
- Aktif kullaniciyi belirlemek
- Sayfalar arasi gecisi yonetmek
- Manuel giris, dosya yukleme, analiz, AI yorum ve gecmis ekranlarini cizmek

Bu dosya projenin "orkestrasyon" katmanidir.

### `database.py`

SQLite tarafindaki tum islemleri toplar.

Tablolar:

- `Users`
  - `id`
  - `name`
  - `age`
  - `gender`
- `TestResults`
  - `id`
  - `user_id`
  - `test_date`
  - `test_name`
  - `test_value`
  - `unit`
  - `status`
  - `reference_text`
  - `is_out_of_range`

Sundugu temel islemler:

- Kullanici ekleme, listeleme, guncelleme, silme
- Tahlil sonucu ekleme, listeleme, guncelleme, silme

`Users` ile `TestResults` arasinda bire-cok iliski vardir. Bir kullanici silindiginde ona bagli tahliller de silinir.

### `reference_engine.py`

Projenin kurala dayali analiz motorudur.

Sorumluluklari:

- Belirli testler icin referans araliklarini tanimlamak
- Test adlarini normalize etmek
- Yas ve cinsiyete gore uygun referans kuralini secmek
- Sonucu `Normal`, `Dusuk` veya `Yuksek` olarak siniflandirmak
- Belgeden gelen referans metnini parse ederek durum cikarmak

Desteklenen testler kod icinde sabit tanimli:

- `Hemoglobin`
- `Ferritin`
- `B12`
- `D Vitamini`
- `Aclik Kan Sekeri`
- `Toplam Kolesterol`

Bu yapi kolay bir baslangic saglasa da daha buyuk bir urunde bu alanin veritabani veya harici konfigurasyonla yonetilmesi daha uygun olur.

### `lab_parser.py`

Ice aktarma motorudur. Farkli kaynaklardan gelen tahlil verisini ortak bir formata donusturur.

Desteklenen kaynaklar:

- PDF
- Excel (`.xlsx`, `.xls`)
- DataFrame tabanli tablolar

Standartlasan cikti kolonlari:

- `test_date`
- `test_name`
- `test_value`
- `unit`
- `reference_text`
- `status`
- `is_out_of_range`
- `source`

Bu dosyanin onemi su: farkli veri kaynaklarini uygulamanin anlayacagi tek bir yapida toplar.

### `google_sheets_service.py`

Google Sheets baglantisini yonetir.

Iki kullanim sekli vardir:

- Public sheet: Sheet URL'si `csv export` linkine cevrilip `pandas.read_csv` ile okunur
- Service account: Google servis hesabi kullanilarak ozel sheet'e erisim saglanir

Okunan veri daha sonra `lab_parser.parse_lab_dataframe(...)` ile ortak formata cevrilir.

### `llm_service.py`

Yapay zeka yorum katmanidir.

Isleyis:

- `.env` icinden `DEEPSEEK_API_KEY` okunur
- DeepSeek icin OpenAI uyumlu istemci olusturulur
- Referans disi sonuclar ozet bir prompt haline getirilir
- Modelden Turkce, dengeli ve uyari iceren bir yorum istenir

Bu katman sadece anormal sonuclari modele gonderir; bu sayede prompt daha odakli kalir.

### `ui_components.py`

Tekrar kullanilan arayuz bilesenlerini ve stil yardimcilarini barindirir.

Sorumluluklari:

- Global CSS enjekte etmek
- Hero alani gostermek
- Ust adim navigasyonunu olusturmak
- AI rapor kutusunu cizmek
- Sonuc tablolarini duruma gore renklendirmek

Bu dosya sayesinde `app.py` icindeki arayuz kodu bir miktar sade tutulmus.

## Kullanici Akisi

Uygulama 5 adimli bir akisla calisiyor:

### 1. Kullanici Kaydi / Secimi

Kullanici yeni profil olusturur veya var olan profili secer.

### 2. Tahlil Girisi

Bu adimda iki secenek vardir:

- Manuel tekli tahlil girisi
- PDF / Excel / Google Sheets ile toplu veri alma

### 3. Sonuc Analizi ve Rapor

Tum sonuclar tablo olarak listelenir.

Bu ekranda:

- Toplam sonuc sayisi
- Referans disi sonuc sayisi
- Normal sonuc sayisi
- Son tahlil tarihi

ozet olarak gosterilir.

### 4. DR. Yapay Zeka

Referans disi sonuclar varsa DeepSeek ile yorum uretilir. Sonuclar tamamen normalse sistem yorum gerektirmedigini bildirir.

### 5. Gecmis Tahliller

Kullanici tum kayitlarini gorur, secilen test icin cizgi grafigi inceler ve isterse belirli bir kaydi silebilir.

## Veri Akisi

Projede veri akisinin basit hali soyledir:

1. Kullanici veriyi manuel girer veya bir kaynaktan yukler
2. `lab_parser.py` veya manuel form veriyi normalize eder
3. `reference_engine.py` sonucun durumunu hesaplar
4. `database.py` kaydi `SQLite` icine yazar
5. `app.py` kayitlari okuyup analiz ekraninda gosterir
6. Anormal sonuclar varsa `llm_service.py` ile AI yorumu uretilir

## Ice Aktarma Mantigi

### PDF

PDF tarafinda e-Nabiz benzeri tablo yapisi hedeflenmis. Sistem:

- Tarih bilgisini satirlardan ayiklar
- Test adini normalize eder
- Sonuc degerini sayiya cevirir
- Referans metnini okuyup durum hesabi yapar
- Varsa temel hasta bilgisini ilk sayfadan cekmeye calisir

### Excel

Excel dosyalarinda kolon adlari eslestirilerek veri cekilir. Sistem su tip kolon isimlerini taniyacak sekilde yazilmis:

- test / tahlil / analiz / parametre
- sonuc / deger / value
- birim / unit
- referans / reference
- tarih / date

Bu, farkli formatlardaki dosyalari belli olcude tolere etmesini saglar.

### Google Sheets

Google Sheets'te de Excel'e benzer sekilde kolon bazli bir parse islemi uygulanir. Sheet verisi once okunur, sonra ortak normalize akisina sokulur.

## Yapay Zeka Yorum Mantigi

AI katmani tum sonuclari degil, yalnizca referans disi olanlari gonderir.

Prompt icinde su bilgiler yer alir:

- Kullanici adi
- Yas
- Cinsiyet
- Test adi
- Olculen deger
- Birim
- Durum
- Referans araligi

Modelden her anormal sonuc icin su beklentiler istenir:

1. Olası anlam
2. Beslenme / yasam tarzı onerisi
3. Hangi durumda doktora gidilmesi gerektigi
4. En sonda tibbi uyari

Bu yaklasim urunu "otomatik tani koyan sistem" olmaktan uzak tutup "aciklayici yorumlayici" seviyesinde tutuyor.

