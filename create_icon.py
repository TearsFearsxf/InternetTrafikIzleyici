#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Icon oluşturucu - Internet Trafik İzleyici için
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_app_icon():
    """Uygulama ikonu oluşturur"""
    # 256x256 boyutunda icon
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Gradient arka plan (mavi tonları)
    for i in range(size):
        color = (0, int(100 + (i/size)*155), int(200 + (i/size)*55), 255)
        draw.rectangle([0, i, size, i+1], fill=color)
    
    # Dış çerçeve (beyaz)
    draw.rounded_rectangle([10, 10, size-10, size-10], radius=30, outline='white', width=8)
    
    # İç çerçeve (koyu mavi)
    draw.rounded_rectangle([20, 20, size-20, size-20], radius=25, outline='#001f3f', width=4)
    
    # Ağ simgesi çiz (üç yatay çizgi - download/upload göstergesi)
    bar_width = 160
    bar_height = 25
    bar_spacing = 15
    start_x = (size - bar_width) // 2
    start_y = 60
    
    # Download ok (yeşil)
    draw.polygon([
        (size//2, start_y + 20),
        (size//2 - 25, start_y - 10),
        (size//2 + 25, start_y - 10)
    ], fill='#00ff00')
    
    # Çubuklar
    colors = ['#00ff00', '#ffff00', '#ff6600']
    for i, color in enumerate(colors):
        y = start_y + 40 + i * (bar_height + bar_spacing)
        # Çubuk
        draw.rounded_rectangle(
            [start_x, y, start_x + bar_width, y + bar_height],
            radius=12,
            fill=color
        )
        # Gölge efekti
        draw.rounded_rectangle(
            [start_x + 3, y + 3, start_x + bar_width + 3, y + bar_height + 3],
            radius=12,
            fill=(0, 0, 0, 50)
        )
    
    # Upload ok (kırmızı)
    upload_y = start_y + 40 + 3 * (bar_height + bar_spacing)
    draw.polygon([
        (size//2, upload_y),
        (size//2 - 25, upload_y + 30),
        (size//2 + 25, upload_y + 30)
    ], fill='#ff0000')
    
    # Metin ekle
    try:
        # Font boyutu
        font_size = 24
        # Basit metin çiz
        text = "NET"
        text_bbox = draw.textbbox((0, 0), text)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (size - text_width) // 2
        text_y = size - 50
        
        # Gölge
        draw.text((text_x + 2, text_y + 2), text, fill='black')
        # Ana metin
        draw.text((text_x, text_y), text, fill='white')
    except:
        pass
    
    # Farklı boyutlarda kaydet
    sizes = [256, 128, 64, 48, 32, 16]
    images = []
    
    for s in sizes:
        resized = img.resize((s, s), Image.Resampling.LANCZOS)
        images.append(resized)
    
    # ICO dosyası olarak kaydet
    img.save('app_icon.ico', format='ICO', sizes=[(s, s) for s in sizes])
    print("✓ app_icon.ico oluşturuldu")
    
    # PNG olarak da kaydet
    img.save('app_icon.png', format='PNG')
    print("✓ app_icon.png oluşturuldu")
    
    return 'app_icon.ico'

if __name__ == "__main__":
    create_app_icon()
    print("\nIcon dosyaları başarıyla oluşturuldu!")
