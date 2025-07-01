#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 GPS Quick Start Tool
Bu araç ESP32 GPS entegrasyonunu hızlıca test etmek için kullanılır.
"""

import subprocess
import sys
import time

def show_banner():
    print("🚀 ESP32 GPS Quick Start Tool")
    print("=" * 50)
    print("SUMO Ambulance GPS Control with ESP32")
    print()

def show_menu():
    print("📋 Kullanılabilir Komutlar:")
    print()
    print("1. 🔧 ESP32 Standalone Test")
    print("   ESP32 HTTP client'ını tek başına test eder")
    print("   Komut: python esp32_gps_client.py")
    print()
    print("2. 🧪 Entegrasyon Testi")
    print("   ESP32 ve SUMO entegrasyonunu test eder")
    print("   Komut: python test_esp32_integration.py")
    print()
    print("3. 🚗 SUMO Simülasyon - Dosyadan GPS")
    print("   Normal dosya modunda simülasyon çalıştırır")
    print("   Komut: python runner.py --gps-source file --nogui")
    print()
    print("4. 📡 SUMO Simülasyon - ESP32 WiFi (192.168.1.100)")
    print("   ESP32 WiFi modunda simülasyon çalıştırır")
    print("   Komut: python runner.py --gps-source esp32 --esp32-ip 192.168.1.100 --nogui")
    print()
    print("5. 📡 SUMO Simülasyon - ESP32 AP Mode (192.168.4.1)")
    print("   ESP32 Access Point modunda simülasyon çalıştırır")
    print("   Komut: python runner.py --gps-source esp32 --esp32-ip 192.168.4.1 --nogui")
    print()
    print("6. 🎮 SUMO Simülasyon - İnteraktif Mod")
    print("   GUI ile interaktif seçenek sunar")
    print("   Komut: python runner.py")
    print()
    print("7. ❓ Yardım - Command Line Options")
    print("   Tüm komut satırı seçeneklerini gösterir")
    print("   Komut: python runner.py --help")
    print()

def run_command(cmd, description):
    print(f"\n🚀 {description}")
    print(f"💻 Komut: {cmd}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, cwd=".", capture_output=False)
        if result.returncode == 0:
            print(f"✅ {description} başarılı!")
        else:
            print(f"❌ {description} başarısız! (Exit code: {result.returncode})")
    except KeyboardInterrupt:
        print(f"\n⏹️ {description} kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"❌ Hata: {e}")

def main():
    show_banner()
    
    while True:
        show_menu()
        
        try:
            choice = input("Seçiminiz (1-7) veya 'q' çıkış: ").strip()
            
            if choice.lower() == 'q':
                print("👋 Güle güle!")
                break
            
            if choice == "1":
                run_command("python esp32_gps_client.py", "ESP32 Standalone Test")
            elif choice == "2":
                run_command("python test_esp32_integration.py", "Entegrasyon Testi")
            elif choice == "3":
                run_command("python runner.py --gps-source file --nogui", "SUMO Simülasyon - Dosyadan GPS")
            elif choice == "4":
                run_command("python runner.py --gps-source esp32 --esp32-ip 192.168.1.100 --nogui", "SUMO Simülasyon - ESP32 WiFi")
            elif choice == "5":
                run_command("python runner.py --gps-source esp32 --esp32-ip 192.168.4.1 --nogui", "SUMO Simülasyon - ESP32 AP Mode")
            elif choice == "6":
                run_command("python runner.py", "SUMO Simülasyon - İnteraktif Mod")
            elif choice == "7":
                run_command("python runner.py --help", "Yardım - Command Line Options")
            else:
                print("❌ Geçersiz seçim! Lütfen 1-7 arası bir sayı girin.")
            
            print("\n" + "="*50)
            input("Devam etmek için Enter'a basın...")
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Güle güle!")
            break
        except Exception as e:
            print(f"❌ Hata: {e}")

if __name__ == "__main__":
    main()
