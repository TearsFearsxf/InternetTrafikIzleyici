# ğŸŒ Internet Trafik Ä°zleyici

Modern ve kullanÄ±cÄ± dostu bir internet trafik izleme uygulamasÄ±. GerÃ§ek zamanlÄ± aÄŸ kullanÄ±mÄ±nÄ±zÄ± takip edin, analiz edin ve kontrol altÄ±nda tutun.

![Version](https://img.shields.io/badge/version-1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

## âœ¨ Ã–zellikler

### ğŸ“Š Temel Ã–zellikler
- **GerÃ§ek ZamanlÄ± Ä°zleme**: AnlÄ±k download/upload hÄ±zÄ± ve toplam veri kullanÄ±mÄ±
- **Ä°ki Ä°zleme Modu**:
  - Genel Takip: TÃ¼m sistem trafiÄŸi
  - Uygulama BazlÄ±: Belirli uygulamalarÄ±n (Chrome, Discord, vb.) trafiÄŸi
- **AkÄ±llÄ± Uygulama SeÃ§ici**: Ã‡alÄ±ÅŸan uygulamalarÄ± otomatik listeler
- **Kota YÃ¶netimi**: Veri limiti belirleyin, uyarÄ± alÄ±n
- **Otomatik KayÄ±t**: TÃ¼m oturumlar SQLite veritabanÄ±na kaydedilir

### ğŸ“ˆ Analiz ve Raporlama
- **3 FarklÄ± Grafik TÃ¼rÃ¼**:
  - Ã‡izgi Grafik: Zaman serisi analizi
  - SÃ¼tun Grafik: GÃ¼nlÃ¼k toplam kullanÄ±m
  - Pasta Grafik: Download vs Upload daÄŸÄ±lÄ±mÄ±
- **Ä°statistikler**: Toplam oturum, sÃ¼re, veri kullanÄ±mÄ±
- **CSV DÄ±ÅŸa Aktarma**: Excel uyumlu veri dÄ±ÅŸa aktarma

### ğŸš€ GeliÅŸmiÅŸ Ã–zellikler
- **HÄ±z Testi**: GerÃ§ek internet hÄ±zÄ±nÄ±zÄ± Ã¶lÃ§Ã¼n
- **IP Analizi**: Public/Local IP ve aktif baÄŸlantÄ±larÄ± gÃ¶rÃ¼ntÃ¼leyin
- **Mini Widget**: SÃ¼rÃ¼klenebilir, ÅŸeffaf hÄ±z gÃ¶stergesi
- **Sistem Tepsisi**: Arka planda Ã§alÄ±ÅŸma desteÄŸi
- **Windows BaÅŸlangÄ±Ã§**: Otomatik baÅŸlatma seÃ§eneÄŸi
- **RAM/CPU GÃ¶stergesi**: UygulamanÄ±n kaynak kullanÄ±mÄ±nÄ± izleyin

### âš™ï¸ Ayarlar
- Windows ile baÅŸlat
- Otomatik izleme baÅŸlat
- Sistem tepsisine kÃ¼Ã§Ã¼lt
- GÃ¼ncelleme aralÄ±ÄŸÄ± (1-10 saniye)
- Veri klasÃ¶rÃ¼ yÃ¶netimi

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

## ğŸ“¥ Kurulum

### HazÄ±r EXE (Ã–nerilen)
1. [Releases](../../releases) sayfasÄ±ndan son sÃ¼rÃ¼mÃ¼ indirin
2. `InternetTrafikIzleyici.exe` dosyasÄ±nÄ± Ã§alÄ±ÅŸtÄ±rÄ±n
3. Ä°lk Ã§alÄ±ÅŸtÄ±rmada Windows Defender uyarÄ± verebilir:
   - "Daha fazla bilgi" â†’ "Yine de Ã§alÄ±ÅŸtÄ±r"

### Kaynak Koddan Ã‡alÄ±ÅŸtÄ±rma
```bash
# Gerekli kÃ¼tÃ¼phaneleri yÃ¼kleyin
pip install customtkinter psutil matplotlib pillow pystray win10toast requests

# UygulamayÄ± Ã§alÄ±ÅŸtÄ±rÄ±n
python internet_trafik_izleyici.py
```

### Kendi EXE'nizi OluÅŸturun
```bash
# PyInstaller'Ä± yÃ¼kleyin
pip install pyinstaller

# EXE oluÅŸturun
python build_exe.py
```

## ğŸ’¾ Veri Depolama

TÃ¼m veriler gÃ¼venli bir konumda saklanÄ±r:
```
C:\Users\[KullanÄ±cÄ±AdÄ±]\AppData\Roaming\InternetTrafikIzleyici\
â”œâ”€â”€ internet_traffic.db  (VeritabanÄ±)
â””â”€â”€ settings.json        (Ayarlar)
```

Bu sayede uygulamayÄ± silseniz bile verileriniz gÃ¼vende kalÄ±r.

## ğŸ› ï¸ Teknolojiler

- **Python 3.11**: Ana programlama dili
- **CustomTkinter**: Modern GUI framework
- **psutil**: Sistem ve aÄŸ izleme
- **matplotlib**: Grafik ve gÃ¶rselleÅŸtirme
- **SQLite**: VeritabanÄ± yÃ¶netimi
- **PyInstaller**: EXE paketleme

## ğŸ“‹ Sistem Gereksinimleri

- **Ä°ÅŸletim Sistemi**: Windows 10/11
- **RAM**: Minimum 100 MB
- **Disk**: 100 MB boÅŸ alan
- **Python**: 3.11+ (kaynak koddan Ã§alÄ±ÅŸtÄ±rma iÃ§in)

## ğŸ¯ KullanÄ±m SenaryolarÄ±

- ğŸ“± **Mobil Hotspot KullanÄ±cÄ±larÄ±**: Veri kotanÄ±zÄ± aÅŸmayÄ±n
- ğŸ® **Oyuncular**: Hangi oyunun ne kadar veri harcadÄ±ÄŸÄ±nÄ± gÃ¶rÃ¼n
- ğŸ’¼ **Uzaktan Ã‡alÄ±ÅŸanlar**: Ä°ÅŸ uygulamalarÄ±nÄ±zÄ±n veri kullanÄ±mÄ±nÄ± takip edin
- ğŸ  **Ev KullanÄ±cÄ±larÄ±**: AylÄ±k internet kotanÄ±zÄ± yÃ¶netin
- ğŸ” **MeraklÄ±lar**: AÄŸ trafiÄŸinizi detaylÄ± analiz edin

## ğŸ¤ KatkÄ±da Bulunma

KatkÄ±larÄ±nÄ±zÄ± bekliyoruz! LÃ¼tfen ÅŸu adÄ±mlarÄ± izleyin:

1. Fork yapÄ±n
2. Feature branch oluÅŸturun (`git checkout -b feature/AmazingFeature`)
3. DeÄŸiÅŸikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'inizi push edin (`git push origin feature/AmazingFeature`)
5. Pull Request aÃ§Ä±n

## ğŸ“ Lisans

Bu proje MIT lisansÄ± altÄ±nda lisanslanmÄ±ÅŸtÄ±r. Detaylar iÃ§in [LICENSE](LICENSE) dosyasÄ±na bakÄ±n.

## ğŸ› Hata Bildirimi

Bir hata mÄ± buldunuz? [Issues](../../issues) sayfasÄ±ndan bildirebilirsiniz.

## ğŸ“§ Ä°letiÅŸim

SorularÄ±nÄ±z iÃ§in issue aÃ§abilir veya pull request gÃ¶nderebilirsiniz.

## ğŸŒŸ YÄ±ldÄ±z Verin!

Bu projeyi beÄŸendiyseniz, lÃ¼tfen â­ vererek destek olun!

---

**Not**: Bu uygulama sadece izleme amaÃ§lÄ±dÄ±r. AÄŸ trafiÄŸini engellemez veya deÄŸiÅŸtirmez.

