#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 GPS Integration Test
Bu test ESP32 GPS client'ının runner.py ile entegrasyonunu test eder.
"""

import sys
import os

# Test için ESP32 GPS client'ı import et
try:
    from esp32_gps_client import ESP32GPSClient
    print("✅ esp32_gps_client.py başarıyla import edildi")
    esp32_available = True
except ImportError as e:
    print(f"❌ esp32_gps_client.py import edilemedi: {e}")
    esp32_available = False

# Test için runner.py'daki fonksiyonları import et
try:
    from runner import on_real_time_gps_update, gps_to_sumo_coords
    print("✅ runner.py fonksiyonları başarıyla import edildi")
    runner_available = True
except ImportError as e:
    print(f"❌ runner.py fonksiyonları import edilemedi: {e}")
    runner_available = False

def test_esp32_integration():
    """ESP32 GPS client entegrasyonunu test et"""
    
    if not esp32_available:
        print("❌ ESP32 client kullanılamıyor")
        return False
    
    if not runner_available:
        print("❌ Runner fonksiyonları kullanılamıyor")
        return False
    
    print("\n🧪 ESP32 GPS Integration Test Başlıyor...")
    
    # Test için örnek ESP32 IP adresi
    test_ip = "192.168.1.100"
    test_port = 80
    
    try:
        # ESP32 GPS Client oluştur
        print(f"📡 ESP32 GPS Client oluşturuluyor: {test_ip}:{test_port}")
        client = ESP32GPSClient(test_ip, test_port)
        
        # Callback'i ayarla
        print("🔗 GPS callback ayarlanıyor...")
        client.set_gps_callback(on_real_time_gps_update)
        
        # Test GPS verisi
        test_lat = 41.0082
        test_lon = 28.9784
        
        print(f"🧪 Test GPS verisi: {test_lat}, {test_lon}")
        
        # Callback'i test et
        on_real_time_gps_update(test_lat, test_lon)
        
        # GPS to SUMO koordinat dönüşümünü test et
        sumo_x, sumo_y = gps_to_sumo_coords(test_lat, test_lon)
        print(f"🎯 SUMO Koordinatları: x={sumo_x:.2f}, y={sumo_y:.2f}")
        
        print("✅ Entegrasyon testi başarılı!")
        return True
        
    except Exception as e:
        print(f"❌ Entegrasyon testi başarısız: {e}")
        return False

def show_usage_examples():
    """Kullanım örneklerini göster"""
    print("\n📚 ESP32 GPS Kullanım Örnekleri:")
    print("\n1. Komut satırından ESP32 GPS source ile:")
    print("   python runner.py --gps-source esp32 --esp32-ip 192.168.1.100 --esp32-port 80")
    
    print("\n2. Komut satırından GUI olmadan:")
    print("   python runner.py --nogui --gps-source esp32 --esp32-ip 192.168.4.1")
    
    print("\n3. İnteraktif modda:")
    print("   python runner.py")
    print("   (Program başlayınca seçenek 2'yi seçin: ESP32 WiFi/HTTP)")
    
    print("\n4. ESP32 test modu:")
    print("   python esp32_gps_client.py")
    print("   (Standalone ESP32 test)")

if __name__ == "__main__":
    print("🚀 ESP32 GPS Integration Test Aracı")
    print("=" * 50)
    
    # Entegrasyon testini çalıştır
    success = test_esp32_integration()
    
    # Kullanım örneklerini göster
    show_usage_examples()
    
    if success:
        print("\n✅ Tüm testler başarılı! ESP32 GPS entegrasyonu hazır.")
        sys.exit(0)
    else:
        print("\n❌ Testler başarısız! Lütfen hataları kontrol edin.")
        sys.exit(1)
