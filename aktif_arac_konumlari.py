import os
import sys
import time

# SUMO_HOME ortam değişkenini kontrol et
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("SUMO_HOME ortam değişkeni tanımlanmamış!")

import traci

def get_active_vehicles_positions():
    """SUMO simülasyonunda aktif olan tüm araçların konumlarını al"""
    
    # SUMO simülasyonunu başlat
    sumo_cmd = ["sumo-gui", "-c", "data/cross.sumocfg", "--start"]
    traci.start(sumo_cmd)
    
    try:
        print("SUMO Simülasyonunda Aktif Araçların Konumları")
        print("=" * 60)
        
        # Simülasyonu başlat ve bir süre çalıştır
        for step in range(100):  # İlk 100 adımı çalıştır
            traci.simulationStep()
            
            # Aktif araçların listesini al
            vehicle_ids = traci.vehicle.getIDList()
            
            if vehicle_ids:
                print(f"\nAdım {step}: {len(vehicle_ids)} aktif araç")
                print("-" * 50)
                
                for vehicle_id in vehicle_ids:
                    # Araç konumunu al (x, y koordinatları)
                    position = traci.vehicle.getPosition(vehicle_id)
                    x, y = position
                    
                    # Araç hızını al
                    speed = traci.vehicle.getSpeed(vehicle_id)
                    
                    # Araç açısını al
                    angle = traci.vehicle.getAngle(vehicle_id)
                    
                    # Araç tipini al
                    vehicle_type = traci.vehicle.getTypeID(vehicle_id)
                    
                    # Araç hangi yolda olduğunu al
                    road_id = traci.vehicle.getRoadID(vehicle_id)
                    
                    # Araç hangi şeritte olduğunu al
                    lane_id = traci.vehicle.getLaneID(vehicle_id)
                    
                    print(f"Araç ID: {vehicle_id}")
                    print(f"  Konum: ({x:.2f}, {y:.2f})")
                    print(f"  Hız: {speed:.2f} m/s ({speed*3.6:.2f} km/h)")
                    print(f"  Açı: {angle:.2f}°")
                    print(f"  Tip: {vehicle_type}")
                    print(f"  Yol: {road_id}")
                    print(f"  Şerit: {lane_id}")
                    print()
                
                # Her 10 adımda bir ekranı temizle ve bekle
                if step % 10 == 0 and step > 0:
                    time.sleep(2)  # 2 saniye bekle
                    os.system('cls' if os.name == 'nt' else 'clear')  # Ekranı temizle
            else:
                print(f"Adım {step}: Aktif araç yok")
    
    except KeyboardInterrupt:
        print("\nSimülasyon kullanıcı tarafından durduruldu.")
    
    finally:
        traci.close()
        print("SUMO bağlantısı kapatıldı.")

def save_positions_to_file():
    """Araç konumlarını dosyaya kaydet"""
    
    # SUMO simülasyonunu başlat
    sumo_cmd = ["sumo", "-c", "data/cross.sumocfg"]  # GUI olmadan
    traci.start(sumo_cmd)
    
    positions_file = "arac_konumlari.txt"
    
    try:
        with open(positions_file, 'w', encoding='utf-8') as file:
            file.write("SUMO Simülasyonu - Araç Konumları\n")
            file.write("=" * 50 + "\n\n")
            
            # Simülasyonu 200 adım boyunca çalıştır
            for step in range(200):
                traci.simulationStep()
                
                vehicle_ids = traci.vehicle.getIDList()
                
                if vehicle_ids:
                    file.write(f"Zaman Adımı: {step}\n")
                    file.write(f"Aktif Araç Sayısı: {len(vehicle_ids)}\n")
                    file.write("-" * 40 + "\n")
                    
                    for vehicle_id in vehicle_ids:
                        position = traci.vehicle.getPosition(vehicle_id)
                        speed = traci.vehicle.getSpeed(vehicle_id)
                        angle = traci.vehicle.getAngle(vehicle_id)
                        vehicle_type = traci.vehicle.getTypeID(vehicle_id)
                        road_id = traci.vehicle.getRoadID(vehicle_id)
                        
                        file.write(f"Araç: {vehicle_id}\n")
                        file.write(f"  Konum: ({position[0]:.2f}, {position[1]:.2f})\n")
                        file.write(f"  Hız: {speed:.2f} m/s\n")
                        file.write(f"  Açı: {angle:.2f}°\n")
                        file.write(f"  Tip: {vehicle_type}\n")
                        file.write(f"  Yol: {road_id}\n\n")
                    
                    file.write("\n")
                
                # İlerleme göster
                if step % 50 == 0:
                    print(f"İşlendi: {step}/200 adım")
    
    except Exception as e:
        print(f"Hata oluştu: {e}")
    
    finally:
        traci.close()
        print(f"Araç konumları '{positions_file}' dosyasına kaydedildi.")

def get_specific_vehicle_info(vehicle_id):
    """Belirli bir aracın detaylı bilgilerini al"""
    
    sumo_cmd = ["sumo-gui", "-c", "data/cross.sumocfg", "--start"]
    traci.start(sumo_cmd)
    
    try:
        print(f"'{vehicle_id}' aracının bilgileri takip ediliyor...")
        print("=" * 50)
        
        for step in range(300):  # 300 adım boyunca takip et
            traci.simulationStep()
            
            # Araç simülasyonda mevcut mu kontrol et
            if vehicle_id in traci.vehicle.getIDList():
                position = traci.vehicle.getPosition(vehicle_id)
                speed = traci.vehicle.getSpeed(vehicle_id)
                angle = traci.vehicle.getAngle(vehicle_id)
                route_id = traci.vehicle.getRouteID(vehicle_id)
                
                print(f"Adım {step}: Konum=({position[0]:.2f}, {position[1]:.2f}), "
                      f"Hız={speed:.2f} m/s, Açı={angle:.2f}°, Rota={route_id}")
                
                time.sleep(0.1)  # Küçük bir bekleme
            elif step > 50:  # İlk 50 adımdan sonra araç yoksa
                print(f"'{vehicle_id}' aracı simülasyonda bulunamadı veya simülasyonu tamamladı.")
                break
    
    except KeyboardInterrupt:
        print("\nTakip durduruldu.")
    
    finally:
        traci.close()

if __name__ == "__main__":
    print("SUMO Araç Konum Takip Sistemi")
    print("1. Tüm aktif araçları göster (ekranda)")
    print("2. Araç konumlarını dosyaya kaydet")
    print("3. Belirli bir aracı takip et")
    
    choice = input("\nSeçiminizi yapın (1/2/3): ").strip()
    
    if choice == "1":
        get_active_vehicles_positions()
    elif choice == "2":
        save_positions_to_file()
    elif choice == "3":
        vehicle_id = input("Takip edilecek araç ID'sini girin (örnek: left_0, right_2, down_18): ").strip()
        get_specific_vehicle_info(vehicle_id)
    else:
        print("Geçersiz seçim!")
