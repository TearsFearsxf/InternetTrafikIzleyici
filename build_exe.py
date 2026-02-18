#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXE Builder - Internet Trafik İzleyici
Optimize edilmiş, tek dosya EXE oluşturur
"""

import os
import sys
import subprocess
import shutil

def check_dependencies():
    """Gerekli kütüphaneleri kontrol eder"""
    print("📦 Gerekli kütüphaneler kontrol ediliyor...")
    
    required = ['pyinstaller', 'customtkinter', 'psutil', 'matplotlib', 'pillow', 'pystray', 'win10toast', 'requests']
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - Yükleniyor...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
    
    print("\n✓ Tüm bağımlılıklar hazır!\n")

def create_spec_file():
    """PyInstaller spec dosyası oluşturur"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['internet_trafik_izleyici.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'customtkinter',
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.ttk',
        'psutil',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'pystray',
        'win10toast',
        'requests',
        'sqlite3',
        'csv',
        'json',
        'collections',
        'threading',
        'datetime'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='InternetTrafikIzleyici',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
    version_file=None,
)
"""
    
    with open('internet_trafik_izleyici.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✓ Spec dosyası oluşturuldu\n")

def build_exe():
    """EXE dosyasını oluşturur"""
    print("🔨 EXE oluşturuluyor... (Bu işlem 2-5 dakika sürebilir)\n")
    
    try:
        # PyInstaller ile build
        subprocess.check_call([
            'pyinstaller',
            '--clean',
            '--noconfirm',
            'internet_trafik_izleyici.spec'
        ])
        
        print("\n✓ EXE başarıyla oluşturuldu!")
        print(f"\n📁 Dosya konumu: {os.path.abspath('dist/InternetTrafikIzleyici.exe')}")
        
        # Dosya boyutunu göster
        exe_path = 'dist/InternetTrafikIzleyici.exe'
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"📊 Dosya boyutu: {size_mb:.2f} MB")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Hata: {e}")
        return False

def cleanup():
    """Gereksiz dosyaları temizler"""
    print("\n🧹 Temizlik yapılıyor...")
    
    dirs_to_remove = ['build', '__pycache__']
    files_to_remove = ['internet_trafik_izleyici.spec']
    
    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"  ✓ {d} silindi")
    
    for f in files_to_remove:
        if os.path.exists(f):
            os.remove(f)
            print(f"  ✓ {f} silindi")
    
    print("\n✓ Temizlik tamamlandı!")

def main():
    """Ana build fonksiyonu"""
    print("=" * 60)
    print("  INTERNET TRAFİK İZLEYİCİ - EXE BUILDER")
    print("=" * 60)
    print()
    
    # 1. Bağımlılıkları kontrol et
    check_dependencies()
    
    # 2. Spec dosyası oluştur
    create_spec_file()
    
    # 3. EXE oluştur
    success = build_exe()
    
    if success:
        # 4. Temizlik
        cleanup()
        
        print("\n" + "=" * 60)
        print("  ✓ BUILD BAŞARILI!")
        print("=" * 60)
        print("\n📦 EXE dosyanız hazır: dist/InternetTrafikIzleyici.exe")
        print("\n💡 İpucu: İlk çalıştırmada Windows Defender uyarı verebilir.")
        print("   'Daha fazla bilgi' -> 'Yine de çalıştır' seçeneğini kullanın.\n")
    else:
        print("\n❌ Build başarısız oldu. Lütfen hataları kontrol edin.")

if __name__ == "__main__":
    main()
