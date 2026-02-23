# 🌐 Internet Trafik İzleyici

Modern ve kullanıcı dostu bir internet trafik izleme uygulaması. Gerçek zamanlı ağ kullanımınızı takip edin, analiz edin ve kontrol altına alın.

![Version](https://img.shields.io/badge/version-1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

## 🖼️ Ekran Görüntüleri

### Ana Ekran
![Python Ana Ekran](screenshots/python-ana-ekran.png)

### Grafikler
![Python Çizgi Grafik](screenshots/python-cizgi-grafigi.png)
![Python Sütun Grafik](screenshots/python-sutun-grafigi.png)
![Python Pasta Grafik](screenshots/python-pasta-grafigi.png)

### Ayarlar
![Python Ayarlar](screenshots/python-ayarlar.png)

### Rust (Opsiyonel)
![Rust Ana Ekran](screenshots/rust-ana-ekran.png)
![Rust Ayarlar](screenshots/rust-ayarlar.png)

## ✨ Özellikler

### 📊 Temel Özellikler
- **Gerçek Zamanlı İzleme**: Anlık download/upload hızı ve toplam veri kullanımı
- **İki İzleme Modu**:
  - Genel Takip: Tüm sistem trafiği
  - Uygulama Bazlı: Belirli uygulamaların (Chrome, Discord, vb.) trafiği
- **Akıllı Uygulama Seçici**: Çalışan uygulamaları otomatik listeler
- **Kota Yönetimi**: Veri limiti belirleyin, uyarı alın
- **Otomatik Kayıt**: Tüm oturumlar SQLite veritabanına kaydedilir

### 📈 Analiz ve Raporlama
- **3 Farklı Grafik Türü**:
  - Çizgi Grafik: Zaman serisi analizi
  - Sütun Grafik: Günlük toplam kullanım
  - Pasta Grafik: Download vs Upload dağılımı
- **İstatistikler**: Toplam oturum, süre, veri kullanımı
- **CSV Dışa Aktarma**: Excel uyumlu veri dışa aktarma

### 🚀 Gelişmiş Özellikler
- **Hız Testi**: Gerçek internet hızınızı ölçün
- **IP Analizi**: Public/Local IP ve aktif bağlantıları görüntüleyin
- **Mini Widget**: Sürüklenebilir hız göstergesi
- **Sistem Tepsisi**: Arka planda çalışma desteği
- **Windows Başlangıç**: Otomatik başlatma seçeneği
- **RAM/CPU Göstergesi**: Uygulamanın kaynak kullanımını izleyin

### ⚙️ Ayarlar
- Windows ile başlat
- Otomatik izleme başlat
- Sistem tepsisine küçült
- Güncelleme aralığı (1-10 saniye)
- Veri klasörü yönetimi

## 📥 Kurulum

### Hazır EXE (Önerilen)
1. [Releases](../../releases) sayfasından son sürümü indirin.
2. `InternetTrafikIzleyici.exe` dosyasını çalıştırın.
3. İlk çalıştırmada Windows Defender uyarı verebilir:
   - "Daha fazla bilgi" → "Yine de çalıştır"

### Kaynak Koddan Çalıştırma
```bash
pip install customtkinter psutil matplotlib pillow pystray win10toast requests
python internet_trafik_izleyici.py
```

### Kendi EXE'nizi Oluşturun
```bash
pip install pyinstaller
python build_exe.py
```

## 💾 Veri Depolama

Tüm veriler şu konumda saklanır:

```text
C:\Users\[KullaniciAdi]\AppData\Roaming\InternetTrafikIzleyici\
├── internet_traffic.db  (Veritabanı)
└── settings.json        (Ayarlar)
```

## 🛠️ Teknolojiler

- **Python 3.11**
- **CustomTkinter**
- **psutil**
- **matplotlib**
- **SQLite**
- **PyInstaller**

## 📋 Sistem Gereksinimleri

- **İşletim Sistemi**: Windows 10/11
- **RAM**: Minimum 100 MB
- **Disk**: 100 MB boş alan
- **Python**: 3.11+ (kaynak kod için)

## 📝 Lisans

Bu proje MIT lisansı altındadır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

**Not**: Bu uygulama sadece izleme amaçlıdır. Ağ trafiğini engellemez veya değiştirmez.
