# Rust Surumu (GUI)

Bu klasor, Python'daki uygulamanin Rust GUI portudur.

## Calistirma

```bash
cargo run
```

## Dahil Ozellikler

- Gercek zamanli genel trafik izleme
- Oturum kaydi (`sessions`) + hiz testi kaydi (`speed_tests`) SQLite
- Kota limiti ve otomatik durdurma
- Cizgi, sutun ve pasta grafik
- Istatistikler penceresi
- CSV disa aktarma
- Ayarlar (`settings.json`) + Windows startup togglesi
- App listesi yenileme + app modu process kontrolu
- Mini widget penceresi
- Sistem tepsisi menusu (ac, mini widget, hiz testi, cikis)
- Basit hiz testi
- Public/Local IP analizi

## Not

- Veriler Python uygulamasi ile ayni klasorde tutulur:
  `C:\Users\<Kullanici>\AppData\Roaming\InternetTrafikIzleyici\`
- `Uygulama bazli takip` modu su an metadata kaydeder; olcum motoru heniz ETW tabanli degil.
