import time
import requests
import json
import threading
from datetime import datetime
import os
import sys
import csv
import pandas as pd

# SUMO kütüphanelerini import et
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("SUMO_HOME ortam değişkeni tanımlanmamış")

import traci

class GPSSUMOEntegrator:
    def __init__(self):
        self.esp32_ip = "192.168.1.100"  # ESP32'nizin IP adresi
        self.sumo_connected = False
        self.gps_data = {}
        self.traffic_lights = {}
        
        # Veri kaynağı ayarları
        self.data_source = None  # 'esp32' veya 'file'
        self.test_data_files = {
            "1": "single_vehicle_test.csv",
            "2": "test_gps_data.csv",
            "3": "detailed_test_gps_data.csv"
        }
        self.test_data = []
        self.test_data_index = 0
        self.current_vehicle_id = None
        self.vehicle_created = False  # Araç bir kere oluşturuldu mu?
        
    def veri_kaynagi_sec(self):
        """Kullanıcıdan veri kaynağını seç"""
        print("\n🔌 Veri Kaynağı Seçimi:")
        print("1. ESP32'den gerçek GPS verisi al")
        print("2. Test dosyasından sahte GPS verisi al")
        
        while True:
            try:
                secim = input("\nSeçiminiz (1 veya 2): ").strip()
                if secim == "1":
                    self.data_source = "esp32"
                    print("✅ ESP32 veri kaynağı seçildi")
                    break
                elif secim == "2":
                    self.data_source = "file"
                    if self.test_dosyasini_yukle("single_vehicle_test.csv"):
                        print("✅ Test dosyası veri kaynağı seçildi")
                        break
                    else:
                        print("❌ Test dosyası yüklenemedi, tekrar seçin")
                        continue    

                else:
                    print("❌ Geçersiz seçim! Lütfen 1 veya 2 girin.")
            except KeyboardInterrupt:
                print("\n⏹️ İptal edildi")
                return False
        return True
    
    def test_dosya_sec(self):
        """Test dosyası seç ve yükle"""
        print("\n📁 Test Dosyası Seçimi:")
        print("1. Tek araç hareketi (single_vehicle_test.csv) - ÖNERİLEN")
        print("2. Çoklu araç verisi (test_gps_data.csv)")
        print("3. Detaylı çoklu araç verisi (detailed_test_gps_data.csv)")
        
        while True:
            try:
                secim = input("Hangi test dosyasını kullanmak istersiniz? (1, 2 veya 3): ").strip()
                if secim in self.test_data_files:
                    selected_file = self.test_data_files[secim]
                    print(f"📂 Seçilen test dosyası: {selected_file}")
                    return self.test_dosyasini_yukle(selected_file)
                else:
                    print("❌ Geçersiz seçim! Lütfen 1, 2 veya 3 girin.")
            except KeyboardInterrupt:
                print("\n⏹️ İptal edildi")
                return False
    
    def test_dosyasini_yukle(self, filename=None):
        """Test verisi dosyasını yükle"""
        if filename is None:
            filename = "test_gps_data.csv"
            
        try:
            if not os.path.exists(filename):
                print(f"❌ Test dosyası bulunamadı: {filename}")
                return False
                
            self.test_data = []
            with open(filename, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    self.test_data.append({
                        'timestamp': row['timestamp'],
                        'lat': float(row['latitude']),
                        'lon': float(row['longitude']),
                        'speed': float(row['speed']),
                        'vehicle_id': row['vehicle_id']
                    })
            
            print(f"📊 Test dosyası yüklendi: {filename} - {len(self.test_data)} veri noktası")
            return True
            
        except Exception as e:
            print(f"❌ Test dosyası yükleme hatası: {e}")
            return False
    
    def test_verisinden_gps_al(self):
        """Test dosyasından sıradaki GPS verisini al"""
        if not self.test_data or self.test_data_index >= len(self.test_data):
            # Dosya sonuna geldiysek baştan başla
            self.test_data_index = 0
            
        data = self.test_data[self.test_data_index]
        self.test_data_index += 1
        
        return {
            'lat': data['lat'],
            'lon': data['lon'],
            'timestamp': datetime.now(),  # Şimdiki zaman kullan
            'speed': data['speed'],
            'vehicle_id': data['vehicle_id']
        }
    
    def gps_veri_al(self):
        """Seçilen kaynaktan GPS verisini al"""
        if self.data_source == "esp32":
            return self.esp32_gps_al()
        elif self.data_source == "file":
            return self.test_verisinden_gps_al()
        else:
            print("❌ Veri kaynağı seçilmemiş!")
            return None
    
    def esp32_gps_al(self):
        try:
            response = requests.get(f"http://{self.esp32_ip}/location", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'lat': data.get('latitude'),
                    'lon': data.get('longitude'),
                    'timestamp': datetime.now(),
                    'speed': data.get('speed', 0)
                }
        except Exception as e:
            print(f"ESP32 bağlantı hatası: {e}")
            return None
    
    def gps_to_sumo_koordinat(self, lat, lon):
        """GPS koordinatlarını SUMO koordinat sistemine çevir"""
        # CSV'deki GPS değişimlerini gözlemlenebilir SUMO koordinat değişimlerine çevir
        
        # CSV'deki değişimleri büyük çarpanlarla normalize et
        lat_change = (lat - 41.0082) * 2000  # İlk değerden fark * büyük çarpan
        lon_change = (lon - 28.9784) * 2000  # İlk değerden fark * büyük çarpan
        
        # Simülasyonun merkezi etrafında hareket
        sumo_x = lon_change  # Boylam değişimi X ekseninde
        sumo_y = lat_change  # Enlem değişimi Y ekseninde
        
        # Cross simülasyonu için sınırlar (-150, +150)
        sumo_x = max(-120, min(120, sumo_x))
        sumo_y = max(-120, min(120, sumo_y))
        
        return sumo_x, sumo_y
    
    def sumo_baslat(self):
        """SUMO simülasyonunu başlat"""
        try:
            sumo_config = "data/cross.sumocfg"
            
            # Config dosyası var mı kontrol et
            if not os.path.exists(sumo_config):
                print(f"❌ SUMO config dosyası bulunamadı: {sumo_config}")
                print("💡 Basit bir simülasyon başlatılıyor...")
                
                # Basit bir ağ oluştur
                traci.start(['sumo-gui', '--start', '--quit-on-end'])
                self.sumo_connected = True
                print("✅ Basit SUMO simülasyonu başlatıldı")
                return
            
            # Config dosyası ile başlat
            traci.start(['sumo-gui', '-c', sumo_config, '--start', '--quit-on-end'])
            self.sumo_connected = True
            print("✅ SUMO simülasyonu başlatıldı")
            
            # Simülasyonu birkaç adım ilerlet (başlangıç için)
            for i in range(3):
                traci.simulationStep()
                
        except Exception as e:
            print(f"❌ SUMO başlatma hatası: {e}")
            print("💡 Alternatif başlatma deneniyor...")
            
            try:
                # Alternatif başlatma
                traci.start(['sumo-gui'])
                self.sumo_connected = True
                print("✅ SUMO alternatif başlatma başarılı")
            except Exception as e2:
                print(f"❌ Alternatif başlatma da başarısız: {e2}")
                self.sumo_connected = False
    
    def aktif_araclar_al(self):
        """SUMO'dan aktif araç listesini al"""
        if not self.sumo_connected:
            return {}
        
        try:
            vehicle_ids = traci.vehicle.getIDList()
            vehicles = {}
            
            for veh_id in vehicle_ids:
                pos = traci.vehicle.getPosition(veh_id)
                speed = traci.vehicle.getSpeed(veh_id)
                angle = traci.vehicle.getAngle(veh_id)
                road_id = traci.vehicle.getRoadID(veh_id)
                
                vehicles[veh_id] = {
                    'position': pos,
                    'speed': speed,
                    'angle': angle,
                    'road': road_id
                }
            
            return vehicles
        except Exception as e:
            print(f"Araç bilgisi alma hatası: {e}")
            return {}
    
    def trafik_yogunlugu_analiz(self, vehicles):
        """Trafik yoğunluğunu analiz et"""
        road_density = {}
        
        for veh_id, data in vehicles.items():
            road = data['road']
            if road not in road_density:
                road_density[road] = {
                    'vehicle_count': 0,
                    'avg_speed': 0,
                    'total_speed': 0
                }
            
            road_density[road]['vehicle_count'] += 1
            road_density[road]['total_speed'] += data['speed']
        
        # Ortalama hızları hesapla
        for road in road_density:
            count = road_density[road]['vehicle_count']
            if count > 0:
                road_density[road]['avg_speed'] = road_density[road]['total_speed'] / count
        
        return road_density
    
    def trafik_isigi_kontrol(self, road_density):
        """Trafik ışıklarını yoğunluğa göre ayarla"""
        try:
            traffic_light_ids = traci.trafficlight.getIDList()
            
            for tl_id in traffic_light_ids:
                # Trafik ışığına bağlı yolları al
                controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
                
                # Yoğunluğu hesapla
                total_density = 0
                for lane in controlled_lanes:
                    road_id = lane.split('_')[0]  # Lane'den road ID'yi çıkar
                    if road_id in road_density:
                        total_density += road_density[road_id]['vehicle_count']
                
                # Yoğunluğa göre faz süresini ayarla
                if total_density > 10:  # Yoğun trafik
                    phase_duration = 45  # Uzun yeşil
                elif total_density > 5:  # Orta yoğunluk
                    phase_duration = 30  # Normal yeşil
                else:  # Az trafik
                    phase_duration = 20  # Kısa yeşil
                
                # Trafik ışığı programını güncelle
                current_program = traci.trafficlight.getProgram(tl_id)
                # Dinamik olarak faz sürelerini ayarla (detaylı implementasyon gerekli)
                
                print(f"🚦 Trafik ışığı {tl_id}: Yoğunluk={total_density}, Süre={phase_duration}s")
        
        except Exception as e:
            print(f"Trafik ışığı kontrol hatası: {e}")
    
    def gps_arac_hareket_ettir(self, gps_data):
        """GPS verilerine göre SUMO'ya yeni araç ekle veya mevcut aracı güncelle"""
        if not gps_data or not self.sumo_connected:
            return
        
        try:
            # GPS koordinatlarını SUMO koordinatlarına çevir
            sumo_x, sumo_y = self.gps_to_sumo_koordinat(gps_data['lat'], gps_data['lon'])
            
            # Araç ID'sini belirle
            if 'vehicle_id' in gps_data:
                vehicle_id = f"gps_{gps_data['vehicle_id']}"
            else:
                vehicle_id = "gps_vehicle_main"
            
            self.current_vehicle_id = vehicle_id
            
            # Araç henüz oluşturulmadıysa oluştur (sadece bir kere)
            if not self.vehicle_created:
                try:
                    # İlk olarak aracı simülasyonun merkezine (0,0) yerleştir
                    traci.vehicle.moveToXY(vehicle_id, "", 0, 0, 0, 0, 5, 1)
                    self.vehicle_created = True
                    print(f"🚗 GPS aracı oluşturuldu (merkez): {vehicle_id}")
                    
                except Exception as e1:
                    try:
                        # moveToXY başarısız olursa, route ile dene
                        available_routes = traci.route.getIDList()
                        if available_routes:
                            route_id = available_routes[0]
                        else:
                            # Basit bir route oluştur
                            edges = traci.edge.getIDList()
                            if len(edges) >= 2:
                                route_id = "gps_route"
                                traci.route.add(route_id, [edges[0], edges[1]])
                            else:
                                print("❌ Route oluşturulamadı, edge yok")
                                return
                        
                        traci.vehicle.add(vehicle_id, route_id, typeID="DEFAULT_VEHTYPE")
                        self.vehicle_created = True
                        print(f"🚗 GPS aracı oluşturuldu (route): {vehicle_id}")
                        
                    except Exception as e2:
                        print(f"❌ Araç oluşturma başarısız: moveToXY={e1}, add={e2}")
                        return
            
            # Aracı GPS pozisyonuna taşı (var olan veya yeni eklenen)
            current_speed = gps_data.get('speed', 0)
            traci.vehicle.moveToXY(vehicle_id, "", 0, sumo_x, sumo_y, 0, current_speed)
            
            print(f"� GPS Aracı güncellendi: {vehicle_id} -> ({gps_data['lat']:.6f}, {gps_data['lon']:.6f}) "
                  f"SUMO: ({sumo_x:.2f}, {sumo_y:.2f}) Hız: {current_speed:.1f} m/s")
        
        except Exception as e:
            print(f"❌ Araç hareket ettirme hatası: {e}")
    
    def ana_dongu(self):
        """Ana sistem döngüsü"""
        print("🚀 GPS-SUMO Entegrasyon Sistemi Başlatılıyor...")
        
        # Veri kaynağını seç
        if not self.veri_kaynagi_sec():
            return
        
        # SUMO'yu başlat
        self.sumo_baslat()
        
        if not self.sumo_connected:
            print("❌ SUMO bağlantısı başarısız, sistem durduruluyor")
            return
        
        step = 0
        
        try:
            simulation_steps = 0
            max_steps = 300  # Maksimum simülasyon adımı
            
            while simulation_steps < max_steps:
                try:
                    # SUMO simülasyonunu bir adım ilerlet
                    traci.simulationStep()
                    step += 1
                    simulation_steps += 1
                except traci.exceptions.FatalTraCIError:
                    print("🏁 SUMO simülasyonu sona erdi")
                    break
                
                # Simülasyonda araç kalmadı mı kontrol et
                if traci.simulation.getMinExpectedNumber() <= 0 and not self.current_vehicle_id:
                    print("⚠️ Simülasyonda hiç araç yok, GPS aracı ekleniyor...")
                
                # Her 5 adımda bir GPS verisini güncelle (daha yavaş hareket)
                if step % 5 == 0:
                    gps_data = self.gps_veri_al()
                    if gps_data:
                        self.gps_arac_hareket_ettir(gps_data)
                
                # Her 20 adımda bir detaylı analiz yap
                if step % 20 == 0:
                    # Aktif araçları al
                    vehicles = self.aktif_araclar_al()
                    
                    # Eğer hiç araç yoksa ve GPS aracı da yoksa döngüyü kır
                    if len(vehicles) == 0 and not self.vehicle_created:
                        print("⚠️ Hiç aktif araç yok, GPS verisi bekleniyor...")
                    
                    # Trafik yoğunluğunu analiz et
                    road_density = self.trafik_yogunlugu_analiz(vehicles)
                    
                    # Trafik ışıklarını kontrol et
                    self.trafik_isigi_kontrol(road_density)
                    
                    # Durum raporu
                    print(f"\n📊 Simülasyon Adımı {step}:")
                    print(f"   🚗 Toplam aktif araç: {len(vehicles)}")
                    
                    # GPS aracının durumu
                    if self.current_vehicle_id and self.current_vehicle_id in vehicles:
                        gps_vehicle = vehicles[self.current_vehicle_id]
                        print(f"   📍 GPS Aracı ({self.current_vehicle_id}):")
                        print(f"       Konum: {gps_vehicle['position']}")
                        print(f"       Hız: {gps_vehicle['speed']:.1f} m/s")
                        print(f"       Yol: {gps_vehicle['road']}")
                    elif self.current_vehicle_id:
                        print(f"   ❌ GPS Aracı ({self.current_vehicle_id}) simülasyonda bulunamadı")
                    
                    # Yol yoğunluğu raporu
                    for road, density in road_density.items():
                        if density['vehicle_count'] > 0:
                            print(f"   📍 {road}: {density['vehicle_count']} araç, "
                                  f"Ort. hız: {density['avg_speed']:.1f} m/s")
                    
                    # CSV sonu kontrolü
                    if self.data_source == "file" and self.test_data_index >= len(self.test_data):
                        print("📄 CSV dosyası sonu, simülasyon 10 adım daha devam edecek")
                        if simulation_steps > len(self.test_data) * 5 + 50:  # Extra steps
                            break
                
                time.sleep(0.2)  # 200ms bekleme
                
            print(f"\n✅ Simülasyon tamamlandı - Toplam {simulation_steps} adım")
        
        except KeyboardInterrupt:
            print("\n⏹️  Sistem kullanıcı tarafından durduruldu")
        
        finally:
            if self.sumo_connected:
                traci.close()
                print("✅ SUMO bağlantısı kapatıldı")

def main():
    """Ana fonksiyon"""
    print("=" * 60)
    print("🌟 GPS-ESP32-SUMO Trafik Kontrol Sistemi")
    print("=" * 60)
    print("📋 Sistem Özellikleri:")
    print("   • ESP32'den gerçek GPS verisi alma")
    print("   • Test dosyasından sahte GPS verisi alma")
    print("   • SUMO simülasyonu ile entegrasyon")
    print("   • Gerçek zamanlı trafik yoğunluğu analizi")
    print("   • Akıllı trafik ışığı kontrolü")
    print("=" * 60)
    
    entegrator = GPSSUMOEntegrator()
    entegrator.ana_dongu()

if __name__ == "__main__":
    main()
