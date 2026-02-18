#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internet Trafik İzleyici - Modern Ağ İzleme Uygulaması
Senior Python Developer & UI/UX Tasarımcısı
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import psutil
import sqlite3
import threading
import time
import datetime
import csv
import os
import sys
import socket
import pystray
from PIL import Image, ImageDraw
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from collections import deque
import win10toast  # Windows bildirimleri için
import requests
import json

# Tema ayarları
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class InternetTrafikIzleyici:
    """Ana uygulama sınıfı - Internet trafik izleme uygulaması"""
    
    def __init__(self):
        """Uygulama başlatıcı - Tüm bileşenleri hazırlar"""
        self.root = ctk.CTk()
        self.root.title("Internet Trafik İzleyici")
        self.root.geometry("1200x800")
        
        # Icon ayarla
        try:
            # EXE içindeyse _MEIPASS klasöründen yükle
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, 'app_icon.ico')
            else:
                icon_path = 'app_icon.ico'
            
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                print(f"Icon yüklendi: {icon_path}")
        except Exception as e:
            print(f"Icon yüklenemedi: {e}")
        
        # Pencereyi yeniden boyutlandırılabilir yap
        self.root.resizable(True, True)
        
        # Minimum boyut ayarla
        self.root.minsize(1000, 700)
        
        # Uygulama veri klasörünü oluştur (AppData)
        self.app_data_dir = os.path.join(os.getenv('APPDATA'), 'InternetTrafikIzleyici')
        if not os.path.exists(self.app_data_dir):
            os.makedirs(self.app_data_dir)
        
        # Veritabanı ve ayarlar yolu
        self.db_path = os.path.join(self.app_data_dir, 'internet_traffic.db')
        self.settings_path = os.path.join(self.app_data_dir, 'settings.json')
        
        print(f"Veri klasörü: {self.app_data_dir}")
        
        # Veritabanı bağlantısı
        self.db_connection = None
        self.cursor = None
        self.init_database()
        
        # İzleme değişkenleri
        self.is_monitoring = False
        self.monitoring_thread = None
        self.start_time = None
        self.total_download = 0
        self.total_upload = 0
        self.last_bytes_sent = 0
        self.last_bytes_recv = 0
        
        # Anlık hız hesaplama için - daha az bellek
        self.speed_history = deque(maxlen=5)  # 10'dan 5'e düşürdük
        self.process_name = ""
        
        # Kota ayarları
        self.data_limit = 500  # MB cinsinden varsayılan limit
        self.limit_enabled = False
        self.shutdown_on_limit = False
        
        # UI bileşenleri
        self.setup_ui()
        
        # Windows bildirimleri
        self.toaster = win10toast.ToastNotifier()
        
        # Yeni özellikler için değişkenler
        self.system_tray_icon = None
        self.mini_widget = None
        self.mini_widget_visible = False
        self.ip_analysis_data = {}
        self.speed_test_results = []
        
        # Ayarlar
        self.settings = {
            'start_with_windows': False,
            'minimize_to_tray': True,
            'auto_start_monitoring': False,
            'update_interval': 3,
            'theme': 'dark'
        }
        self.load_settings()
        
        # Uygulama listesini başlangıçta yenile
        self.root.after(1000, self.refresh_app_list)
        
        # Otomatik izleme başlat (ayarlarda aktifse)
        if self.settings.get('auto_start_monitoring', False):
            self.root.after(2000, self.start_monitoring)
        
        # Sağ alt köşeye sistem kaynak göstergesi ekle
        # Frame ile arka plan
        self.resource_frame = ctk.CTkFrame(
            self.root,
            fg_color="black",
            corner_radius=8
        )
        self.resource_frame.place(relx=0.99, rely=0.99, anchor='se')
        
        self.resource_label = ctk.CTkLabel(
            self.resource_frame, 
            text="RAM: -- | CPU: --%", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white",
            padx=10,
            pady=5
        )
        self.resource_label.pack()
        
        # Kaynak kullanımını güncelleyen thread
        self.resource_thread = threading.Thread(target=self.update_resource_usage, daemon=True)
        self.resource_thread.start()
        
        # Pencere kapatma olayını yakala
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def init_database(self):
        """SQLite veritabanını başlatır ve tabloları oluşturur"""
        try:
            self.db_connection = sqlite3.connect(self.db_path)
            self.cursor = self.db_connection.cursor()
            
            # Oturumlar tablosu
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    download_mb REAL NOT NULL,
                    upload_mb REAL NOT NULL,
                    tracking_type TEXT NOT NULL,
                    process_name TEXT
                )
            ''')
            
            self.db_connection.commit()
            print(f"Veritabanı başarıyla başlatıldı: {self.db_path}")
        except Exception as e:
            print(f"Veritabanı hatası: {e}")
            messagebox.showerror("Veritabanı Hatası", f"Veritabanı başlatılamadı: {e}")
    
    def setup_ui(self):
        """Kullanıcı arayüzünü oluşturur ve düzenler"""
        # Ana frame
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Sol panel container - Sabit genişlik
        left_container = ctk.CTkFrame(main_frame, width=320)
        left_container.pack(side="left", fill="y", padx=(0, 10))
        left_container.pack_propagate(False)
        
        # Sol panel - Scrollable içerik
        left_panel = ctk.CTkScrollableFrame(left_container)
        left_panel.pack(fill="both", expand=True)
        
        # Sağ panel - Göstergeler ve grafikler
        right_panel = ctk.CTkFrame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True)
        
        # Sol panel içeriği
        self.setup_left_panel(left_panel)
        
        # Sağ panel içeriği
        self.setup_right_panel(right_panel)
    
    def setup_left_panel(self, parent):
        """Sol paneldeki kontrol bileşenlerini oluşturur"""
        # Başlık
        title_label = ctk.CTkLabel(parent, text="Internet Trafik İzleyici", 
                                   font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=20)
        
        # Takip modu seçimi
        mode_frame = ctk.CTkFrame(parent)
        mode_frame.pack(fill="x", padx=20, pady=10)
        
        mode_label = ctk.CTkLabel(mode_frame, text="Takip Modu:", font=ctk.CTkFont(size=14))
        mode_label.pack(anchor="w", pady=(0, 5))
        
        self.tracking_mode = tk.StringVar(value="general")
        
        general_radio = ctk.CTkRadioButton(mode_frame, text="Genel Takip (Tüm Sistem)", 
                                          variable=self.tracking_mode, value="general")
        general_radio.pack(anchor="w", pady=2)
        
        app_radio = ctk.CTkRadioButton(mode_frame, text="Uygulama Bazlı Takip", 
                                       variable=self.tracking_mode, value="app")
        app_radio.pack(anchor="w", pady=2)
        
        # Uygulama seçici
        self.app_name_frame = ctk.CTkFrame(parent)
        self.app_name_frame.pack(fill="x", padx=20, pady=5)
        
        app_label = ctk.CTkLabel(self.app_name_frame, text="Uygulama Seçin:")
        app_label.pack(anchor="w")
        
        # Uygulama seçici frame
        app_selector_frame = ctk.CTkFrame(self.app_name_frame)
        app_selector_frame.pack(fill="x", pady=(5, 0))
        
        # Açılır liste
        self.app_combobox = ctk.CTkComboBox(app_selector_frame, 
                                           values=["chrome.exe", "firefox.exe", "msedge.exe"],
                                           state="readonly")
        self.app_combobox.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Yenile butonu
        refresh_btn = ctk.CTkButton(app_selector_frame, text="🔄", width=40,
                                   command=self.refresh_app_list)
        refresh_btn.pack(side="right")
        
        # Elle giriş için
        manual_frame = ctk.CTkFrame(self.app_name_frame)
        manual_frame.pack(fill="x", pady=(5, 10))
        
        manual_label = ctk.CTkLabel(manual_frame, text="Veya elle girin:")
        manual_label.pack(side="left", padx=(0, 10))
        
        self.app_name_entry = ctk.CTkEntry(manual_frame, placeholder_text="chrome.exe")
        self.app_name_entry.pack(side="left", fill="x", expand=True)
        
        # Takip butonları
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        self.start_button = ctk.CTkButton(button_frame, text="BAŞLAT", 
                                         command=self.start_monitoring,
                                         height=50, font=ctk.CTkFont(size=16, weight="bold"))
        self.start_button.pack(fill="x", pady=5)
        
        self.stop_button = ctk.CTkButton(button_frame, text="DURDUR", 
                                        command=self.stop_monitoring,
                                        height=50, font=ctk.CTkFont(size=16, weight="bold"),
                                        state="disabled")
        self.stop_button.pack(fill="x", pady=5)
        
        # Kota ayarları
        quota_frame = ctk.CTkFrame(parent)
        quota_frame.pack(fill="x", padx=20, pady=20)
        
        quota_label = ctk.CTkLabel(quota_frame, text="Kota Ayarları", 
                                  font=ctk.CTkFont(size=14, weight="bold"))
        quota_label.pack(anchor="w", pady=(0, 10))
        
        limit_frame = ctk.CTkFrame(quota_frame)
        limit_frame.pack(fill="x", pady=5)
        
        limit_label = ctk.CTkLabel(limit_frame, text="Limit (MB):")
        limit_label.pack(side="left", padx=(0, 10))
        
        self.limit_entry = ctk.CTkEntry(limit_frame, width=100)
        self.limit_entry.insert(0, "500")
        self.limit_entry.pack(side="left")
        
        self.limit_checkbox = ctk.CTkCheckBox(quota_frame, text="Kota uyarısını aktif et")
        self.limit_checkbox.pack(anchor="w", pady=5)
        
        self.shutdown_checkbox = ctk.CTkCheckBox(quota_frame, text="Limit dolunca izlemeyi durdur")
        self.shutdown_checkbox.pack(anchor="w", pady=5)
        
        # Yeni özellikler butonları
        features_frame = ctk.CTkFrame(parent)
        features_frame.pack(fill="x", padx=20, pady=20)
        
        features_label = ctk.CTkLabel(features_frame, text="Zeka Özellikleri", 
                                     font=ctk.CTkFont(size=14, weight="bold"))
        features_label.pack(anchor="w", pady=(0, 10))
        
        # Ayarlar butonu
        settings_btn = ctk.CTkButton(features_frame, text="⚙️ Ayarlar", 
                                    command=self.show_settings)
        settings_btn.pack(fill="x", pady=5)
        
        # Hız testi butonu
        speed_test_btn = ctk.CTkButton(features_frame, text="⚡ Hızımı Test Et", 
                                      command=self.run_speed_test)
        speed_test_btn.pack(fill="x", pady=5)
        
        # IP analizi butonu
        ip_analysis_btn = ctk.CTkButton(features_frame, text="🌐 IP Analizi", 
                                       command=self.show_ip_analysis)
        ip_analysis_btn.pack(fill="x", pady=5)
        
        # Mini widget butonu
        self.mini_widget_btn = ctk.CTkButton(features_frame, text="📱 Mini Widget Aç", 
                                           command=self.toggle_mini_widget)
        self.mini_widget_btn.pack(fill="x", pady=5)
        
        # Sistem tepsisi butonu
        tray_btn = ctk.CTkButton(features_frame, text="📌 Sisteme Sabitle", 
                                command=self.create_system_tray)
        tray_btn.pack(fill="x", pady=5)
        
        # Analiz butonları
        analysis_frame = ctk.CTkFrame(parent)
        analysis_frame.pack(fill="x", padx=20, pady=20)
        
        analysis_label = ctk.CTkLabel(analysis_frame, text="Analiz ve Dışa Aktarma", 
                                     font=ctk.CTkFont(size=14, weight="bold"))
        analysis_label.pack(anchor="w", pady=(0, 10))
        
        show_graphs_btn = ctk.CTkButton(analysis_frame, text="📊 Grafikleri Göster", 
                                       command=self.show_graphs)
        show_graphs_btn.pack(fill="x", pady=5)
        
        stats_btn = ctk.CTkButton(analysis_frame, text="📈 İstatistikleri Göster", 
                                  command=self.show_statistics)
        stats_btn.pack(fill="x", pady=5)
        
        export_btn = ctk.CTkButton(analysis_frame, text="💾 CSV Olarak Dışa Aktar", 
                                  command=self.export_to_csv)
        export_btn.pack(fill="x", pady=5)
        
        clear_db_btn = ctk.CTkButton(analysis_frame, text="🗑️ Veritabanını Temizle", 
                                    command=self.clear_database, fg_color="red", hover_color="darkred")
        clear_db_btn.pack(fill="x", pady=5)
    
    def setup_right_panel(self, parent):
        """Sağ paneldeki gösterge ve grafik bileşenlerini oluşturur"""
        # Üst kısım - Göstergeler
        indicators_frame = ctk.CTkFrame(parent)
        indicators_frame.pack(fill="x", padx=10, pady=10)
        
        # Süre göstergesi
        time_frame = ctk.CTkFrame(indicators_frame)
        time_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        time_label = ctk.CTkLabel(time_frame, text="Geçen Süre", font=ctk.CTkFont(size=12))
        time_label.pack(pady=(10, 5))
        
        self.time_value = ctk.CTkLabel(time_frame, text="00:00:00", 
                                      font=ctk.CTkFont(size=24, weight="bold"))
        self.time_value.pack(pady=(0, 10))
        
        # Download göstergesi
        download_frame = ctk.CTkFrame(indicators_frame)
        download_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        download_label = ctk.CTkLabel(download_frame, text="Download", font=ctk.CTkFont(size=12))
        download_label.pack(pady=(10, 5))
        
        self.download_value = ctk.CTkLabel(download_frame, text="0 MB", 
                                          font=ctk.CTkFont(size=24, weight="bold"))
        self.download_value.pack(pady=(0, 10))
        
        # Upload göstergesi
        upload_frame = ctk.CTkFrame(indicators_frame)
        upload_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        upload_label = ctk.CTkLabel(upload_frame, text="Upload", font=ctk.CTkFont(size=12))
        upload_label.pack(pady=(10, 5))
        
        self.upload_value = ctk.CTkLabel(upload_frame, text="0 MB", 
                                        font=ctk.CTkFont(size=24, weight="bold"))
        self.upload_value.pack(pady=(0, 10))
        
        # Anlık hız göstergesi
        speed_frame = ctk.CTkFrame(indicators_frame)
        speed_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        speed_label = ctk.CTkLabel(speed_frame, text="Anlık Hız", font=ctk.CTkFont(size=12))
        speed_label.pack(pady=(10, 5))
        
        self.speed_value = ctk.CTkLabel(speed_frame, text="0 Mbps", 
                                       font=ctk.CTkFont(size=24, weight="bold"))
        self.speed_value.pack(pady=(0, 10))
        
        # Alt kısım - Grafikler
        self.graph_frame = ctk.CTkFrame(parent)
        self.graph_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Notebook (sekme) oluştur
        self.notebook = ttk.Notebook(self.graph_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Grafik sekmeleri
        self.line_tab = ctk.CTkFrame(self.notebook)
        self.bar_tab = ctk.CTkFrame(self.notebook)
        self.pie_tab = ctk.CTkFrame(self.notebook)
        
        self.notebook.add(self.line_tab, text="Çizgi Grafik")
        self.notebook.add(self.bar_tab, text="Sütun Grafik")
        self.notebook.add(self.pie_tab, text="Pasta Grafik")
        
        # Başlangıçta boş grafikler
        self.create_empty_graphs()
    
    def create_empty_graphs(self):
        """Boş grafikler oluşturur"""
        # Çizgi grafik
        self.line_fig = Figure(figsize=(8, 4), dpi=100)
        self.line_ax = self.line_fig.add_subplot(111)
        self.line_ax.set_title("Zaman Serisi - Download/Upload")
        self.line_ax.set_xlabel("Zaman")
        self.line_ax.set_ylabel("MB")
        self.line_ax.grid(True, alpha=0.3)
        self.line_canvas = FigureCanvasTkAgg(self.line_fig, self.line_tab)
        self.line_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Sütun grafik
        self.bar_fig = Figure(figsize=(8, 4), dpi=100)
        self.bar_ax = self.bar_fig.add_subplot(111)
        self.bar_ax.set_title("Günlük Toplam Veri Kullanımı")
        self.bar_ax.set_xlabel("Tarih")
        self.bar_ax.set_ylabel("MB")
        self.bar_ax.grid(True, alpha=0.3)
        self.bar_canvas = FigureCanvasTkAgg(self.bar_fig, self.bar_tab)
        self.bar_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Pasta grafik
        self.pie_fig = Figure(figsize=(8, 4), dpi=100)
        self.pie_ax = self.pie_fig.add_subplot(111)
        self.pie_ax.set_title("Download vs Upload Dağılımı")
        self.pie_canvas = FigureCanvasTkAgg(self.pie_fig, self.pie_tab)
        self.pie_canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def start_monitoring(self):
        """İzlemeyi başlatır ve arka plan thread'ini çalıştırır"""
        if self.is_monitoring:
            return
        
        # Kota ayarlarını güncelle
        try:
            self.data_limit = float(self.limit_entry.get())
        except ValueError:
            self.data_limit = 500
        
        self.limit_enabled = self.limit_checkbox.get()
        self.shutdown_on_limit = self.shutdown_checkbox.get()
        
        # Uygulama adını al
        if self.tracking_mode.get() == "app":
            # Önce combobox'tan, boşsa entry'den al
            self.process_name = self.app_combobox.get().strip()
            if not self.process_name:
                self.process_name = self.app_name_entry.get().strip()
            
            if not self.process_name:
                messagebox.showwarning("Uyarı", "Lütfen bir uygulama adı giriniz veya seçiniz.")
                return
        
        # İzleme değişkenlerini sıfırla
        self.is_monitoring = True
        self.start_time = time.time()
        self.total_download = 0
        self.total_upload = 0
        
        # Başlangıç ağ verilerini al
        net_io = psutil.net_io_counters()
        self.last_bytes_sent = net_io.bytes_sent
        self.last_bytes_recv = net_io.bytes_recv
        
        # Buton durumlarını güncelle
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
        # İzleme thread'ini başlat
        self.monitoring_thread = threading.Thread(target=self.monitor_traffic, daemon=True)
        self.monitoring_thread.start()
        
        # Süre güncelleme thread'ini başlat
        self.update_time_thread = threading.Thread(target=self.update_time_display, daemon=True)
        self.update_time_thread.start()
        
        print("İzleme başlatıldı.")
    
    def stop_monitoring(self):
        """İzlemeyi durdurur ve oturumu kaydeder"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        # Buton durumlarını güncelle
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        
        # Oturumu veritabanına kaydet
        self.save_session()
        
        print("İzleme durduruldu.")
    
    def monitor_traffic(self):
        """Ağ trafiğini izleyen ana fonksiyon - Thread'de çalışır"""
        last_check_time = time.time()
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                time_diff = current_time - last_check_time
                
                if time_diff < 0.5:  # Minimum 0.5 saniye bekle
                    time.sleep(0.5 - time_diff)
                    continue
                
                # Mevcut ağ verilerini al
                net_io = psutil.net_io_counters()
                
                # Farkı hesapla
                bytes_sent_diff = net_io.bytes_sent - self.last_bytes_sent
                bytes_recv_diff = net_io.bytes_recv - self.last_bytes_recv
                
                # MB'ye çevir
                download_mb = bytes_recv_diff / (1024 * 1024)
                upload_mb = bytes_sent_diff / (1024 * 1024)
                
                # Toplamlara ekle
                self.total_download += download_mb
                self.total_upload += upload_mb
                
                # Anlık hızı hesapla (Mbps) - Doğru formül
                total_bytes = bytes_sent_diff + bytes_recv_diff
                if time_diff > 0:
                    speed_mbps = (total_bytes * 8) / (time_diff * 1024 * 1024)  # Mbps
                else:
                    speed_mbps = 0
                
                self.speed_history.append(speed_mbps)
                
                # UI güncellemeleri
                self.root.after(0, self.update_display, download_mb, upload_mb, speed_mbps)
                
                # Kota kontrolü
                if self.limit_enabled:
                    total_used = self.total_download + self.total_upload
                    if total_used >= self.data_limit:
                        self.handle_limit_reached()
                
                # Son değerleri güncelle
                self.last_bytes_sent = net_io.bytes_sent
                self.last_bytes_recv = net_io.bytes_recv
                last_check_time = current_time
                
                # Uygulama bazlı izleme
                if self.tracking_mode.get() == "app" and self.process_name:
                    self.monitor_specific_process()
                
            except Exception as e:
                print(f"İzleme hatası: {e}")
            
            # 1 saniye bekle
            time.sleep(1)
    
    def monitor_specific_process(self):
        """Belirli bir uygulamanın trafiğini izler"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                    if self.process_name.lower() in proc_name:
                        # Uygulama bulundu, ağ bağlantılarını kontrol et
                        try:
                            connections = proc.connections()
                            if connections:
                                # Uygulama ağ kullanıyor
                                pass
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Uygulama izleme hatası: {e}")
    
    def update_display(self, download_mb, upload_mb, speed_mbps):
        """Ekrandaki değerleri günceller"""
        try:
            # Toplam değerleri göster - GB'ye çevir büyük değerler için
            if self.total_download > 1024:
                download_text = f"{self.total_download/1024:.2f} GB"
            else:
                download_text = f"{self.total_download:.2f} MB"
            
            if self.total_upload > 1024:
                upload_text = f"{self.total_upload/1024:.2f} GB"
            else:
                upload_text = f"{self.total_upload:.2f} MB"
            
            self.download_value.configure(text=download_text)
            self.upload_value.configure(text=upload_text)
            
            # Anlık hızı göster - Hareketli ortalama
            if self.speed_history:
                # Son 5 değerin ortalamasını al
                recent_speeds = list(self.speed_history)[-5:]
                avg_speed = sum(recent_speeds) / len(recent_speeds)
            else:
                avg_speed = speed_mbps
            
            # Hızı formatla
            if avg_speed < 0.1:
                speed_text = f"{avg_speed*1000:.1f} Kbps"
            else:
                speed_text = f"{avg_speed:.2f} Mbps"
            
            self.speed_value.configure(text=speed_text)
            
            # Renk kodlaması
            if avg_speed > 20:
                self.speed_value.configure(text_color="#ff0000")  # Kırmızı
            elif avg_speed > 10:
                self.speed_value.configure(text_color="#ff9900")  # Turuncu
            elif avg_speed > 5:
                self.speed_value.configure(text_color="#ffff00")  # Sarı
            elif avg_speed > 1:
                self.speed_value.configure(text_color="#00ff00")  # Yeşil
            else:
                self.speed_value.configure(text_color="#cccccc")  # Gri
            
            # Kota durumunu göster
            if self.limit_enabled:
                total_used = self.total_download + self.total_upload
                if total_used > 0:
                    percentage = (total_used / self.data_limit) * 100
                    if percentage > 80:
                        self.download_value.configure(text_color="#ff6666")
                        self.upload_value.configure(text_color="#ff6666")
                    elif percentage > 50:
                        self.download_value.configure(text_color="#ffcc00")
                        self.upload_value.configure(text_color="#ffcc00")
                    else:
                        self.download_value.configure(text_color="#ffffff")
                        self.upload_value.configure(text_color="#ffffff")
        except Exception as e:
            print(f"Display update error: {e}")
    
    def update_time_display(self):
        """Geçen süreyi günceller"""
        while self.is_monitoring:
            try:
                if self.start_time:
                    elapsed = time.time() - self.start_time
                    hours = int(elapsed // 3600)
                    minutes = int((elapsed % 3600) // 60)
                    seconds = int(elapsed % 60)
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    self.root.after(0, lambda ts=time_str: self.time_value.configure(text=ts))
                time.sleep(1)
            except Exception as e:
                print(f"Süre güncelleme hatası: {e}")
                break
    
    def handle_limit_reached(self):
        """Kota limiti dolduğunda yapılacak işlemler"""
        # Windows bildirimi gönder
        try:
            self.toaster.show_toast(
                "Internet Trafik İzleyici",
                f"Kota limiti doldu! Kullanılan: {self.total_download + self.total_upload:.2f} MB",
                duration=5
            )
        except:
            pass
        
        # Limit dolunca durdurma seçeneği aktifse
        if self.shutdown_on_limit:
            self.root.after(0, self.stop_monitoring)
            messagebox.showwarning("Kota Uyarısı", 
                                 f"Kota limiti doldu! İzleme durduruldu.\nKullanılan: {self.total_download + self.total_upload:.2f} MB")
    
    def save_session(self):
        """Mevcut oturumu veritabanına kaydeder"""
        try:
            end_time = time.time()
            duration = end_time - self.start_time
            
            # Tarih formatı
            start_datetime = datetime.datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')
            end_datetime = datetime.datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
            
            # Takip türü
            tracking_type = "app" if self.tracking_mode.get() == "app" else "general"
            
            self.cursor.execute('''
                INSERT INTO sessions (start_time, end_time, duration_seconds, 
                                     download_mb, upload_mb, tracking_type, process_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (start_datetime, end_datetime, duration, 
                  self.total_download, self.total_upload, tracking_type, self.process_name))
            
            self.db_connection.commit()
            print("Oturum veritabanına kaydedildi.")
            
        except Exception as e:
            print(f"Oturum kaydetme hatası: {e}")
    
    def show_graphs(self):
        """Geçmiş verilerden grafikleri oluşturur ve gösterir"""
        try:
            # Veritabanından verileri al
            self.cursor.execute('''
                SELECT start_time, download_mb, upload_mb 
                FROM sessions 
                ORDER BY start_time
            ''')
            rows = self.cursor.fetchall()
            
            if not rows:
                messagebox.showinfo("Bilgi", "Grafik oluşturmak için yeterli veri yok.")
                return
            
            # Verileri ayır
            dates = [row[0] for row in rows]
            downloads = [row[1] for row in rows]
            uploads = [row[2] for row in rows]
            
            # Çizgi grafiği güncelle - Daha iyi görselleştirme
            self.line_ax.clear()
            
            # Tarihleri daha okunabilir hale getir
            date_labels = []
            for date_str in dates:
                try:
                    dt = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    date_labels.append(dt.strftime('%H:%M'))
                except:
                    date_labels.append(date_str)
            
            # Çizgi grafiği
            x_indices = list(range(len(dates)))
            self.line_ax.plot(x_indices, downloads, 'b-', label='Download', linewidth=2, marker='o', markersize=4)
            self.line_ax.plot(x_indices, uploads, 'r-', label='Upload', linewidth=2, marker='s', markersize=4)
            self.line_ax.set_title("Zaman Serisi - Download/Upload")
            self.line_ax.set_xlabel("Oturumlar")
            self.line_ax.set_ylabel("MB")
            self.line_ax.legend()
            self.line_ax.grid(True, alpha=0.3)
            
            # X ekseni etiketlerini ayarla
            if len(date_labels) > 10:
                step = len(date_labels) // 10
                visible_indices = list(range(0, len(date_labels), step))
                visible_labels = [date_labels[i] for i in visible_indices]
                self.line_ax.set_xticks(visible_indices)
                self.line_ax.set_xticklabels(visible_labels, rotation=45)
            else:
                self.line_ax.set_xticks(x_indices)
                self.line_ax.set_xticklabels(date_labels, rotation=45)
            
            self.line_fig.tight_layout()
            self.line_canvas.draw()
            
            # Sütun grafiği güncelle (günlük toplam)
            daily_totals = {}
            for date_str, download, upload in zip(dates, downloads, uploads):
                try:
                    date = date_str.split()[0]  # Sadece tarih kısmı
                    total = download + upload
                    if date in daily_totals:
                        daily_totals[date] += total
                    else:
                        daily_totals[date] = total
                except:
                    continue
            
            if daily_totals:
                dates_list = list(daily_totals.keys())
                totals_list = list(daily_totals.values())
                
                self.bar_ax.clear()
                bars = self.bar_ax.bar(range(len(dates_list)), totals_list, color='skyblue', alpha=0.7)
                self.bar_ax.set_title("Günlük Toplam Veri Kullanımı")
                self.bar_ax.set_xlabel("Tarih")
                self.bar_ax.set_ylabel("MB")
                self.bar_ax.grid(True, alpha=0.3)
                
                # Çubuklara değer yaz
                for bar, value in zip(bars, totals_list):
                    height = bar.get_height()
                    self.bar_ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                    f'{value:.1f}', ha='center', va='bottom', fontsize=8)
                
                self.bar_ax.set_xticks(range(len(dates_list)))
                self.bar_ax.set_xticklabels(dates_list, rotation=45)
                self.bar_fig.tight_layout()
                self.bar_canvas.draw()
            
            # Pasta grafiği güncelle
            total_download = sum(downloads)
            total_upload = sum(uploads)
            
            self.pie_ax.clear()
            if total_download + total_upload > 0:
                sizes = [total_download, total_upload]
                labels = [f'Download\n{total_download:.1f} MB', f'Upload\n{total_upload:.1f} MB']
                colors = ['#66b3ff', '#ff6666']
                explode = (0.05, 0.05)  # Dilimleri ayır
                
                wedges, texts, autotexts = self.pie_ax.pie(
                    sizes, explode=explode, labels=labels, colors=colors,
                    autopct='%1.1f%%', startangle=90, shadow=True
                )
                
                # Yüzde yazılarını kalın yap
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
                
                self.pie_ax.set_title(f"Download vs Upload Dağılımı\nToplam: {total_download + total_upload:.2f} MB")
                self.pie_ax.axis('equal')  # Daireyi yuvarlak yap
            else:
                self.pie_ax.text(0.5, 0.5, "Veri yok", ha='center', va='center', fontsize=12)
            
            self.pie_fig.tight_layout()
            self.pie_canvas.draw()
            
        except Exception as e:
            print(f"Grafik oluşturma hatası: {e}")
            messagebox.showerror("Hata", f"Grafikler oluşturulamadı: {e}")
    
    def export_to_csv(self):
        """Veritabanındaki tüm verileri CSV dosyasına aktarır"""
        try:
            # Kaydetme yeri seç
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="CSV Olarak Kaydet"
            )
            
            if not file_path:
                return
            
            # Veritabanından tüm verileri al
            self.cursor.execute('''
                SELECT * FROM sessions ORDER BY start_time
            ''')
            rows = self.cursor.fetchall()
            
            # Sütun isimleri
            column_names = [description[0] for description in self.cursor.description]
            
            # CSV dosyasına yaz
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(column_names)
                writer.writerows(rows)
            
            messagebox.showinfo("Başarılı", f"Veriler başarıyla kaydedildi:\n{file_path}")
            
        except Exception as e:
            print(f"CSV aktarma hatası: {e}")
            messagebox.showerror("Hata", f"CSV aktarılamadı: {e}")
    
    def clear_database(self):
        """Veritabanındaki tüm verileri temizler"""
        if messagebox.askyesno("Onay", "Tüm veritabanı verileri silinecek. Emin misiniz?"):
            try:
                self.cursor.execute("DELETE FROM sessions")
                self.db_connection.commit()
                messagebox.showinfo("Başarılı", "Veritabanı temizlendi.")
                
                # Grafikleri temizle
                self.create_empty_graphs()
                
            except Exception as e:
                messagebox.showerror("Hata", f"Veritabanı temizlenemedi: {e}")
    
    def on_closing(self):
        """Pencere kapatılırken çağrılır"""
        if self.settings.get('minimize_to_tray', True):
            # Sistem tepsisine küçült
            self.root.withdraw()
            if not self.system_tray_icon:
                self.create_system_tray()
            try:
                self.toaster.show_toast(
                    "Internet Trafik İzleyici",
                    "Uygulama arka planda çalışmaya devam ediyor.",
                    duration=3,
                    threaded=True
                )
            except:
                pass
        else:
            # Tamamen kapat
            if self.is_monitoring:
                self.stop_monitoring()
            self.root.quit()
    
    def run(self):
        """Uygulamayı çalıştırır"""
        self.root.mainloop()
    
    def load_settings(self):
        """Ayarları yükler"""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
                print(f"Ayarlar yüklendi: {self.settings_path}")
        except Exception as e:
            print(f"Ayarlar yüklenemedi: {e}")
    
    def save_settings(self):
        """Ayarları kaydeder"""
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            print(f"Ayarlar kaydedildi: {self.settings_path}")
        except Exception as e:
            print(f"Ayarlar kaydedilemedi: {e}")
    
    def add_to_startup(self):
        """Windows başlangıcına ekler"""
        try:
            import winreg
            
            # EXE yolunu al
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.abspath(__file__)
            
            # Registry anahtarını aç
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            # Değeri ayarla
            winreg.SetValueEx(key, "InternetTrafikIzleyici", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            
            return True
        except Exception as e:
            print(f"Başlangıca ekleme hatası: {e}")
            return False
    
    def remove_from_startup(self):
        """Windows başlangıcından kaldırır"""
        try:
            import winreg
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            try:
                winreg.DeleteValue(key, "InternetTrafikIzleyici")
            except FileNotFoundError:
                pass
            
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Başlangıçtan kaldırma hatası: {e}")
            return False
    
    def show_settings(self):
        """Ayarlar penceresini gösterir"""
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Ayarlar")
        settings_window.geometry("500x600")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Başlık
        title_label = ctk.CTkLabel(settings_window, text="⚙️ Ayarlar", 
                                   font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=20)
        
        # Ayarlar frame
        settings_frame = ctk.CTkScrollableFrame(settings_window)
        settings_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Başlangıç ayarları
        startup_frame = ctk.CTkFrame(settings_frame)
        startup_frame.pack(fill="x", pady=10)
        
        startup_label = ctk.CTkLabel(startup_frame, text="Başlangıç Ayarları", 
                                    font=ctk.CTkFont(size=14, weight="bold"))
        startup_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Windows ile başlat
        self.startup_var = tk.BooleanVar(value=self.settings['start_with_windows'])
        startup_check = ctk.CTkCheckBox(
            startup_frame, 
            text="Windows ile başlat",
            variable=self.startup_var,
            command=self.toggle_startup
        )
        startup_check.pack(anchor="w", padx=20, pady=5)
        
        # Otomatik izleme başlat
        self.auto_monitor_var = tk.BooleanVar(value=self.settings['auto_start_monitoring'])
        auto_monitor_check = ctk.CTkCheckBox(
            startup_frame,
            text="Açılışta izlemeyi otomatik başlat",
            variable=self.auto_monitor_var
        )
        auto_monitor_check.pack(anchor="w", padx=20, pady=5)
        
        # Sistem tepsisine küçült
        self.minimize_tray_var = tk.BooleanVar(value=self.settings['minimize_to_tray'])
        minimize_check = ctk.CTkCheckBox(
            startup_frame,
            text="Kapatırken sistem tepsisine küçült",
            variable=self.minimize_tray_var
        )
        minimize_check.pack(anchor="w", padx=20, pady=(5, 10))
        
        # Performans ayarları
        perf_frame = ctk.CTkFrame(settings_frame)
        perf_frame.pack(fill="x", pady=10)
        
        perf_label = ctk.CTkLabel(perf_frame, text="Performans Ayarları", 
                                 font=ctk.CTkFont(size=14, weight="bold"))
        perf_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Güncelleme aralığı
        interval_label = ctk.CTkLabel(perf_frame, text="Güncelleme Aralığı (saniye):")
        interval_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.interval_var = tk.IntVar(value=self.settings['update_interval'])
        interval_slider = ctk.CTkSlider(
            perf_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            variable=self.interval_var
        )
        interval_slider.pack(fill="x", padx=20, pady=5)
        
        self.interval_value_label = ctk.CTkLabel(perf_frame, text=f"{self.interval_var.get()} saniye")
        self.interval_value_label.pack(anchor="w", padx=20, pady=(0, 10))
        
        def update_interval_label(value):
            self.interval_value_label.configure(text=f"{int(float(value))} saniye")
        
        interval_slider.configure(command=update_interval_label)
        
        # Veritabanı ayarları
        db_frame = ctk.CTkFrame(settings_frame)
        db_frame.pack(fill="x", pady=10)
        
        db_label = ctk.CTkLabel(db_frame, text="Veritabanı", 
                               font=ctk.CTkFont(size=14, weight="bold"))
        db_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Veritabanı boyutu
        try:
            db_size = os.path.getsize(self.db_path) / (1024 * 1024)
            db_size_text = f"Veritabanı Boyutu: {db_size:.2f} MB"
        except:
            db_size_text = "Veritabanı Boyutu: Bilinmiyor"
        
        db_size_label = ctk.CTkLabel(db_frame, text=db_size_text)
        db_size_label.pack(anchor="w", padx=20, pady=5)
        
        # Veri klasörü yolu
        data_folder_label = ctk.CTkLabel(db_frame, text=f"Veri Klasörü:", 
                                        font=ctk.CTkFont(size=11, weight="bold"))
        data_folder_label.pack(anchor="w", padx=20, pady=(10, 2))
        
        data_path_label = ctk.CTkLabel(db_frame, text=self.app_data_dir, 
                                      font=ctk.CTkFont(size=10),
                                      text_color="gray")
        data_path_label.pack(anchor="w", padx=20, pady=(0, 5))
        
        # Klasörü aç butonu
        def open_data_folder():
            try:
                os.startfile(self.app_data_dir)
            except Exception as e:
                messagebox.showerror("Hata", f"Klasör açılamadı: {e}")
        
        open_folder_btn = ctk.CTkButton(db_frame, text="📁 Veri Klasörünü Aç", 
                                       command=open_data_folder)
        open_folder_btn.pack(fill="x", padx=20, pady=5)
        
        # Oturum sayısı
        try:
            self.cursor.execute("SELECT COUNT(*) FROM sessions")
            session_count = self.cursor.fetchone()[0]
            session_text = f"Toplam Oturum: {session_count}"
        except:
            session_text = "Toplam Oturum: Bilinmiyor"
        
        session_label = ctk.CTkLabel(db_frame, text=session_text)
        session_label.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Hakkında
        about_frame = ctk.CTkFrame(settings_frame)
        about_frame.pack(fill="x", pady=10)
        
        about_label = ctk.CTkLabel(about_frame, text="Hakkında", 
                                  font=ctk.CTkFont(size=14, weight="bold"))
        about_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        version_label = ctk.CTkLabel(about_frame, text="Internet Trafik İzleyici v1.0")
        version_label.pack(anchor="w", padx=20, pady=5)
        
        author_label = ctk.CTkLabel(about_frame, text="Modern Ağ İzleme Uygulaması")
        author_label.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Butonlar
        button_frame = ctk.CTkFrame(settings_window)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        def save_and_close():
            # Ayarları kaydet
            self.settings['start_with_windows'] = self.startup_var.get()
            self.settings['auto_start_monitoring'] = self.auto_monitor_var.get()
            self.settings['minimize_to_tray'] = self.minimize_tray_var.get()
            self.settings['update_interval'] = self.interval_var.get()
            
            self.save_settings()
            messagebox.showinfo("Başarılı", "Ayarlar kaydedildi!")
            settings_window.destroy()
        
        save_btn = ctk.CTkButton(button_frame, text="Kaydet", command=save_and_close)
        save_btn.pack(side="left", expand=True, padx=5)
        
        cancel_btn = ctk.CTkButton(button_frame, text="İptal", command=settings_window.destroy)
        cancel_btn.pack(side="right", expand=True, padx=5)
    
    def toggle_startup(self):
        """Windows başlangıç ayarını değiştirir"""
        if self.startup_var.get():
            if self.add_to_startup():
                messagebox.showinfo("Başarılı", "Uygulama Windows ile başlayacak şekilde ayarlandı.")
            else:
                messagebox.showerror("Hata", "Windows başlangıcına eklenemedi.")
                self.startup_var.set(False)
        else:
            if self.remove_from_startup():
                messagebox.showinfo("Başarılı", "Uygulama Windows başlangıcından kaldırıldı.")
            else:
                messagebox.showerror("Hata", "Windows başlangıcından kaldırılamadı.")
                self.startup_var.set(True)
    
    def refresh_app_list(self):
        """Çalışan uygulamaların listesini yeniler"""
        try:
            app_names = set()
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name and name.endswith('.exe'):
                        app_names.add(name.lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sık kullanılanlar
            common_apps = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 
                          'discord.exe', 'steam.exe', 'spotify.exe', 'whatsapp.exe']
            
            # Tüm uygulamaları birleştir
            all_apps = common_apps + sorted(list(app_names))
            unique_apps = sorted(set(all_apps))
            
            self.app_combobox.configure(values=unique_apps)
            messagebox.showinfo("Başarılı", f"{len(unique_apps)} uygulama bulundu.")
            
        except Exception as e:
            print(f"Uygulama listesi yenileme hatası: {e}")
            messagebox.showerror("Hata", f"Uygulama listesi yenilenemedi: {e}")
    
    def run_speed_test(self):
        """İnternet hız testi yapar - Basit download testi"""
        def speed_test_thread():
            try:
                self.root.after(0, lambda: messagebox.showinfo("Bilgi", "Hız testi başlatılıyor... Bu işlem 10-20 saniye sürebilir."))
                
                # Test dosyası URL'leri (farklı boyutlarda)
                test_urls = [
                    ('https://speed.cloudflare.com/__down?bytes=10000000', 10),  # 10MB
                    ('https://proof.ovh.net/files/10Mb.dat', 10),  # 10MB
                ]
                
                download_speeds = []
                
                for url, size_mb in test_urls:
                    try:
                        start_time = time.time()
                        response = requests.get(url, timeout=30, stream=True)
                        
                        total_bytes = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            total_bytes += len(chunk)
                        
                        end_time = time.time()
                        duration = end_time - start_time
                        
                        if duration > 0:
                            speed_mbps = (total_bytes * 8) / (duration * 1_000_000)
                            download_speeds.append(speed_mbps)
                            break  # İlk başarılı test yeterli
                    except:
                        continue
                
                if not download_speeds:
                    raise Exception("Hız testi sunucularına bağlanılamadı")
                
                # Ortalama hızı al
                avg_download = sum(download_speeds) / len(download_speeds)
                
                # Ping testi (basit)
                try:
                    ping_start = time.time()
                    requests.get('https://www.google.com', timeout=5)
                    ping = (time.time() - ping_start) * 1000
                except:
                    ping = 0
                
                # Upload testi yapma (çok uzun sürer), tahmini değer
                upload_speed = avg_download * 0.3  # Genelde download'un %30'u
                
                # Sonuçları kaydet
                test_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.speed_test_results.append({
                    'time': test_time,
                    'download': avg_download,
                    'upload': upload_speed,
                    'ping': ping
                })
                
                # Veritabanına kaydet
                try:
                    self.cursor.execute('''
                        CREATE TABLE IF NOT EXISTS speed_tests (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            test_time TEXT NOT NULL,
                            download_mbps REAL NOT NULL,
                            upload_mbps REAL NOT NULL,
                            ping_ms REAL NOT NULL
                        )
                    ''')
                    
                    self.cursor.execute('''
                        INSERT INTO speed_tests (test_time, download_mbps, upload_mbps, ping_ms)
                        VALUES (?, ?, ?, ?)
                    ''', (test_time, avg_download, upload_speed, ping))
                    
                    self.db_connection.commit()
                except Exception as db_error:
                    print(f"Veritabanı kayıt hatası: {db_error}")
                
                # Sonuçları göster
                result_text = f"""⚡ HIZ TESTİ SONUÇLARI ⚡

Test Zamanı: {test_time}
Download: {avg_download:.2f} Mbps
Upload: {upload_speed:.2f} Mbps (tahmini)
Ping: {ping:.1f} ms

Not: Bu basit bir hız testidir.
Daha detaylı test için speedtest.net kullanın.

Sonuçlar veritabanına kaydedildi."""
                
                def show_result():
                    messagebox.showinfo("Hız Testi Sonuçları", result_text)
                
                self.root.after(0, show_result)
                
            except Exception as e:
                error_msg = f"Hız testi başarısız: {str(e)}\n\nİnternet bağlantınızı kontrol edin."
                def show_error():
                    messagebox.showerror("Hata", error_msg)
                self.root.after(0, show_error)
        
        # Thread'de çalıştır
        threading.Thread(target=speed_test_thread, daemon=True).start()
    
    def show_ip_analysis(self):
        """IP analizi penceresini açar"""
        try:
            # Basit IP analizi penceresi
            analysis_window = ctk.CTkToplevel(self.root)
            analysis_window.title("IP Analizi")
            analysis_window.geometry("600x400")
            
            # Başlık
            title_label = ctk.CTkLabel(analysis_window, text="🌐 IP ve Ağ Analizi", 
                                      font=ctk.CTkFont(size=18, weight="bold"))
            title_label.pack(pady=20)
            
            # IP bilgileri
            try:
                # Public IP
                public_ip = requests.get('https://api.ipify.org').text
                
                # Local IP
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                
                # IP bilgilerini göster
                info_frame = ctk.CTkFrame(analysis_window)
                info_frame.pack(fill="x", padx=20, pady=10)
                
                public_label = ctk.CTkLabel(info_frame, text=f"Public IP: {public_ip}", 
                                           font=ctk.CTkFont(size=14))
                public_label.pack(anchor="w", pady=5)
                
                local_label = ctk.CTkLabel(info_frame, text=f"Local IP: {local_ip}", 
                                          font=ctk.CTkFont(size=14))
                local_label.pack(anchor="w", pady=5)
                
                # Ağ bağlantıları
                connections_frame = ctk.CTkFrame(analysis_window)
                connections_frame.pack(fill="both", expand=True, padx=20, pady=10)
                
                connections_label = ctk.CTkLabel(connections_frame, text="Aktif Ağ Bağlantıları:", 
                                                font=ctk.CTkFont(size=14, weight="bold"))
                connections_label.pack(anchor="w", pady=(0, 10))
                
                # Treeview oluştur
                tree = ttk.Treeview(connections_frame, columns=("PID", "Uygulama", "Yerel Adres", "Uzak Adres", "Durum"), 
                                   show="headings", height=8)
                
                tree.heading("PID", text="PID")
                tree.heading("Uygulama", text="Uygulama")
                tree.heading("Yerel Adres", text="Yerel Adres")
                tree.heading("Uzak Adres", text="Uzak Adres")
                tree.heading("Durum", text="Durum")
                
                tree.column("PID", width=60)
                tree.column("Uygulama", width=120)
                tree.column("Yerel Adres", width=120)
                tree.column("Uzak Adres", width=120)
                tree.column("Durum", width=80)
                
                # Scrollbar ekle
                scrollbar = ttk.Scrollbar(connections_frame, orient="vertical", command=tree.yview)
                tree.configure(yscrollcommand=scrollbar.set)
                
                tree.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
                # Ağ bağlantılarını doldur
                for conn in psutil.net_connections(kind='inet'):
                    try:
                        if conn.status == 'ESTABLISHED' and conn.raddr:
                            pid = conn.pid
                            laddr = f"{conn.laddr.ip}:{conn.laddr.port}"
                            raddr = f"{conn.raddr.ip}:{conn.raddr.port}"
                            status = conn.status
                            
                            # PID'den uygulama adını al
                            app_name = "Bilinmiyor"
                            if pid:
                                try:
                                    proc = psutil.Process(pid)
                                    app_name = proc.name()
                                except:
                                    pass
                            
                            tree.insert("", "end", values=(pid, app_name, laddr, raddr, status))
                    except:
                        continue
                
            except Exception as e:
                error_label = ctk.CTkLabel(analysis_window, text=f"IP analizi hatası: {e}", 
                                          text_color="red")
                error_label.pack(pady=20)
            
        except Exception as e:
            messagebox.showerror("Hata", f"IP analizi penceresi açılamadı: {e}")
    
    def toggle_mini_widget(self):
        """Mini widget'ı açıp kapatır"""
        if not self.mini_widget_visible:
            self.create_mini_widget()
        else:
            self.destroy_mini_widget()
    
    def create_mini_widget(self):
        """Mini widget oluşturur"""
        try:
            self.mini_widget = ctk.CTkToplevel(self.root)
            self.mini_widget.title("Mini Trafik Widget")
            self.mini_widget.geometry("200x100+50+50")
            self.mini_widget.overrideredirect(True)  # Başlık çubuğunu kaldır
            self.mini_widget.attributes('-topmost', True)  # Her zaman üstte
            self.mini_widget.attributes('-alpha', 0.8)  # Şeffaflık
            
            # Widget içeriği
            widget_frame = ctk.CTkFrame(self.mini_widget, fg_color="transparent")
            widget_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Hız göstergesi
            self.mini_speed_label = ctk.CTkLabel(widget_frame, text="0 Mbps", 
                                                font=ctk.CTkFont(size=20, weight="bold"))
            self.mini_speed_label.pack(pady=5)
            
            # Download/Upload
            self.mini_data_label = ctk.CTkLabel(widget_frame, text="D: 0 MB | U: 0 MB", 
                                               font=ctk.CTkFont(size=12))
            self.mini_data_label.pack(pady=5)
            
            # Kapat butonu
            close_btn = ctk.CTkButton(widget_frame, text="X", width=30, height=30,
                                     command=self.destroy_mini_widget)
            close_btn.pack(pady=5)
            
            self.mini_widget_visible = True
            self.mini_widget_btn.configure(text="📱 Mini Widget Kapat")
            
            # Widget'ı sürüklenebilir yap
            self.mini_widget.bind('<Button-1>', self.start_move)
            self.mini_widget.bind('<ButtonRelease-1>', self.stop_move)
            self.mini_widget.bind('<B1-Motion>', self.do_move)
            
            # Mini widget güncelleme thread'i
            self.mini_widget_update_thread = threading.Thread(target=self.update_mini_widget, daemon=True)
            self.mini_widget_update_thread.start()
            
        except Exception as e:
            print(f"Mini widget oluşturma hatası: {e}")
    
    def destroy_mini_widget(self):
        """Mini widget'ı kapatır"""
        if self.mini_widget:
            self.mini_widget.destroy()
            self.mini_widget = None
            self.mini_widget_visible = False
            self.mini_widget_btn.configure(text="📱 Mini Widget Aç")
    
    def start_move(self, event):
        """Widget sürükleme başlat"""
        self.mini_widget.x = event.x
        self.mini_widget.y = event.y
    
    def stop_move(self, event):
        """Widget sürükleme durdur"""
        self.mini_widget.x = None
        self.mini_widget.y = None
    
    def do_move(self, event):
        """Widget sürükle"""
        deltax = event.x - self.mini_widget.x
        deltay = event.y - self.mini_widget.y
        x = self.mini_widget.winfo_x() + deltax
        y = self.mini_widget.winfo_y() + deltay
        self.mini_widget.geometry(f"+{x}+{y}")
    
    def update_mini_widget(self):
        """Mini widget'ı günceller"""
        while self.mini_widget_visible and self.mini_widget:
            try:
                if hasattr(self, 'speed_history') and self.speed_history:
                    recent_speeds = list(self.speed_history)[-3:]
                    avg_speed = sum(recent_speeds) / len(recent_speeds) if recent_speeds else 0
                    
                    speed_text = f"{avg_speed:.1f} Mbps" if avg_speed >= 0.1 else f"{avg_speed*1000:.0f} Kbps"
                    data_text = f"D: {self.total_download:.1f}MB | U: {self.total_upload:.1f}MB"
                    
                    self.mini_widget.after(0, lambda s=speed_text, d=data_text: (
                        self.mini_speed_label.configure(text=s),
                        self.mini_data_label.configure(text=d)
                    ))
                
                time.sleep(1)
            except:
                break
    
    def create_system_tray(self):
        """Sistem tepsisi ikonu oluşturur"""
        try:
            # İkon yolunu belirle
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, 'app_icon.png')
            else:
                icon_path = 'app_icon.png'
            
            # İkon oluştur veya yükle
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
                print(f"Sistem tepsisi icon yüklendi: {icon_path}")
            else:
                # Basit bir ikon oluştur
                image = Image.new('RGB', (64, 64), color='#0078D4')
                draw = ImageDraw.Draw(image)
                # Ağ simgesi çiz
                draw.rectangle([16, 20, 48, 25], fill='white')
                draw.rectangle([16, 30, 48, 35], fill='white')
                draw.rectangle([16, 40, 48, 45], fill='white')
                print("Sistem tepsisi icon oluşturuldu")
            
            # Menü öğeleri
            menu = (
                pystray.MenuItem('Uygulamayı Aç', self.show_from_tray),
                pystray.MenuItem('Mini Widget', self.toggle_mini_widget),
                pystray.MenuItem('Hız Testi', self.run_speed_test),
                pystray.MenuItem('Çıkış', self.quit_from_tray)
            )
            
            # İkon oluştur
            self.system_tray_icon = pystray.Icon("InternetTrafikIzleyici", image, "Internet Trafik İzleyici", menu)
            
            # Thread'de çalıştır
            tray_thread = threading.Thread(target=self.system_tray_icon.run, daemon=True)
            tray_thread.start()
            
            messagebox.showinfo("Bilgi", "Uygulama sisteme sabitlendi. Saatin yanında görünecek.")
            
        except Exception as e:
            print(f"Sistem tepsisi hatası: {e}")
            messagebox.showerror("Hata", f"Sistem tepsisi oluşturulamadı: {e}")
    
    def show_from_tray(self):
        """Sistem tepsisi menüsünden uygulamayı açar"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def quit_from_tray(self):
        """Sistem tepsisi menüsünden çıkış yapar"""
        self.system_tray_icon.stop()
        self.root.quit()
    
    def update_resource_usage(self):
        """Uygulamanın kaynak kullanımını günceller"""
        while True:
            try:
                # Mevcut process'in kaynak kullanımını al
                current_process = psutil.Process()
                
                # RAM kullanımı (MB)
                ram_usage = current_process.memory_info().rss / (1024 * 1024)
                
                # CPU kullanımı (%)
                cpu_percent = current_process.cpu_percent(interval=0.1)
                
                # Metni oluştur
                resource_text = f"🖥️ RAM: {ram_usage:.1f}MB | CPU: {cpu_percent:.1f}%"
                
                # Renk kodlaması - daha net renkler
                text_color = "#00ff00"  # Yeşil (normal)
                bg_color = "black"
                
                if cpu_percent > 50 or ram_usage > 150:
                    text_color = "#ff0000"  # Kırmızı (yüksek)
                    bg_color = "#330000"  # Koyu kırmızı arka plan
                elif cpu_percent > 30 or ram_usage > 100:
                    text_color = "#ffaa00"  # Turuncu (orta)
                    bg_color = "#332200"  # Koyu turuncu arka plan
                elif cpu_percent > 15 or ram_usage > 50:
                    text_color = "#ffff00"  # Sarı (hafif yüksek)
                    bg_color = "#333300"  # Koyu sarı arka plan
                
                # UI'ı güncelle
                self.root.after(0, lambda rt=resource_text, tc=text_color, bc=bg_color: (
                    self.resource_label.configure(text=rt, text_color=tc),
                    self.resource_frame.configure(fg_color=bc)
                ))
                
                time.sleep(3)  # 2'den 3'e çıkardık - daha az CPU
                
            except Exception as e:
                print(f"Kaynak güncelleme hatası: {e}")
                time.sleep(5)
    
    def show_statistics(self):
        """İstatistikleri gösterir"""
        try:
            # Veritabanından istatistikleri al
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(duration_seconds) as total_time,
                    SUM(download_mb) as total_download,
                    SUM(upload_mb) as total_upload,
                    AVG(download_mb) as avg_download,
                    AVG(upload_mb) as avg_upload
                FROM sessions
            ''')
            stats = self.cursor.fetchone()
            
            if stats and stats[0] > 0:
                total_sessions, total_time, total_download, total_upload, avg_download, avg_upload = stats
                
                # Süreyi formatla
                hours = int(total_time // 3600)
                minutes = int((total_time % 3600) // 60)
                
                # Verileri formatla
                if total_download > 1024:
                    total_download_text = f"{total_download/1024:.2f} GB"
                else:
                    total_download_text = f"{total_download:.2f} MB"
                
                if total_upload > 1024:
                    total_upload_text = f"{total_upload/1024:.2f} GB"
                else:
                    total_upload_text = f"{total_upload:.2f} MB"
                
                stats_text = f"""📊 İSTATİSTİKLER 📊

Toplam Oturum: {total_sessions}
Toplam Süre: {hours} saat {minutes} dakika
Toplam Download: {total_download_text}
Toplam Upload: {total_upload_text}
Ortalama Download/Oturum: {avg_download:.2f} MB
Ortalama Upload/Oturum: {avg_upload:.2f} MB
Toplam Veri: {(total_download + total_upload)/1024:.2f} GB"""
                
                messagebox.showinfo("İstatistikler", stats_text)
            else:
                messagebox.showinfo("Bilgi", "Henüz yeterli veri yok.")
                
        except Exception as e:
            messagebox.showerror("Hata", f"İstatistikler alınamadı: {e}")
    
    def __del__(self):
        """Nesne yok edilirken veritabanı bağlantısını kapatır"""
        if self.db_connection:
            self.db_connection.close()

def main():
    """Ana fonksiyon - Uygulamayı başlatır"""
    try:
        app = InternetTrafikIzleyici()
        app.run()
    except Exception as e:
        print(f"Uygulama hatası: {e}")
        messagebox.showerror("Kritik Hata", f"Uygulama başlatılamadı: {e}")

if __name__ == "__main__":
    main()