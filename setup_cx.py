#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cx_Freeze Setup - Internet Trafik İzleyici
Daha stabil EXE oluşturur
"""

import sys
from cx_Freeze import setup, Executable

# Dahil edilecek dosyalar
include_files = [
    ('app_icon.ico', 'app_icon.ico'),
]

# Dahil edilecek paketler
packages = [
    'customtkinter',
    'tkinter',
    'psutil',
    'sqlite3',
    'matplotlib',
    'PIL',
    'pystray',
    'win10toast',
    'requests',
    'json',
    'csv',
    'datetime',
    'threading',
    'time',
    'collections',
    'os',
    'sys'
]

# Build options
build_exe_options = {
    "packages": packages,
    "include_files": include_files,
    "excludes": [],
    "optimize": 2,
}

# Base için GUI uygulaması
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="Internet Trafik İzleyici",
    version="1.0",
    description="Modern Internet Trafik İzleme Uygulaması",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "internet_trafik_izleyici.py",
            base=base,
            icon="app_icon.ico",
            target_name="InternetTrafikIzleyici.exe"
        )
    ]
)
