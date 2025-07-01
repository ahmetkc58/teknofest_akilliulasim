#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 GPS Server Test Tool
Bu script ESP32 GPS server'ının çalışıp çalışmadığını test eder
"""

import requests
import time
import json
import sys
from datetime import datetime

class ESP32Tester:
    def __init__(self, esp32_ip="192.168.1.100", esp32_port=80):
        self.base_url = f"http://{esp32_ip}:{esp32_port}"
        self.esp32_ip = esp32_ip
        self.esp32_port = esp32_port
        
    def test_connection(self):
        """ESP32 bağlantısını test et"""
        print(f"🔗 ESP32 bağlantısı test ediliyor: {self.base_url}")
        
        try:
            response = requests.get(f"{self.base_url}/status", timeout=5)
            if response.status_code == 200:
                print("✅ ESP32 bağlantısı başarılı!")
                return True
            else:
                print(f"❌ HTTP hatası: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Bağlantı hatası - ESP32 erişilebilir değil")
            return False
        except requests.exceptions.Timeout:
            print("❌ Timeout hatası - ESP32 yanıt vermiyor")
            return False
        except Exception as e:
            print(f"❌ Beklenmeyen hata: {e}")
            return False
    
    def test_gps_endpoint(self):
        """GPS endpoint'ini test et"""
        print("\n📡 GPS endpoint testi...")
        
        try:
            response = requests.get(f"{self.base_url}/gps", timeout=5)
            if response.status_code == 200:
                gps_data = response.json()
                print("✅ GPS endpoint çalışıyor!")
                print(f"   📍 Latitude: {gps_data.get('latitude', 'N/A')}")
                print(f"   📍 Longitude: {gps_data.get('longitude', 'N/A')}")
                print(f"   ✔️ Valid: {gps_data.get('valid', 'N/A')}")
                print(f"   🛰️ Satellites: {gps_data.get('satellites', 'N/A')}")
                return True
            else:
                print(f"❌ GPS endpoint hatası: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ GPS endpoint test hatası: {e}")
            return False
    
    def test_status_endpoint(self):
        """Status endpoint'ini test et"""
        print("\n📊 Status endpoint testi...")
        
        try:
            response = requests.get(f"{self.base_url}/status", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                print("✅ Status endpoint çalışıyor!")
                print(f"   🔧 Device: {status_data.get('device', 'N/A')}")
                print(f"   📶 WiFi: {status_data.get('wifi_connected', 'N/A')}")
                print(f"   ⏱️ Uptime: {status_data.get('uptime', 0) / 1000:.1f}s")
                print(f"   💾 Free Heap: {status_data.get('free_heap', 'N/A')} bytes")
                return True
            else:
                print(f"❌ Status endpoint hatası: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Status endpoint test hatası: {e}")
            return False
    
    def test_led_control(self):
        """LED kontrol test"""
        print("\n🔴 LED kontrol testi...")
        
        try:
            # LED ON
            response = requests.get(f"{self.base_url}/led_on", timeout=5)
            if response.status_code == 200:
                print("✅ LED ON komutu başarılı")
                time.sleep(1)
                
                # LED OFF
                response = requests.get(f"{self.base_url}/led_off", timeout=5)
                if response.status_code == 200:
                    print("✅ LED OFF komutu başarılı")
                    return True
            
            print("❌ LED kontrol başarısız")
            return False
        except Exception as e:
            print(f"❌ LED kontrol test hatası: {e}")
            return False
    
    def test_buzzer_control(self):
        """Buzzer kontrol test"""
        print("\n🔊 Buzzer kontrol testi...")
        
        try:
            response = requests.get(f"{self.base_url}/buzzer", timeout=5)
            if response.status_code == 200:
                print("✅ Buzzer komutu başarılı")
                return True
            else:
                print("❌ Buzzer kontrol başarısız")
                return False
        except Exception as e:
            print(f"❌ Buzzer kontrol test hatası: {e}")
            return False
    
    def test_web_interface(self):
        """Web interface test"""
        print("\n🌐 Web interface testi...")
        
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200 and "ESP32" in response.text:
                print("✅ Web interface erişilebilir")
                print(f"   🌍 URL: {self.base_url}")
                return True
            else:
                print("❌ Web interface sorunu")
                return False
        except Exception as e:
            print(f"❌ Web interface test hatası: {e}")
            return False
    
    def continuous_gps_test(self, duration=30):
        """Sürekli GPS veri akış testi"""
        print(f"\n🔄 Sürekli GPS test ({duration} saniye)...")
        
        start_time = time.time()
        success_count = 0
        error_count = 0
        
        while time.time() - start_time < duration:
            try:
                response = requests.get(f"{self.base_url}/gps", timeout=2)
                if response.status_code == 200:
                    gps_data = response.json()
                    success_count += 1
                    print(f"📡 GPS #{success_count}: {gps_data['latitude']:.6f}, {gps_data['longitude']:.6f}")
                else:
                    error_count += 1
                    print(f"❌ Error #{error_count}")
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n⏹️ Test kullanıcı tarafından durduruldu")
                break
            except Exception as e:
                error_count += 1
                print(f"❌ Error #{error_count}: {e}")
                time.sleep(1)
        
        print(f"\n📊 Test Sonucu:")
        print(f"   ✅ Başarılı: {success_count}")
        print(f"   ❌ Hatalı: {error_count}")
        print(f"   📈 Başarı oranı: {success_count/(success_count+error_count)*100:.1f}%")
        
        return success_count > 0
    
    def run_full_test(self):
        """Tam test paketi"""
        print("🚀 ESP32 GPS Server - Tam Test Paketi")
        print("=" * 50)
        
        tests = [
            ("Bağlantı Testi", self.test_connection),
            ("GPS Endpoint", self.test_gps_endpoint),
            ("Status Endpoint", self.test_status_endpoint),
            ("LED Kontrol", self.test_led_control),
            ("Buzzer Kontrol", self.test_buzzer_control),
            ("Web Interface", self.test_web_interface),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Test: {test_name}")
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name} - BAŞARILI")
                else:
                    print(f"❌ {test_name} - BAŞARISIZ")
            except Exception as e:
                print(f"💥 {test_name} - HATA: {e}")
        
        print("\n" + "=" * 50)
        print(f"📊 TEST SONUCU: {passed}/{total} test başarılı")
        
        if passed == total:
            print("🎉 TÜM TESTLER BAŞARILI! ESP32 hazır.")
            return True
        else:
            print("⚠️ Bazı testler başarısız. Konfigürasyonu kontrol edin.")
            return False

def main():
    print("ESP32 GPS Server Test Aracı")
    print("=" * 30)
    
    # Komut satırı argümanları
    if len(sys.argv) > 1:
        esp32_ip = sys.argv[1]
    else:
        esp32_ip = input("ESP32 IP adresi [192.168.1.100]: ").strip() or "192.168.1.100"
    
    if len(sys.argv) > 2:
        esp32_port = int(sys.argv[2])
    else:
        esp32_port = 80
    
    # Test menüsü
    tester = ESP32Tester(esp32_ip, esp32_port)
    
    while True:
        print(f"\n📋 ESP32 Test Menüsü ({esp32_ip}:{esp32_port})")
        print("1. 🔗 Hızlı Bağlantı Testi")
        print("2. 📡 GPS Endpoint Testi")
        print("3. 🎛️ Kontrol Testleri (LED/Buzzer)")
        print("4. 🔄 Sürekli GPS Testi (30s)")
        print("5. 🧪 Tam Test Paketi")
        print("6. 🌐 Web Interface Aç")
        print("7. ❓ ESP32 Bilgileri")
        print("q. Çıkış")
        
        choice = input("\nSeçiminiz: ").strip().lower()
        
        if choice == "1":
            tester.test_connection()
        elif choice == "2":
            tester.test_gps_endpoint()
        elif choice == "3":
            tester.test_led_control()
            tester.test_buzzer_control()
        elif choice == "4":
            tester.continuous_gps_test(30)
        elif choice == "5":
            tester.run_full_test()
        elif choice == "6":
            import webbrowser
            webbrowser.open(f"http://{esp32_ip}:{esp32_port}")
            print(f"🌐 Web browser açıldı: {tester.base_url}")
        elif choice == "7":
            try:
                response = requests.get(f"{tester.base_url}/info", timeout=5)
                if response.status_code == 200:
                    info = response.json()
                    print("\n📋 ESP32 Bilgileri:")
                    for key, value in info.items():
                        print(f"   {key}: {value}")
                else:
                    print("❌ Bilgi alınamadı")
            except:
                print("❌ Info endpoint bulunamadı")
        elif choice == "q":
            print("👋 Güle güle!")
            break
        else:
            print("❌ Geçersiz seçim!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Program sonlandırıldı")
    except Exception as e:
        print(f"💥 Beklenmeyen hata: {e}")
