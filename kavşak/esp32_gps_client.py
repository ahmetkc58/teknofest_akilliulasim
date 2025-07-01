#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 GPS HTTP Client - SUMO GPS Ambulans Projesi
Bu modül ESP32'den HTTP ile GPS verilerini alır ve SUMO simülasyonuna aktarır.
"""

import requests
import json
import time
import threading
from datetime import datetime

class ESP32GPSClient:
    def __init__(self, esp32_ip="192.168.1.100", esp32_port=80):
        """
        ESP32 GPS Client başlatıcısı
        
        Args:
            esp32_ip (str): ESP32'nin IP adresi
            esp32_port (int): ESP32 HTTP sunucu portu
        """
        self.esp32_ip = esp32_ip
        self.esp32_port = esp32_port
        self.base_url = f"http://{esp32_ip}:{esp32_port}"
        
        self.is_running = False
        self.gps_callback = None
        self.update_thread = None
        
        # Son GPS verisi
        self.last_gps = {
            'latitude': 0.0,
            'longitude': 0.0,
            'timestamp': None,
            'valid': False
        }
        
        print(f"📡 ESP32 GPS Client hazırlandı: {self.base_url}")
    
    def set_gps_callback(self, callback_function):
        """GPS verisi geldiğinde çağrılacak callback fonksiyonunu ayarla"""
        self.gps_callback = callback_function
        print("✅ GPS callback fonksiyonu ayarlandı")
    
    def test_connection(self):
        """ESP32 bağlantısını test et"""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ ESP32 bağlantısı başarılı!")
                print(f"   📟 ESP32 Durum: {data.get('status', 'Unknown')}")
                print(f"   🛰️ GPS Durumu: {data.get('gps_status', 'Unknown')}")
                print(f"   📶 WiFi Sinyal: {data.get('wifi_signal', 'Unknown')} dBm")
                return True
            else:
                print(f"❌ ESP32 yanıt hatası: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ ESP32 bağlantı hatası: {e}")
            return False
    
    def get_gps_data(self):
        """ESP32'den anlık GPS verisi al"""
        try:
            response = requests.get(f"{self.base_url}/gps", timeout=3)
            if response.status_code == 200:
                data = response.json()
                
                # GPS verisi geçerli mi kontrol et
                if data.get('valid', False):
                    gps_data = {
                        'latitude': float(data['latitude']),
                        'longitude': float(data['longitude']),
                        'timestamp': datetime.now(),
                        'valid': True,
                        'satellites': data.get('satellites', 0),
                        'hdop': data.get('hdop', 99.99)
                    }
                    
                    self.last_gps = gps_data
                    return gps_data
                else:
                    print("⚠️ GPS sinyali geçersiz")
                    return None
            else:
                print(f"❌ GPS veri hatası: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ GPS veri alma hatası: {e}")
            return None
    
    def start_gps_updates(self, update_interval=1.0):
        """GPS güncellemelerini başlat (alias for start_continuous_updates)"""
        return self.start_continuous_updates(update_interval)
    
    def start_continuous_updates(self, update_interval=1.0):
        """Sürekli GPS güncellemelerini başlat"""
        if self.is_running:
            print("⚠️ GPS güncellemeleri zaten çalışıyor")
            return
        
        self.is_running = True
        self.update_thread = threading.Thread(
            target=self._continuous_update_worker,
            args=(update_interval,),
            daemon=True
        )
        self.update_thread.start()
        print(f"🔄 Sürekli GPS güncellemeleri başlatıldı (her {update_interval}s)")
    
    def stop_continuous_updates(self):
        """Sürekli GPS güncellemelerini durdur"""
        self.is_running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=2)
        print("🛑 GPS güncellemeleri durduruldu")
    
    def _continuous_update_worker(self, update_interval):
        """Arka planda sürekli GPS güncellemesi yapan worker"""
        consecutive_errors = 0
        max_errors = 5
        
        while self.is_running:
            try:
                gps_data = self.get_gps_data()
                
                if gps_data and gps_data['valid']:
                    # Başarılı GPS verisi alındı
                    consecutive_errors = 0
                    
                    # Callback fonksiyonunu çağır (SUMO'ya veri gönder)
                    if self.gps_callback:
                        self.gps_callback(gps_data['latitude'], gps_data['longitude'])
                    
                    # Detaylı GPS bilgisi (her 10 saniyede bir)
                    if int(time.time()) % 10 == 0:
                        print(f"🛰️ GPS: {gps_data['latitude']:.8f}, {gps_data['longitude']:.8f} "
                              f"| Uydu: {gps_data['satellites']} | HDOP: {gps_data['hdop']:.2f}")
                
                else:
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        print(f"❌ {max_errors} ardışık GPS hatası - Bağlantı sorunu olabilir")
                        consecutive_errors = 0  # Reset counter
                
                time.sleep(update_interval)
                
            except Exception as e:
                consecutive_errors += 1
                print(f"❌ GPS update worker hatası: {e}")
                time.sleep(update_interval * 2)  # Hata durumunda daha uzun bekle
    
    def send_command_to_esp32(self, command, parameters=None):
        """ESP32'ye komut gönder (LED kontrolü, ayarlar vs.)"""
        try:
            data = {'command': command}
            if parameters:
                data.update(parameters)
            
            response = requests.post(
                f"{self.base_url}/command",
                json=data,
                timeout=3
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ ESP32 komutu başarılı: {command}")
                return result
            else:
                print(f"❌ ESP32 komut hatası: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ ESP32 komut gönderme hatası: {e}")
            return None
    
    def set_led_status(self, led_on=True):
        """ESP32 LED durumunu ayarla"""
        return self.send_command_to_esp32('set_led', {'state': led_on})
    
    def get_system_info(self):
        """ESP32 sistem bilgilerini al"""
        try:
            response = requests.get(f"{self.base_url}/info", timeout=5)
            if response.status_code == 200:
                info = response.json()
                print("📟 ESP32 Sistem Bilgileri:")
                print(f"   🔧 Firmware: {info.get('firmware', 'Unknown')}")
                print(f"   💾 RAM: {info.get('free_heap', 'Unknown')} bytes")
                print(f"   ⏱️ Uptime: {info.get('uptime', 'Unknown')} ms")
                print(f"   📡 WiFi: {info.get('wifi_ssid', 'Unknown')}")
                return info
            else:
                print(f"❌ Sistem bilgisi hatası: HTTP {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Sistem bilgisi alma hatası: {e}")
            return None


# Test fonksiyonu
if __name__ == "__main__":
    # ESP32 GPS Client test
    print("🧪 ESP32 GPS Client Test")
    
    # ESP32 IP adresini buraya girin
    esp32_ip = input("ESP32 IP adresi [192.168.1.100]: ").strip() or "192.168.1.100"
    
    client = ESP32GPSClient(esp32_ip=esp32_ip)
    
    # Bağlantı testi
    if not client.test_connection():
        print("❌ ESP32'ye bağlanılamadı. IP adresini kontrol edin.")
        exit(1)
    
    # Sistem bilgilerini al
    client.get_system_info()
    
    # Test callback fonksiyonu
    def test_gps_callback(lat, lon):
        print(f"📍 GPS Callback: {lat:.8f}, {lon:.8f}")
    
    client.set_gps_callback(test_gps_callback)
    
    try:
        # Sürekli GPS güncellemelerini başlat
        client.start_continuous_updates(update_interval=2.0)
        
        print("\n✅ GPS güncellemeleri başladı. Durdurmak için Ctrl+C basın...")
        
        # Ana döngü
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Test durduruldu")
        client.stop_continuous_updates()
