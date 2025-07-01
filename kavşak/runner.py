#!/usr/bin/env python
# Eclipse SUMO, Simulation of Urban MObility; see https://eclipse.dev/sumo
# Copyright (C) 2009-2024 German Aerospace Center (DLR) and others.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# https://www.eclipse.org/legal/epl-2.0/
# This Source Code may also be made available under the following Secondary
# Licenses when the conditions for such availability set forth in the Eclipse
# Public License 2.0 are satisfied: GNU General Public License, version 2
# or later which is available at
# https://www.gnu.org/licenses/old-licenses/gpl-2.0-standalone.html
# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

# @file    runner.py
# @author  Lena Kalleske
# @author  Daniel Krajzewicz
# @author  Michael Behrisch
# @author  Jakob Erdmann
# @date    2009-03-26

from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import random
import xml.etree.ElementTree as ET
import time
import threading
import math

# ESP32 GPS Client'ı import et
try:
    from esp32_gps_client import ESP32GPSClient
    esp32_client_available = True
except ImportError:
    print("⚠️ esp32_gps_client.py bulunamadı, ESP32 WiFi modu kullanılamayacak")
    esp32_client_available = False

# Global GPS değişkenleri
gps_coordinates = []
gps_index = 0
real_time_gps = None  # Gerçek zamanlı GPS verisi
use_real_time = False  # Gerçek zamanlı mod kontrolü
current_network_type = "cross"  # Varsayılan ağ tipi
esp32_gps_client = None  # ESP32 GPS client instance

# GPS Noise Filtreleme parametreleri
GPS_NOISE_FILTER = {
    'enabled': True,                    # Filtreleme aktif/pasif
    'min_movement_threshold': 0.000005, # Minimum hareket eşiği (derece - yaklaşık 0.5 metre)
    'max_speed_threshold': 50.0,        # Maksimum hız eşiği (km/h)
    'moving_average_window': 3,         # Hareketli ortalama pencere boyutu
    'stationary_timeout': 5.0,          # Durağan sayılma süresi (saniye)
    'noise_suppression_factor': 0.7     # Noise bastırma faktörü
}

# GPS Geçmiş veriler (filtreleme için)
gps_history = {
    'positions': [],                    # Son GPS pozisyonları [(lat, lon, timestamp), ...]
    'last_significant_position': None,  # Son önemli pozisyon
    'last_movement_time': 0,           # Son hareket zamanı
    'is_stationary': False,            # Durağan durum kontrolü
    'filtered_position': None,         # Filtrelenmiş pozisyon
    'total_updates': 0,                # Toplam GPS güncelleme sayısı
    'filtered_count': 0,               # Filtrelenen (noise) sayısı
}

# Global ambulans pozisyon tablosu ve sayaçlar
ambulance_position_table = {}  # {vehicle_id: [(step, x, y, lat, lon), ...]}
position_step_counter = 0

def add_position_to_table(vehicle_id, step, sumo_x, sumo_y, gps_lat, gps_lon):
    """Ambulansın pozisyonunu tabloya kaydet"""
    global ambulance_position_table
    
    if vehicle_id not in ambulance_position_table:
        ambulance_position_table[vehicle_id] = []
    
    ambulance_position_table[vehicle_id].append({
        'step': step,
        'sumo_x': round(sumo_x, 2),
        'sumo_y': round(sumo_y, 2),
        'gps_lat': round(gps_lat, 6),
        'gps_lon': round(gps_lon, 6)
    })

def print_ambulance_position_table():
    """Ambulans pozisyon tablosunu güzel formatta yazdır"""
    global ambulance_position_table
    
    if not ambulance_position_table:
        print("❌ Ambulans pozisyon verisi bulunamadı!")
        return
    
    print("\n" + "="*80)
    print("🚑 AMBULANS POZISYON TABLOSU - SUMO KOORDİNATLARI")
    print("="*80)
    
    for vehicle_id, positions in ambulance_position_table.items():
        if not positions:
            continue
            
        print(f"\n📍 {vehicle_id.upper()}:")
        print("-" * 70)
        print(f"{'Adım':<6} {'SUMO X':<10} {'SUMO Y':<10} {'GPS Lat':<12} {'GPS Lon':<12}")
        print("-" * 70)
        
        for pos in positions:
            print(f"{pos['step']:<6} {pos['sumo_x']:<10} {pos['sumo_y']:<10} {pos['gps_lat']:<12} {pos['gps_lon']:<12}")
        
        print(f"\n📊 Toplam {len(positions)} adım kaydedildi")
        
        # İlk ve son pozisyonları özetle
        if len(positions) > 1:
            first_pos = positions[0]
            last_pos = positions[-1]
            
            # Toplam mesafe hesapla
            total_distance = math.sqrt(
                (last_pos['sumo_x'] - first_pos['sumo_x'])**2 + 
                (last_pos['sumo_y'] - first_pos['sumo_y'])**2
            )
            
            print(f"🎯 Başlangıç: ({first_pos['sumo_x']}, {first_pos['sumo_y']})")
            print(f"🏁 Bitiş: ({last_pos['sumo_x']}, {last_pos['sumo_y']})")
            print(f"📏 Toplam mesafe: {total_distance:.2f} metre (Geniş hareket alanı: 200→800)")
    
    # GPS Filtreleme istatistikleri
    print("\n" + "="*80)
    print("🔧 GPS NOISE FILTER İSTATİSTİKLERİ")
    print("="*80)
    print(get_gps_filter_status())
    
    if gps_history['total_updates'] > 0:
        total_updates = gps_history['total_updates']
        filtered_count = gps_history['filtered_count']
        accepted_count = total_updates - filtered_count
        filter_ratio = (filtered_count / total_updates) * 100
        
        print(f"📈 Toplam GPS güncellemesi: {total_updates}")
        print(f"🔴 Filtrelenen (noise): {filtered_count}")
        print(f"✅ Kabul edilen (geçerli): {accepted_count}")
        print(f"📊 Filtreleme oranı: {filter_ratio:.1f}%")
        
        if filter_ratio > 80:
            print("⚠️ YÜKSEK NOISE ORANI! GPS modülünü kontrol edin.")
        elif filter_ratio > 50:
            print("⚠️ ORTA NOISE ORANI - Filtreleme parametrelerini ayarlayın")
        else:
            print("✅ Normal noise oranı")
    
    print("\n🔧 GPS Filter Parametreleri:")
    for key, value in GPS_NOISE_FILTER.items():
        print(f"   {key}: {value}")
    print("="*80)

def export_position_table_to_csv():
    """Ambulans pozisyon tablosunu CSV dosyasına aktar"""
    global ambulance_position_table
    
    if not ambulance_position_table:
        print("❌ CSV için veri bulunamadı!")
        return
    
    try:
        import csv
        csv_filename = f"ambulance_positions_{int(time.time())}.csv"
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['vehicle_id', 'step', 'sumo_x', 'sumo_y', 'gps_lat', 'gps_lon']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for vehicle_id, positions in ambulance_position_table.items():
                for pos in positions:
                    writer.writerow({
                        'vehicle_id': vehicle_id,
                        'step': pos['step'],
                        'sumo_x': pos['sumo_x'],
                        'sumo_y': pos['sumo_y'],
                        'gps_lat': pos['gps_lat'],
                        'gps_lon': pos['gps_lon']
                    })
        
        print(f"✅ Pozisyon verileri CSV'ye aktarıldı: {csv_filename}")
        
    except Exception as e:
        print(f"❌ CSV aktarım hatası: {e}")

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa


def generate_routefile():
    """GPS verilerini kullanarak ambulans rotası ile birlikte route dosyası oluştur"""
    global gps_coordinates, current_network_type
    
    # Ağ tipini tespit et
    network_type = detect_network_type()
    
    if network_type == "berlin":
        # Berlin ağı için routes oluştur
        return generate_berlin_routes()
    
    # Cross ağı için mevcut kod
    random.seed(42)  # make tests reproducible
    N = 5000  # number of time steps                simülasyon süresini belirtir
    
    # GPS verilerini oku
    gps_coordinates = parse_gps_data("gps-data-2.gpx")
    if gps_coordinates:
        print(f"GPS verisi başarıyla okundu: {len(gps_coordinates)} koordinat")
        # İlk ve son koordinatları göster
        print(f"İlk koordinat: {gps_coordinates[0]}")
        print(f"Son koordinat: {gps_coordinates[-1]}")
    else:
        print("GPS verisi okunamadı, varsayılan rotalar kullanılacak")
    
    # Normal trafik araçları - Tekrar aktif
    pWE = 1. / 10  # batı ve doğudan gelen araba sayıları
    pEW = 1. / 11
    pNS = 1. / 30
    
    with open("data/cross.rou.xml", "w") as routes: # burada trafik modeli olan xml dosyasını kopyalar
        print("""<routes>
        <vType id="typeWE" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" \
guiShape="passenger"/>
        <vType id="typeNS" accel="0.8" decel="4.5" sigma="0.5" length="7" minGap="3" maxSpeed="25" guiShape="emergency"/>
        <vType id="ambulance" accel="1.0" decel="5.0" sigma="0.1" length="6" minGap="2" maxSpeed="50" guiShape="emergency" color="1,0,0"/>

        <route id="right" edges="51o 1i 2o 52i" />
        <route id="left" edges="52o 2i 1o 51i" />
        <route id="down" edges="54o 4i 3o 53i" />
        <route id="ambulance_route" edges="51o 1i 2o 52i" />""", file=routes)
        
        vehNr = 0
        
        # GPS ile kontrol edilecek ambulansları ekle - ERKEN BAŞLATMA
        if gps_coordinates:
            ambulans_sayisi = 1  # Sadece bir ambulans (ambulance_gps_0)
            for amb_id in range(ambulans_sayisi):
                depart_time = 10 + (amb_id * 5)  # 10 saniye sonra başlat (normal araçlarla aynı anda)
                print(f'    <vehicle id="ambulance_gps_{amb_id}" type="ambulance" route="ambulance_route" depart="{depart_time}" color="1,0,0" departSpeed="0" departPos="0"/>', file=routes)
                vehNr += 1
            print(f"🚑 GPS ambulans {ambulans_sayisi} adet eklendi - {depart_time}s sonra başlayacak (normal araçlarla birlikte)")
        else:
            print("GPS verisi yok, ambulans eklenmedi")
        
        # Normal trafik araçları - DEVRE DIŞI BIRAKILDI (Sadece ambulans aktif)
        # for i in range(N):
        #     if random.uniform(0, 1) < pWE:
        #         print('    <vehicle id="right_%i" type="typeWE" route="right" depart="%i" />' % (
        #             vehNr, i), file=routes)
        #         vehNr += 1
        #     if random.uniform(0, 1) < pEW:
        #         print('    <vehicle id="left_%i" type="typeWE" route="left" depart="%i" />' % (
        #             vehNr, i), file=routes)
        #         vehNr += 1
        #     if random.uniform(0, 1) < pNS:
        #         print('    <vehicle id="down_%i" type="typeNS" route="down" depart="%i" color="1,0,0"/>' % (
        #             vehNr, i), file=routes)
        #         vehNr += 1
        
        print("🚫 Normal trafik araçları DEVRE DIŞI - Sadece ambulans aktif olacak")
        print("</routes>", file=routes)   # xml dosyasının sonunu belirtir

# The program looks like this
#    <tlLogic id="0" type="static" programID="0" offset="0">
# the locations of the tls are      NESW
#        <phase duration="31" state="GrGr"/>
#        <phase duration="6"  state="yryr"/>
#        <phase duration="31" state="rGrG"/>
#        <phase duration="6"  state="ryry"/>
#    </tlLogic>


def run():
    """execute the TraCI control loop"""
    global gps_index, current_network_type
    step = 0
    gps_vehicles_added = False
    
    # Trafik ışığı kontrolü sadece cross ağı için - TÜM IŞIKLAR KIRMIZI
    if current_network_type == "cross":
        # Tüm ışıkları kırmızı yap - Phase 0: "rrrr" (tüm yönler kırmızı)
        traci.trafficlight.setPhase("0", 0)                   # Tüm ışıklar kırmızı
        print("🔴 Başlangıç: TÜM IŞIKLAR KIRMIZI - Sadece ambulans için yeşil yapılacak")
    
    print(f"🚗 Simülasyon başlatıldı - Ağ tipi: {current_network_type}")
    
    # GPS Filtreleme durumunu göster
    if GPS_NOISE_FILTER['enabled']:
        print(f"🔧 GPS Noise Filtreleme AKTİF:")
        print(f"   📏 Min hareket eşiği: {GPS_NOISE_FILTER['min_movement_threshold']:.6f} derece")
        print(f"   🚀 Max hız eşiği: {GPS_NOISE_FILTER['max_speed_threshold']} km/h")
        print(f"   📊 Pencere boyutu: {GPS_NOISE_FILTER['moving_average_window']} veri")
        print(f"   ⏱️ Durağan timeout: {GPS_NOISE_FILTER['stationary_timeout']} saniye")
    else:
        print("🔧 GPS Noise Filtreleme PASİF - Tüm GPS verileri kabul edilecek")
    
    while step < 3600:  # 1 saat simülasyon
        traci.simulationStep()                                  # simülasyon adımı gerçekleştirilir
        
        # Berlin ağı için GPS vehicles'ı dinamik olarak ekle
        if current_network_type == "berlin" and not gps_vehicles_added and step > 10:
            gps_vehicles_added = add_gps_vehicles_to_simulation()
        
        # Cross ağı için ambulanslar zaten route dosyasında tanımlı, sadece işaretle
        if current_network_type == "cross" and not gps_vehicles_added and step > 10:
            gps_vehicles_added = True  # Cross ağında ambulanslar route file'da tanımlı
            
            # Ambulansları başlangıçta durdur (sadece ambulance_gps_0)
            for amb_id in range(1):  # Sadece ambulance_gps_0
                vehicle_id = f"ambulance_gps_{amb_id}"
                if vehicle_id in traci.vehicle.getIDList():
                    traci.vehicle.setSpeed(vehicle_id, 0)
                    traci.vehicle.setSpeedMode(vehicle_id, 0)
                    print(f"⏸️ {vehicle_id} durduruldu - Sadece GPS ile kontrol edilecek")
        
        # Ambulansları sürekli durdurmaya devam et (kendi kendine hareket etmesinler)
        if gps_vehicles_added and current_network_type == "cross":
            for amb_id in range(1):  # Sadece ambulance_gps_0
                vehicle_id = f"ambulance_gps_{amb_id}"
                if vehicle_id in traci.vehicle.getIDList():
                    # Sürekli hızı sıfırla
                    current_speed = traci.vehicle.getSpeed(vehicle_id)
                    if current_speed > 0:
                        traci.vehicle.setSpeed(vehicle_id, 0)
                        traci.vehicle.slowDown(vehicle_id, 0, 0.1)
        
        # Ambulansların GPS verilerine göre konumunu güncelle (Daha az sıklıkta - daha stabil)
        if (gps_coordinates or use_real_time) and gps_vehicles_added:
            # Gerçek zamanlı modda sürekli güncelle, dosya modunda her 15 adımda (daha az sık)
            update_frequency = 1 if use_real_time else 15
            
            if step % update_frequency == 0:
                if not use_real_time and gps_index < len(gps_coordinates):
                    print(f"\n🗺️ GPS Güncelleme - Adım {step}, GPS indeks: {gps_index}/{len(gps_coordinates)}")
                    update_gps_vehicles()
                    gps_index += 1
                elif use_real_time:
                    update_gps_vehicles()
        
        # Ambulans trafik ışığı kontrolü - her adımda çalışacak
        if current_network_type == "cross":
            monitor_all_ambulances_for_traffic_control()
        
        # Normal trafik ışığı kontrolü DEVRE DIŞI - Sadece ambulans kontrolü aktif
        # Normal araç olmadığı için trafik ışığı kontrolü gerekmiyor
        # Tüm ışıklar kırmızı kalacak, sadece ambulans yaklaştığında yeşil olacak
        if current_network_type == "cross":
            # Cross ağında simülasyon bitiş kontrolü
            if traci.simulation.getMinExpectedNumber() <= 0:
                break
                
            # Normal trafik akışı DEVRE DIŞI (normal araç yok)
            # if not is_ambulance_traffic_control_active():
            #     if traci.trafficlight.getPhase("0") == 2:
            #         # we are not already switching
            #         if traci.inductionloop.getLastStepVehicleNumber("0") > 0:         #burada kuzeyden gelen bir araç var mı diye bakılıyor
            #             # there is a vehicle from the north, switch
            #             traci.trafficlight.setPhase("0", 3)                 # tarafik ışığı fazı 3 olarak değiştirilir  doğu ve batı kısımlarında kırmızı yanmaya başlar
            #         else:                                                # araba gelmiyosa yeşil yakmaya devam eder
            #             # otherwise try to keep green for EW
            #             traci.trafficlight.setPhase("0", 2)
            
            # Ambulans aktif değilse ışıkları kırmızıda tut
            if not is_ambulance_traffic_control_active():
                traci.trafficlight.setPhase("0", 0)  # Tüm ışıklar kırmızı
        
        step += 1                                              # adım sayısı bir arttırılır
        
        # Berlin için progress gösterimi
        if current_network_type == "berlin" and step % 300 == 0:
            active_vehicles = len(traci.vehicle.getIDList())
            print(f"📊 Berlin simülasyon - Adım: {step}, Aktif araçlar: {active_vehicles}")
            
    print(f"✅ Simülasyon tamamlandı - Toplam adım: {step}")
    
    # Ambulans pozisyon tablosunu yazdır
    print_ambulance_position_table()
    
    # CSV'ye aktar (opsiyonel)
    export_position_table_to_csv()
    
    # ESP32 GPS client'ı kapat
    cleanup_gps_clients()
    
    traci.close()
    sys.stdout.flush()

def cleanup_gps_clients():
    """GPS client'larını temizle"""
    global esp32_gps_client
    
    if esp32_gps_client:
        try:
            esp32_gps_client.stop_gps_updates()
            print("✅ ESP32 GPS client durduruldu")
        except Exception as e:
            print(f"⚠️ ESP32 GPS client durdurulamadı: {e}")
        esp32_gps_client = None


def get_options():
    optParser = optparse.OptionParser() # analiz için kullanılan bişeymiş
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    optParser.add_option("--gps-source", type="choice", 
                         choices=["file", "esp32", "serial", "socket"],
                         default="file", help="GPS data source: file, esp32, serial, socket")
    optParser.add_option("--esp32-ip", type="string", default="192.168.1.100",
                         help="ESP32 IP address for WiFi GPS (default: 192.168.1.100)")
    optParser.add_option("--esp32-port", type="int", default=80,
                         help="ESP32 HTTP port (default: 80)")
    
    # GPS Noise Filtreleme parametreleri
    optParser.add_option("--gps-filter", action="store_true",
                         default=True, help="Enable GPS noise filtering (default: enabled)")
    optParser.add_option("--no-gps-filter", action="store_true",
                         default=False, help="Disable GPS noise filtering")
    optParser.add_option("--gps-min-movement", type="float", default=0.000005,
                         help="Minimum GPS movement threshold in degrees (default: 0.000005)")
    optParser.add_option("--gps-max-speed", type="float", default=50.0,
                         help="Maximum speed threshold in km/h (default: 50.0)")
    optParser.add_option("--gps-window-size", type="int", default=3,
                         help="Moving average window size (default: 3)")
    
    options, args = optParser.parse_args()
    
    # GPS filtre ayarlarını uygula
    if options.no_gps_filter:
        GPS_NOISE_FILTER['enabled'] = False
    else:
        GPS_NOISE_FILTER['enabled'] = True
    
    GPS_NOISE_FILTER['min_movement_threshold'] = options.gps_min_movement
    GPS_NOISE_FILTER['max_speed_threshold'] = options.gps_max_speed
    GPS_NOISE_FILTER['moving_average_window'] = options.gps_window_size
    
    return options


def parse_gps_data(gpx_file):
    """GPX dosyasından GPS koordinatlarını oku ve aralık analizi yap"""
    try:
        tree = ET.parse(gpx_file)
        root = tree.getroot()
        
        # GPX namespace
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
        
        coordinates = []
        # trkpt elementlerini bul
        for trkpt in root.findall('.//gpx:trkpt', ns):
            if trkpt is None:
                continue
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            coordinates.append((lat, lon))
        
        # Eğer namespace ile bulamazsak, namespace olmadan dene
        if not coordinates:
            for trkpt in root.findall('.//trkpt'):
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                coordinates.append((lat, lon))
        
        if coordinates:
            # GPS aralık analizi
            lats = [coord[0] for coord in coordinates]
            lons = [coord[1] for coord in coordinates]
            
            lat_min, lat_max = min(lats), max(lats)
            lon_min, lon_max = min(lons), max(lons)
            
            # Mesafe hesaplaması (yaklaşık)
            lat_distance = (lat_max - lat_min) * 111000  # 1 derece ≈ 111km
            lon_distance = (lon_max - lon_min) * 111000 * abs(math.cos(math.radians((lat_min + lat_max)/2)))
            
            print(f"📊 GPS Aralık Analizi:")
            print(f"   Latitude: {lat_min:.6f} - {lat_max:.6f} (Fark: {lat_distance:.1f}m)")
            print(f"   Longitude: {lon_min:.6f} - {lon_max:.6f} (Fark: {lon_distance:.1f}m)")
            print(f"   Toplam Nokta: {len(coordinates)}")
            print(f"   İlk nokta: {coordinates[0]}")
            print(f"   Son nokta: {coordinates[-1]}")
            
            # Küçük aralık uyarısı
            if lat_distance < 10 and lon_distance < 10:
                print(f"⚠️ GPS aralığı çok küçük (<10m) - Amplification aktif!")
        
        return coordinates
    except Exception as e:
        print(f"GPS verisi okunamadı: {e}")
        return []


def gps_to_sumo_coords(lat, lon, network_type="cross"):
    """
    GPS koordinatlarını SUMO koordinatlarına dönüştür - Ultra hassas mikro hareket destekli
    
    Bu fonksiyon küçük GPS değişikliklerini görünür SUMO hareketlerine dönüştürür.
    GPS Aralığı: Lat(37.066913-37.066950), Lon(30.209252-30.209310)
    SUMO Hedef: x(200-800), y(500-620) = 600x120 birim alan - GENİŞLETİLMİŞ HAREKET ALANI
    """
    
    if network_type == "berlin":
        # Berlin ağı için doğru UTM Zone 36N koordinatları
        min_lon, min_lat = 30.494791, 37.406898
        max_lon, max_lat = 30.614099, 37.515896
        min_x, min_y = 0.0, 0.0
        max_x, max_y = 10604.93, 9947.54
        
        x = (lon - min_lon) / (max_lon - min_lon) * (max_x - min_x) + min_x
        y = (lat - min_lat) / (max_lat - min_lat) * (max_y - min_y) + min_y
        
        safety_margin = 100.0
        x = max(safety_margin, min(max_x - safety_margin, x))
        y = max(safety_margin, min(max_y - safety_margin, y))
        
        return x, y
    
    else:
        # İYİLEŞTİRİLMİŞ CROSS NETWORK MAPPING - DOĞRUSAL VE STABİL HAREKETİ
        
        # GPS-data-2.gpx'teki GERÇEK koordinat aralığı (analiz edilen)
        gps_lat_min = 36.91973000  # En küçük latitude
        gps_lat_max = 36.91979667  # En büyük latitude (~7.4 metre fark)
        gps_lon_min = 30.67373167  # En küçük longitude  
        gps_lon_max = 30.67379000  # En büyük longitude (~5.2 metre fark)
        
        # SUMO KAVŞAK ROTASı - GPS verilerine göre doğrusal yol
        # Cross ağında mevcut yol yapısını kullanarak ambulansı
        # Batıdan doğuya (West to East) hareket ettireceğiz
        
        # GPS progression: South-West → North-East yönü 
        # SUMO mapping: (200, 510) → (800, 510) yatay çizgi üzerinde - GENİŞLETİLMİŞ ALAN
        
        sumo_x_start = 200.0   # Batı başlangıç noktası (kavşak öncesi) - GENİŞLETİLDİ
        sumo_x_end = 800.0     # Doğu bitiş noktası (kavşak sonrası) - GENİŞLETİLDİ  
        sumo_y_road = 510.0    # Yatay yol merkezi (sabit Y)
        
        # GPS progression oranını hesapla (0.0 = başlangıç, 1.0 = son)
        if gps_lat_max > gps_lat_min and gps_lon_max > gps_lon_min:
            # GPS verilerindeki ilerleyişi hesapla
            lat_progress = (lat - gps_lat_min) / (gps_lat_max - gps_lat_min)
            lon_progress = (lon - gps_lon_min) / (gps_lon_max - gps_lon_min)
            
            # İki progress'in ortalamasını al (daha stabil)
            combined_progress = (lat_progress + lon_progress) / 2.0
            
            # 0-1 aralığında sınırla
            combined_progress = max(0.0, min(1.0, combined_progress))
            
            # DOĞRUSAL SUMO X KOORDİNATI (Batı→Doğu)
            sumo_x = sumo_x_start + (combined_progress * (sumo_x_end - sumo_x_start))
            sumo_y = sumo_y_road  # Y sabit (yatay yol)
            
        else:
            # Fallback: Kavşak merkezi
            sumo_x = 510.0
            sumo_y = 510.0
        
        # SAFETY CLAMP - Yol sınırları içinde tut - GENİŞLETİLMİŞ SINIRLAR
        sumo_x = max(150.0, min(850.0, sumo_x))  # Geniş sınırlar (200-800 + güvenlik marjı)
        sumo_y = max(505.0, min(515.0, sumo_y))  # Yol genişliği sınırları
        
        # Debug bilgisi (daha az sıklıkta - her 10 koordinatta bir)
        if hasattr(gps_to_sumo_coords, 'debug_counter'):
            gps_to_sumo_coords.debug_counter += 1
        else:
            gps_to_sumo_coords.debug_counter = 1
            
        # Her 10 koordinatta bir debug yazdır (daha az log karmaşası)
        if gps_to_sumo_coords.debug_counter % 10 == 1:
            print(f"🎯 GPS Mapping Debug #{gps_to_sumo_coords.debug_counter}:")
            print(f"   📍 GPS Giriş: ({lat:.8f}, {lon:.8f})")
            print(f"   🎯 SUMO Çıkış: ({sumo_x:.2f}, {sumo_y:.2f})")
            print(f"   📏 GPS Range: lat=({gps_lat_min:.8f} - {gps_lat_max:.8f}), lon=({gps_lon_min:.8f} - {gps_lon_max:.8f})")
            print(f"   🛣️ SUMO Route: X({sumo_x_start:.1f} → {sumo_x_end:.1f}), Y={sumo_y_road:.1f} (Geniş doğrusal yol - 600m mesafe)")
        
        return sumo_x, sumo_y


def gps_to_cross_coords_manual(lat, lon, custom_bounds=None):
    """
    Manual GPS to Cross SUMO coordinate conversion with custom bounds
    
    Args:
        lat, lon: GPS coordinates
        custom_bounds: Optional dict with 'gps' and 'sumo' bounds
                      Example: {
                          'gps': {'lat_min': 37.066, 'lat_max': 37.067, 'lon_min': 30.208, 'lon_max': 30.210},
                          'sumo': {'x_min': 500, 'x_max': 520, 'y_min': 500, 'y_max': 520}
                      }
    """
    if custom_bounds:
        # Use custom bounds
        gps_bounds = custom_bounds['gps']
        sumo_bounds = custom_bounds['sumo']
        
        gps_lat_min = gps_bounds['lat_min']
        gps_lat_max = gps_bounds['lat_max']
        gps_lon_min = gps_bounds['lon_min']  
        gps_lon_max = gps_bounds['lon_max']
        
        sumo_x_min = sumo_bounds['x_min']
        sumo_x_max = sumo_bounds['x_max']
        sumo_y_min = sumo_bounds['y_min']
        sumo_y_max = sumo_bounds['y_max']
    else:
        # Default bounds for cross intersection
        gps_lat_min, gps_lat_max = 37.0665, 37.0675
        gps_lon_min, gps_lon_max = 30.2085, 30.2105
        sumo_x_min, sumo_x_max = 500.0, 520.0
        sumo_y_min, sumo_y_max = 500.0, 520.0
    
    # Linear scaling
    x = ((lon - gps_lon_min) / (gps_lon_max - gps_lon_min)) * (sumo_x_max - sumo_x_min) + sumo_x_min
    y = ((lat - gps_lat_min) / (gps_lat_max - gps_lat_min)) * (sumo_y_max - sumo_y_min) + sumo_y_min
    
    # Clamp to bounds
    x = max(sumo_x_min, min(sumo_x_max, x))
    y = max(sumo_y_min, min(sumo_y_max, y))
    
    return x, y


def is_position_safe(x, y, network_type="cross"):
    """Verilen pozisyonun SUMO ağında güvenli olup olmadığını kontrol et"""
    if network_type == "berlin":
        # Berlin ağı sınırları
        if x < 0 or x > 10604.93 or y < 0 or y > 9947.54:
            return False
        
        # Kenar güvenlik kontrolü
        safety_margin = 100.0
        if (x < safety_margin or x > 10604.93 - safety_margin or 
            y < safety_margin or y > 9947.54 - safety_margin):
            return False
            
        return True
    else:
        # Cross ağı sınırları (1020x1020 intersection)
        if x < 0 or x > 1020 or y < 0 or y > 1020:
            return False
        
        # Cross intersection active area - vehicles should stay in central area
        # where roads actually exist (around center 510,510)
        center_x, center_y = 510, 510
        max_distance_from_center = 200.0  # 200m radius from intersection center
        
        distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
        return distance <= max_distance_from_center


def is_position_on_intersection_roads(x, y):
    """
    Check if position is on actual roads in the cross intersection
    
    Cross intersection has roads in these areas:
    - Horizontal road: roughly y=505-515, x=0-1020  
    - Vertical road: roughly x=505-515, y=0-1020
    """
    # Horizontal road corridor
    if 505 <= y <= 515 and 0 <= x <= 1020:
        return True
    
    # Vertical road corridor  
    if 505 <= x <= 515 and 0 <= y <= 1020:
        return True
    
    return False


def safe_move_vehicle(vehicle_id, lat, lon, retry_count=3, network_type="cross"):
    """Aracı hassas GPS koordinatlarına ışınla - Ultra hassas mikro hareket destekli"""
    global position_step_counter
    
    # Hassas koordinat dönüşümü
    sumo_x, sumo_y = gps_to_sumo_coords(lat, lon, network_type)
    
    # Teleportasyon için en uygun pozisyonu bul
    for attempt in range(retry_count):
        try:
            # Aracı tamamen durdur
            traci.vehicle.setSpeed(vehicle_id, 0)
            traci.vehicle.setSpeedMode(vehicle_id, 0)  # Tüm güvenlik kontrollerini devre dışı bırak
            
            # Ultra hassas teleportasyon
            # Cross ağında yolları hassas şekilde belirle
            if network_type == "cross":
                # Yatay yol (East-West) üzerinde hareket
                # Lane bilgisini de ekleyerek daha hassas yerleştirme
                target_edge = ""  # Otomatik edge bulma
                target_lane = 0   # En yakın lane
                
                # Teleportasyon açısını hareket yönüne göre ayarla
                # GPS verilerindeki hareket yönünü hesaplayabiliriz
                angle = 90  # Varsayılan: Doğu yönü (0=Kuzey, 90=Doğu, 180=Güney, 270=Batı)
                
                # moveToXY ile hassas yerleştirme
                traci.vehicle.moveToXY(
                    vehicle_id,
                    target_edge,     # "" = otomatik edge bulma
                    target_lane,     # Lane index
                    sumo_x,          # X koordinatı
                    sumo_y,          # Y koordinatı  
                    angle,           # Araç yönü
                    keepRoute=0      # Rotayı takip etme
                )
            else:
                # Berlin ağı için
                traci.vehicle.moveToXY(
                    vehicle_id, "", 0, sumo_x, sumo_y, angle=0, keepRoute=0
                )
            
            # Hareket etmemesi için hızı kilitle
            traci.vehicle.setSpeed(vehicle_id, 0)
            traci.vehicle.slowDown(vehicle_id, 0, 0.1)  # Anında dur
            
            # Başarılı teleportasyon sonrası gerçek pozisyonu al
            actual_pos = traci.vehicle.getPosition(vehicle_id)
            
            # AYRRINTILI Ambulans koordinat logu - Hareket analizi
            print(f"📍 {vehicle_id} | GPS: ({lat:.8f}, {lon:.8f}) | SUMO: ({actual_pos[0]:.2f}, {actual_pos[1]:.2f})")
            
            # Pozisyon değişikliği hesapla (önceki pozisyonla karşılaştır)
            if hasattr(safe_move_vehicle, 'prev_positions'):
                if vehicle_id in safe_move_vehicle.prev_positions:
                    prev_pos = safe_move_vehicle.prev_positions[vehicle_id]
                    distance_moved = math.sqrt(
                        (actual_pos[0] - prev_pos[0])**2 + 
                        (actual_pos[1] - prev_pos[1])**2
                    )
                    print(f"📏 {vehicle_id} hareket mesafesi: {distance_moved:.2f} metre")
                else:
                    safe_move_vehicle.prev_positions = {}
                safe_move_vehicle.prev_positions[vehicle_id] = actual_pos
            else:
                safe_move_vehicle.prev_positions = {vehicle_id: actual_pos}
            
            # Pozisyonu tabloya kaydet  
            position_step_counter += 1
            add_position_to_table(
                vehicle_id, 
                position_step_counter, 
                actual_pos[0], actual_pos[1], 
                lat, lon
            )
            
            # Hassas hareket logging - daha ayrıntılı
            print(f"🎯 {vehicle_id} - Adım {position_step_counter}:")
            print(f"   📍 GPS: ({lat:.8f}, {lon:.8f})")
            print(f"   🎯 Target SUMO: ({sumo_x:.2f}, {sumo_y:.2f})")
            print(f"   ✅ Actual SUMO: ({actual_pos[0]:.2f}, {actual_pos[1]:.2f}) [LOCKED]")
            
            return True
            
        except Exception as e:
            if attempt < retry_count - 1:
                # Hassas retry stratejileri
                if attempt == 0:
                    # 1. Deneme: Y koordinatını yol merkezine snap
                    if network_type == "cross":
                        sumo_y = 510.0  # Yatay yol merkezi
                    print(f"🔄 Retry {attempt + 1}: Yol merkezine snap (y={sumo_y})")
                elif attempt == 1:
                    # 2. Deneme: X koordinatını biraz kaydır
                    sumo_x += 5.0
                    print(f"🔄 Retry {attempt + 1}: X kaydırma (+5m)")
            else:
                print(f"❌ Hassas teleport başarısız {vehicle_id}: {e}")
                return False
    
    return False


def calculate_gps_distance(lat1, lon1, lat2, lon2):
    """İki GPS koordinatı arasındaki mesafeyi hesapla (metre)"""
    import math
    
    # Haversine formula
    R = 6371000  # Dünya yarıçapı (metre)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon/2) * math.sin(delta_lon/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def filter_gps_noise(lat, lon):
    """GPS noise filtreleme algoritması"""
    global gps_history, GPS_NOISE_FILTER
    
    current_time = time.time()
    
    # Toplam güncelleme sayısını artır
    gps_history['total_updates'] += 1
    
    # Filtreleme devre dışıysa orijinal veriyi döndür
    if not GPS_NOISE_FILTER['enabled']:
        return lat, lon, False
    
    # Geçmiş pozisyonları sakla
    gps_history['positions'].append((lat, lon, current_time))
    
    # Pencere boyutunu aş olanları temizle
    window_size = GPS_NOISE_FILTER['moving_average_window']
    if len(gps_history['positions']) > window_size:
        gps_history['positions'] = gps_history['positions'][-window_size:]
    
    # İlk veri ise direkt kabul et
    if len(gps_history['positions']) == 1:
        gps_history['last_significant_position'] = (lat, lon, current_time)
        gps_history['last_movement_time'] = current_time
        gps_history['filtered_position'] = (lat, lon)
        print(f"🟢 GPS Filter: İlk pozisyon kaydedildi ({lat:.8f}, {lon:.8f})")
        return lat, lon, False
    
    # Son önemli pozisyonla mesafe hesapla
    last_lat, last_lon, last_time = gps_history['last_significant_position']
    distance = calculate_gps_distance(last_lat, last_lon, lat, lon)
    time_diff = current_time - last_time
    
    # Hız hesapla (km/h)
    speed_kmh = 0
    if time_diff > 0:
        speed_kmh = (distance / time_diff) * 3.6  # m/s to km/h
    
    # Minimum hareket eşiği kontrolü
    min_threshold = GPS_NOISE_FILTER['min_movement_threshold']
    coordinate_distance = math.sqrt((lat - last_lat)**2 + (lon - last_lon)**2)
    
    print(f"🔍 GPS Filter Debug:")
    print(f"   📍 Mesafe: {distance:.2f}m | Hız: {speed_kmh:.1f} km/h")
    print(f"   📏 Koordinat farkı: {coordinate_distance:.8f} derece")
    print(f"   ⏱️ Zaman farkı: {time_diff:.1f}s")
    
    # Noise tespit kriterleri
    is_noise = False
    noise_reasons = []
    
    # 1. Minimum hareket eşiği
    if coordinate_distance < min_threshold:
        is_noise = True
        noise_reasons.append(f"hareket<{min_threshold:.6f}")
    
    # 2. Maksimum hız kontrolü
    if speed_kmh > GPS_NOISE_FILTER['max_speed_threshold']:
        is_noise = True
        noise_reasons.append(f"hız>{GPS_NOISE_FILTER['max_speed_threshold']}km/h")
    
    # 3. Durağan durum kontrolü
    stationary_timeout = GPS_NOISE_FILTER['stationary_timeout']
    time_since_last_movement = current_time - gps_history['last_movement_time']
    
    if time_since_last_movement > stationary_timeout:
        gps_history['is_stationary'] = True
        if distance < 2.0:  # 2 metre içinde hareket = noise
            is_noise = True
            noise_reasons.append("durağan_gürültü")
    
    # Filtreleme kararı
    if is_noise:
        gps_history['filtered_count'] += 1  # Filtrelenen sayısını artır
        print(f"🔴 GPS NOISE TESPİT EDİLDİ: {', '.join(noise_reasons)}")
        print(f"   🚫 Pozisyon güncellenmeyecek")
        
        # Moving average hesapla (gürültü bastırma)
        if len(gps_history['positions']) >= 2:
            avg_lat = sum(p[0] for p in gps_history['positions']) / len(gps_history['positions'])
            avg_lon = sum(p[1] for p in gps_history['positions']) / len(gps_history['positions'])
            
            # Noise suppression factor uygula
            factor = GPS_NOISE_FILTER['noise_suppression_factor']
            filtered_lat = last_lat * factor + avg_lat * (1 - factor)
            filtered_lon = last_lon * factor + avg_lon * (1 - factor)
            
            gps_history['filtered_position'] = (filtered_lat, filtered_lon)
            
        # Son önemli pozisyonu döndür (hareket yok)
        return last_lat, last_lon, True
    
    else:
        print(f"✅ GPS GEÇERLI HAREKET:")
        print(f"   📍 Yeni pozisyon: ({lat:.8f}, {lon:.8f})")
        print(f"   📏 Hareket mesafesi: {distance:.2f}m")
        
        # Önemli pozisyonu güncelle
        gps_history['last_significant_position'] = (lat, lon, current_time)
        gps_history['last_movement_time'] = current_time
        gps_history['is_stationary'] = False
        gps_history['filtered_position'] = (lat, lon)
        
        return lat, lon, False

def get_gps_filter_status():
    """GPS filtre durumunu döndür"""
    global gps_history
    
    if not gps_history['last_significant_position']:
        return "GPS filtreleme henüz başlamadı"
    
    current_time = time.time()
    last_time = gps_history['last_significant_position'][2]
    time_since_last = current_time - last_time
    
    status = f"GPS Filter Durumu:\n"
    status += f"📍 Son önemli pozisyon: {gps_history['last_significant_position'][0]:.6f}, {gps_history['last_significant_position'][1]:.6f}\n"
    status += f"⏱️ Son güncelleme: {time_since_last:.1f} saniye önce\n"
    status += f"🏃 Durağan: {'Evet' if gps_history['is_stationary'] else 'Hayır'}\n"
    status += f"📊 Geçmiş veri sayısı: {len(gps_history['positions'])}\n"
    
    return status

def toggle_gps_filter(enabled=None):
    """GPS filtrelemeyi aç/kapat"""
    global GPS_NOISE_FILTER
    
    if enabled is None:
        GPS_NOISE_FILTER['enabled'] = not GPS_NOISE_FILTER['enabled']
    else:
        GPS_NOISE_FILTER['enabled'] = enabled
    
    status = "AKTİF" if GPS_NOISE_FILTER['enabled'] else "PASİF"
    print(f"🔧 GPS Noise Filtreleme: {status}")
    return GPS_NOISE_FILTER['enabled']


def find_nearest_safe_position(x, y, network_type="cross"):
    """En yakın güvenli pozisyonu bul"""
    if network_type == "berlin":
        # Berlin ağı için sınırları kontrol et
        safety_margin = 100.0
        max_x, max_y = 10604.93, 9947.54
        
        # Sınırlar içine al
        safe_x = max(safety_margin, min(max_x - safety_margin, x))
        safe_y = max(safety_margin, min(max_y - safety_margin, y))
        
        return safe_x, safe_y
    else:
        # Cross ağı için intersection merkezine yaklaştır
        center_x, center_y = 510, 510
        
        # If outside safe radius, pull back to safe area
        max_distance = 200.0  # Safe radius from center
        distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
        
        if distance > max_distance:
            # Scale back to safe radius
            ratio = max_distance / distance
            safe_x = center_x + (x - center_x) * ratio
            safe_y = center_y + (y - center_y) * ratio
        else:
            safe_x, safe_y = x, y
        
        # Ensure we're on actual roads
        if not is_position_on_intersection_roads(safe_x, safe_y):
            # Snap to nearest road
            if abs(safe_x - center_x) < abs(safe_y - center_y):
                # Closer to horizontal road
                safe_y = center_y  # Snap to horizontal road center
            else:
                # Closer to vertical road  
                safe_x = center_x  # Snap to vertical road center
        
        return safe_x, safe_y


def snap_to_nearest_edge(x, y, network_type="cross"):
    """En yakın edge'e snap et (basit implementasyon)"""
    if network_type == "berlin":
        # Berlin için ana yolları tahmin et (gerçek implementasyonda edge listesi kullanın)
        # Bu basit bir örnek, gerçekte SUMO ağından edge listesi alabilirsiniz
        return x, y  # Şimdilik orijinal pozisyonu döndür
    else:
        # Cross ağı için merkezdeki trafik ışığını döndür
        center_x, center_y = 510, 510
        
        # En yakın ana yola snap et
        if abs(x - center_x) < abs(y - center_y):
            # Yatay yola snap
            return x, center_y
        else:
            # Dikey yola snap
            return center_x, y


def update_gps_vehicles():
    """Tüm GPS araçlarını güncelle - Sadece ışınlama, hareket yok"""
    global gps_index, real_time_gps, current_network_type
    
    # Gerçek zamanlı GPS verisi varsa onu kullan
    if use_real_time and real_time_gps:
        lat, lon = real_time_gps
        print(f"🔴 REAL-TIME GPS: {lat:.6f}, {lon:.6f}")
    elif gps_coordinates and gps_index < len(gps_coordinates):
        # Dosyadan GPS verisi kullan
        lat, lon = gps_coordinates[gps_index]
        print(f"📁 FILE GPS: {lat:.6f}, {lon:.6f}")
    else:
        return  # GPS verisi yok
    
    # Aktif olan tüm GPS araçlarını ışınla (sadece ambulance_gps_0)
    successful_teleports = 0
    for amb_id in range(1):  # Sadece ambulance_gps_0
        vehicle_id = f"ambulance_gps_{amb_id}"
        if vehicle_id in traci.vehicle.getIDList():
            # Ambulansı GPS koordinatına ışınla (hareket etmesin)
            success = safe_move_vehicle(vehicle_id, lat, lon, network_type=current_network_type)
            
            if success:
                successful_teleports += 1
                
                # Ambulans başarıyla ışınlandıysa, trafik ışığı kontrolü yap
                if current_network_type == "cross":
                    check_ambulance_traffic_light_control(vehicle_id)
    
    if successful_teleports > 0:
        print(f"✅ {successful_teleports}/1 ambulans başarıyla ışınlandı ve durduruldu")


def add_real_time_gps_reader():
    """Gerçek zamanlı GPS okuyucu (Serial/Socket için hazır)"""
    # Bu fonksiyon ESP32'den gelen verileri okumak için kullanılabilir
    pass

def detect_network_type():
    """Kullanılan ağ tipini otomatik tespit et ve konfigürasyonu ayarla"""
    global current_network_type
    
    try:
        # Komut satırı argümanlarından kontrol et
        import sys
        for arg in sys.argv:
            if "berli" in arg or "berlin" in arg:
                print("🗺️ Berlin ağı (komut satırından) tespit edildi")
                current_network_type = "berlin"
                return "berlin"
            elif "cross" in arg:
                print("🗺️ Cross ağı (komut satırından) tespit edildi")
                current_network_type = "cross"
                return "cross"
        
        # Cross ağını öncelik ver - GPS ambulans projesi için
        if os.path.exists("data/cross.net.xml"):
            print("🗺️ Cross ağı kullanılacak (GPS ambulans projesi)")
            current_network_type = "cross"
            return "cross"
        elif os.path.exists("data/berli.net.xml"):
            print("🗺️ Berlin ağı dosyası mevcut")
            current_network_type = "berlin"
            return "berlin"
        else:
            print("⚠️ Bilinmeyen ağ tipi, cross varsayılan olarak kullanılacak")
            current_network_type = "cross"
            return "cross"
            
    except Exception as e:
        print(f"⚠️ Ağ tipi tespit hatası: {e}")
        current_network_type = "cross"
        return "cross"

def on_real_time_gps_update(lat, lon):
    """Gerçek zamanlı GPS verisi geldiğinde çağrılan callback - Noise filtreleme ile"""
    global real_time_gps
    
    # GPS noise filtreleme uygula
    filtered_lat, filtered_lon, was_filtered = filter_gps_noise(lat, lon)
    
    # Filtreleme sonucunu logla
    if was_filtered:
        print(f"🔴 GPS NOISE FILTERED: {lat:.8f}, {lon:.8f} -> Konum değişmedi")
        # Eski pozisyonu koru (güncelleme yok)
    else:
        print(f"✅ GPS ACCEPTED: {lat:.8f}, {lon:.8f} -> {filtered_lat:.8f}, {filtered_lon:.8f}")
        # Gerçek zamanlı GPS verisini güncelle
        real_time_gps = (filtered_lat, filtered_lon)
    
    # ESP32'den gelen veri için detaylı log
    if esp32_gps_client:
        status = "🔴 FILTERED" if was_filtered else "✅ ACCEPTED"
        print(f"📡 ESP32 GPS {status}: {lat:.6f}, {lon:.6f}")
    else:
        print(f"🔄 Gerçek zamanlı GPS: {filtered_lat:.6f}, {filtered_lon:.6f}")

def start_real_time_gps(options=None):
    """Gerçek zamanlı GPS okuyucuyu başlat"""
    global use_real_time, esp32_gps_client
    
    # Cross ağı için dosyadan okuma yeterli, ama ESP32 için seçenek sun
    if current_network_type == "cross":
        # Eğer command line'dan GPS source verilmişse, onu kullan
        if options and options.gps_source != "file":
            gps_source = options.gps_source
        else:
            # Cross ağı için kullanıcıya seçenek sun
            print("\n📡 GPS veri kaynağı seçin:")
            print("1. Dosyadan oku (gps-data-2.gpx) [varsayılan]")
            print("2. ESP32 WiFi/HTTP")
            print("3. Serial (ESP32)")
            print("4. Socket (WiFi)")
            
            choice = input("Seçiminiz (1-4) [1]: ").strip() or "1"
            
            if choice == "1":
                gps_source = "file"
            elif choice == "2":
                gps_source = "esp32"
            elif choice == "3":
                gps_source = "serial"
            elif choice == "4":
                gps_source = "socket"
            else:
                gps_source = "file"
                
        # GPS source'a göre başlatma
        if gps_source == "esp32":
            start_esp32_gps(options)
        elif gps_source == "serial":
            start_serial_gps()
        elif gps_source == "socket":
            start_socket_gps()
        else:
            print("📁 Dosyadan GPS verisi kullanılacak (gps-data-2.gpx)")
            use_real_time = False
    else:
        # Berlin ağı için eski davranış
        start_legacy_real_time_gps()

def start_esp32_gps(options=None):
    """ESP32 WiFi/HTTP GPS modunu başlat"""
    global use_real_time, esp32_gps_client
    
    if not esp32_client_available:
        print("❌ ESP32 GPS Client kullanılamıyor, dosyadan okuma moduna geçiliyor")
        use_real_time = False
        return
    
    # IP ve port ayarlarını al
    if options:
        esp32_ip = options.esp32_ip
        esp32_port = options.esp32_port
    else:
        esp32_ip = input("ESP32 IP adresi [192.168.1.100]: ").strip() or "192.168.1.100"
        try:
            esp32_port = int(input("ESP32 HTTP portu [80]: ").strip() or "80")
        except ValueError:
            esp32_port = 80
    
    try:
        print(f"🔗 ESP32'ye bağlanılıyor: {esp32_ip}:{esp32_port}")
        esp32_gps_client = ESP32GPSClient(esp32_ip, esp32_port)
        
        # Test bağlantısı
        if esp32_gps_client.test_connection():
            # Callback'i ayarla
            esp32_gps_client.set_gps_callback(on_real_time_gps_update)
            
            # GPS okumayı başlat
            esp32_gps_client.start_gps_updates()
            use_real_time = True
            print(f"✅ ESP32 WiFi GPS okuyucu başlatıldı: {esp32_ip}:{esp32_port}")
        else:
            print("❌ ESP32'ye bağlanılamadı, dosyadan okuma moduna geçiliyor")
            use_real_time = False
            
    except Exception as e:
        print(f"❌ ESP32 GPS başlatılamadı: {e}")
        print("📁 Dosyadan GPS okuma moduna geçiliyor")
        use_real_time = False

def start_serial_gps():
    """Serial GPS modunu başlat (eski GPS reader ile)"""
    global use_real_time
    
    try:
        # GPS okuyucu modülünü import et (eğer mevcutsa)
        try:
            from gps_reader import GPSReader
            gps_reader_available = True
        except ImportError:
            print("⚠️ GPS Reader modülü bulunamadı")
            gps_reader_available = False
        
        if gps_reader_available:
            port = input("Serial port [COM3]: ").strip() or "COM3"
            gps_reader = GPSReader()
            gps_reader.set_callback(on_real_time_gps_update)
            gps_reader.start_serial_reader(port, 9600)
            use_real_time = True
            print(f"✅ Serial GPS okuyucu başlatıldı: {port}")
        else:
            print("📁 GPS Reader bulunamadı, dosyadan okuma moduna geçiliyor")
            use_real_time = False
            
    except Exception as e:
        print(f"❌ Serial GPS başlatılamadı: {e}")
        print("📁 Dosyadan GPS okuma moduna geçiliyor")
        use_real_time = False

def start_socket_gps():
    """Socket GPS modunu başlat (eski GPS reader ile)"""
    global use_real_time
    
    try:
        # GPS okuyucu modülünü import et (eğer mevcutsa)
        try:
            from gps_reader import GPSReader
            gps_reader_available = True
        except ImportError:
            print("⚠️ GPS Reader modülü bulunamadı")
            gps_reader_available = False
        
        if gps_reader_available:
            port = int(input("Socket port [8888]: ").strip() or "8888")
            gps_reader = GPSReader()
            gps_reader.set_callback(on_real_time_gps_update)
            gps_reader.start_socket_reader("0.0.0.0", port)
            use_real_time = True
            print(f"✅ Socket GPS sunucu başlatıldı: port {port}")
        else:
            print("📁 GPS Reader bulunamadı, dosyadan okuma moduna geçiliyor")
            use_real_time = False
            
    except Exception as e:
        print(f"❌ Socket GPS başlatılamadı: {e}")
        print("📁 Dosyadan GPS okuma moduna geçiliyor")
        use_real_time = False

def start_legacy_real_time_gps():
    """Berlin ağı için eski gerçek zamanlı GPS başlatma davranışı"""
    global use_real_time
    
    try:
        # GPS okuyucu modülünü import et (eğer mevcutsa)
        try:
            from gps_reader import GPSReader
            gps_reader_available = True
        except ImportError:
            print("⚠️ GPS Reader modülü bulunamadı, mock veriler kullanılacak")
            gps_reader_available = False
        
        if gps_reader_available:
            gps_reader = GPSReader()
            gps_reader.set_callback(on_real_time_gps_update)
        
        # Kullanıcıya seçenek sun
        print("\n📡 Gerçek zamanlı GPS modu:")
        print("1. Serial (ESP32)")
        print("2. Socket (WiFi)")
        print("3. Dosyadan oku (varsayılan)")
        
        choice = input("Seçiminiz (1-3) [3]: ").strip() or "3"
        
        if choice == "1" and gps_reader_available:
            port = input("Serial port [COM3]: ").strip() or "COM3"
            gps_reader.start_serial_reader(port, 9600)
            use_real_time = True
            print(f"✅ Serial GPS okuyucu başlatıldı: {port}")
        elif choice == "2" and gps_reader_available:
            port = int(input("Socket port [8888]: ").strip() or "8888")
            gps_reader.start_socket_reader("0.0.0.0", port)
            use_real_time = True
            print(f"✅ Socket GPS sunucu başlatıldı: port {port}")
        else:
            print("📁 Dosyadan GPS verisi kullanılacak")
            
    except Exception as e:
        print(f"❌ Gerçek zamanlı GPS başlatılamadı: {e}")
        print("📁 Dosyadan GPS okuma moduna geçiliyor")

def create_berlin_config():
    """Berlin ağı için SUMO konfigürasyon dosyası oluştur"""
    config_content = """<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="berli.net.xml"/>
        <route-files value="berlin.rou.xml"/>
    </input>
    <output>
        <tripinfo-output value="tripinfo.xml"/>
    </output>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
    <processing>
        <ignore-route-errors value="true"/>
    </processing>
    <routing>
        <device.rerouting.adaptation-steps value="18"/>
        <device.rerouting.adaptation-interval value="10"/>
    </routing>
</configuration>"""
    
    config_file = "data/berlin.sumocfg"
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Berlin konfigürasyonu oluşturuldu: {config_file}")
    return config_file


def generate_berlin_routes():
    """Berlin ağı için route dosyası oluştur - GPS controlled vehicles için"""
    
    # GPS-controlled vehicles için sadece vehicle type tanımları yeterli
    # Route'lar moveToXY ile dinamik olarak kontrol edilecek
    route_content = """<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    <!-- Vehicle Types for Berlin Network -->
    <vType id="ambulance" accel="2.0" decel="6.0" sigma="0.1" length="6" minGap="2" maxSpeed="50" 
           guiShape="emergency" color="1,0,0" emergencyDecel="8.0"/>
    <vType id="passenger" accel="1.5" decel="4.5" sigma="0.5" length="4.5" minGap="2.5" maxSpeed="35" 
           guiShape="passenger"/>
           
    <!-- GPS-guided ambulances will be added dynamically via TraCI -->
    <!-- No pre-defined routes needed as vehicles are controlled by moveToXY -->
</routes>"""
    
    route_file = "data/berlin.rou.xml"
    with open(route_file, 'w') as f:
        f.write(route_content)
    
    print(f"✅ Berlin rotaları oluşturuldu: {route_file}")
    print("ℹ️  GPS ambulanslar TraCI ile dinamik olarak eklenecek")
    return route_file


def add_gps_vehicles_to_simulation():
    """GPS kontrollü ambulansları simülasyona dinamik olarak ekle"""
    try:
        # Ambulans sayısı (sadece 1 - ambulance_gps_0)
        num_ambulances = 1
        
        for amb_id in range(num_ambulances):
            vehicle_id = f"ambulance_gps_{amb_id}"
            
            # Berlin ağının ortasında bir başlangıç pozisyonu
            start_x = 5000.0 + (amb_id * 100)  # Ambulansları biraz aralıklı yerleştir
            start_y = 5000.0 + (amb_id * 100)
            
            # Ambulansı simülasyona ekle
            traci.vehicle.add(
                vehID=vehicle_id,
                routeID="",  # Boş route - GPS ile kontrol edilecek
                typeID="ambulance",
                depart="now"
            )
            
            # Başlangıç pozisyonunu ayarla
            traci.vehicle.moveToXY(
                vehicle_id,
                "",  # Edge ID
                0,   # Lane index
                start_x,
                start_y,
                angle=0,
                keepRoute=0
            )
            
            print(f"✅ {vehicle_id} eklendi: ({start_x:.0f}, {start_y:.0f})")
            
        print(f"🚑 {num_ambulances} GPS ambulans simülasyona eklendi (sadece ambulance_gps_0)")
        return True
        
    except Exception as e:
        print(f"❌ GPS ambulans ekleme hatası: {e}")
        return False


def calculate_distance(pos1, pos2):
    """İki pozisyon arasındaki Öklid mesafesini hesapla"""
    import math
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)


def check_ambulance_traffic_light_control(vehicle_id):
    """
    Ambulansın kavşağa yaklaştığını kontrol et ve gerekirse trafik ışığını yeşile çevir
    """
    try:
        # Ambulansın mevcut pozisyonunu al
        ambulance_pos = traci.vehicle.getPosition(vehicle_id)
        
        # Kavşak merkezini tanımla (cross ağı için)
        intersection_center = (510, 510)
        intersection_radius = 75  # 75 metre yarıçap - Daha geç ışık aktivasyonu
        
        # Ambulansın kavşağa olan mesafesini hesapla
        distance_to_intersection = calculate_distance(ambulance_pos, intersection_center)
        
        # Trafik ışığı logları geçici olarak devre dışı
        # print(f"🚑 {vehicle_id} kavşağa mesafe: {distance_to_intersection:.1f}m")
        
        # Eğer ambulans kavşağa yakınsa (150m içindeyse)
        if distance_to_intersection <= intersection_radius:
            # Trafik ışığı logları geçici olarak devre dışı
            # print(f"⚠️ {vehicle_id} kavşağa yaklaştı! Trafik ışığı kontrolü başlatılıyor...")
            
            # Mevcut trafik ışığı durumunu kontrol et
            current_phase = traci.trafficlight.getPhase("0")
            traffic_state = traci.trafficlight.getRedYellowGreenState("0")
            
            # Trafik ışığı logları geçici olarak devre dışı
            # print(f"🚦 Mevcut trafik ışığı durumu - Faz: {current_phase}, Durum: {traffic_state}")
            
            # Eğer trafik ışığı yeşil değilse, yeşile çevir
            if current_phase != 2:  # Faz 2 = Doğu-Batı yeşil
                # Trafik ışığı logları geçici olarak devre dışı
                # print("🟢 Ambulans için trafik ışığı yeşile çevriliyor...")
                traci.trafficlight.setPhase("0", 2)
                
                # ESP32'ye sinyal gönder (mock)
                send_signal_to_esp32("GREEN_LIGHT_ACTIVATED", vehicle_id)
                
                # Kontrol aktif durumunu işaretle
                mark_ambulance_control_active(vehicle_id)
            else:
                # Trafik ışığı logları geçici olarak devre dışı
                # print("✅ Trafik ışığı zaten yeşil - Ambulans geçiş yapabilir")
                
                # ESP32'ye ambulans geçiş sinyali gönder
                send_signal_to_esp32("AMBULANCE_PASSING", vehicle_id)
        
        # Ambulans kavşaktan uzaklaştığında normal trafik akışına dön
        elif distance_to_intersection > intersection_radius * 2.0:  # 150m dışında reset
            reset_normal_traffic_flow(vehicle_id)
        
        # ZORLA RESET: Çok uzaktaki ambulanslar için (200m+)
        elif distance_to_intersection > 200.0:
            # Çok uzakta ise zorla kontrol durumunu sıfırla
            global ambulance_control_status
            if vehicle_id in ambulance_control_status:
                ambulance_control_status[vehicle_id] = False
            
    except Exception as e:
        print(f"❌ Trafik ışığı kontrolü hatası {vehicle_id}: {e}")


def send_signal_to_esp32(signal_type, vehicle_id):
    """
    ESP32 devresine sinyal gönder (HTTP ile gerçek implementasyon)
    Trafik LED'i kontrol eder
    """
    import time
    import requests
    
    timestamp = time.strftime("%H:%M:%S")
    
    # ESP32 LED Controller IP adresi (otomatik tespit edilecek)
    esp32_led_ip = "192.168.1.107"  # İkinci ESP32'nizin IP'sini buraya yazın
    
    try:
        if signal_type == "GREEN_LIGHT_ACTIVATED":
            # Ambulans için yeşil ışık - Kırmızı LED'i söndür
            response = requests.post(f"http://{esp32_led_ip}/ambulance/green", timeout=2)
            print(f"📡 ESP32 LED SİGNALİ [{timestamp}]: KIRMIZI LED SÖNDÜRÜLDÜ - Ambulans yeşil ışık")
            print(f"    └── Ambulans ID: {vehicle_id}")
            print(f"    └── ESP32 Response: {response.status_code}")
            
        elif signal_type == "AMBULANCE_PASSING":
            # Ambulans geçiş yapıyor (ek sinyal gerekmez, LED zaten söndürülmüş)
            print(f"📡 ESP32 SİGNALİ [{timestamp}]: Ambulans geçiş yapıyor (LED söndürülmüş durumda)")
            print(f"    └── Ambulans ID: {vehicle_id}")
            
        elif signal_type == "NORMAL_TRAFFIC_RESUMED":
            # Normal trafik - Kırmızı LED'i yak
            response = requests.post(f"http://{esp32_led_ip}/ambulance/normal", timeout=2)
            print(f"📡 ESP32 LED SİGNALİ [{timestamp}]: KIRMIZI LED YAKILDI - Normal trafik")
            print(f"    └── ESP32 Response: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ESP32 LED bağlantı hatası [{timestamp}]: {e}")
        print(f"    └── Offline mode: {signal_type} sinyali gönderilmedi")
    except Exception as e:
        print(f"❌ ESP32 LED genel hatası [{timestamp}]: {e}")


# Global ambulans kontrol durumu
ambulance_control_status = {}


def mark_ambulance_control_active(vehicle_id):
    """Ambulansın trafik kontrolünü aktif olarak işaretle"""
    global ambulance_control_status
    ambulance_control_status[vehicle_id] = True
    print(f"🎛️ {vehicle_id} trafik kontrolü aktif edildi")


def reset_normal_traffic_flow(vehicle_id):
    """
    Ambulans kavşaktan uzaklaştığında normal trafik akışına dön
    """
    global ambulance_control_status
    
    # Bu ambulans için kontrol aktifse
    if vehicle_id in ambulance_control_status and ambulance_control_status[vehicle_id]:
        print(f"� {vehicle_id} kavşaktan uzaklaştı - Normal trafik akışı başlatılıyor")
        
        # ESP32'ye normal duruma dönüş sinyali gönder
        send_signal_to_esp32("NORMAL_TRAFFIC_RESUMED", vehicle_id)
        
        # Bu ambulans için kontrol durumunu kaldır
        ambulance_control_status[vehicle_id] = False


def is_ambulance_traffic_control_active():
    """
    Herhangi bir ambulansın trafik ışığı kontrolü aktif mi kontrol et
    """
    global ambulance_control_status
    return any(ambulance_control_status.values()) if ambulance_control_status else False


def monitor_all_ambulances_for_traffic_control():
    """
    Tüm ambulansları izle ve trafik ışığı kontrolü yap
    Bu fonksiyon ana simülasyon döngüsünden çağrılacak
    """
    if current_network_type != "cross":
        return  # Sadece cross ağında çalış
    
    ambulance_vehicles = [vid for vid in traci.vehicle.getIDList() if "ambulance" in vid]
    
    for vehicle_id in ambulance_vehicles:
        try:
            check_ambulance_traffic_light_control(vehicle_id)
        except Exception as e:
            print(f"❌ Ambulans monitoring hatası {vehicle_id}: {e}")


def find_nearest_traffic_light(lon, lat, network_type="cross"):
    """Verilen konuma en yakın trafik ışığını bul"""
    try:
        if network_type == "berlin":
            # Berlin ağı için en yakın trafik ışığını bul
            # Bu örnekte basitçe sabit bir TLS ID döndürüyoruz
            return "0"
        else:
            # Cross ağı için merkezdeki trafik ışığını döndür
            return "0"
    except Exception as e:
        print(f"❌ Trafik ışığı bulunamadı: {e}")
        return None


def sumo_to_gps_coords(x, y, network_type="cross"):
    """SUMO koordinatlarını GPS koordinatlarına dönüştür - Çoklu ağ destekli"""
    
    if network_type == "berlin":
        # Berlin ağı için ters dönüşüm
        min_lon, min_lat = 30.494791, 37.406898
        max_lon, max_lat = 30.614099, 37.515896
        
        min_x, min_y = 0.0, 0.0
        max_x, max_y = 10604.93, 9947.54
        
        # Ters lineer dönüşüm
        lon = (x - min_x) / (max_x - min_x) * (max_lon - min_lon) + min_lon
        lat = (y - min_y) / (max_y - min_y) * (max_lat - min_lat) + min_lat
        
        return lat, lon
    
    else:
        # Cross network için ters dönüşüm
        gps_lat_min, gps_lat_max = 37.0665, 37.0675
        gps_lon_min, gps_lon_max = 30.2085, 30.2105
        
        active_x_min, active_x_max = 400.0, 620.0
        active_y_min, active_y_max = 400.0, 620.0
        
        # Ters lineer dönüşüm
        lon = ((x - active_x_min) / (active_x_max - active_x_min)) * (gps_lon_max - gps_lon_min) + gps_lon_min
        lat = ((y - active_y_min) / (active_y_max - active_y_min)) * (gps_lat_max - gps_lat_min) + gps_lat_min
        
        return lat, lon


# this is the main entry point of this script
if __name__ == "__main__":
    options = get_options()

    # Ağ tipini tespit et
    network_type = detect_network_type()
    print(f"🎯 Kullanılacak ağ: {network_type}")

    # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    # first, generate the route file for this simulation
    generate_routefile() #rota dosyasını oluştur
    
    # Cross ağı için gerçek zamanlı GPS sistemini başlatma
    if network_type == "cross":
        print("📁 Cross ağı - GPS veri kaynağı seçilebilir")
        start_real_time_gps(options)
    else:
        # Gerçek zamanlı GPS sistemini başlat (sadece Berlin için)
        start_real_time_gps(options)

    # Ağ tipine göre uygun konfigürasyon dosyasını seç
    if network_type == "berlin":
        if os.path.exists("data/berlin.sumocfg"):
            config_file = "data/berlin.sumocfg"
        else:
            # Berlin için temel konfigürasyon oluştur
            config_file = create_berlin_config()
    else:
        config_file = "data/cross.sumocfg"

    print(f"🚗 SUMO başlatılıyor: {config_file}")
    
    # this is the normal way of using traci. sumo is started as a
    # subprocess and then the python script connects and runs
    traci.start([sumoBinary, "-c", config_file,
                             "--tripinfo-output", "tripinfo.xml"])
    run()
