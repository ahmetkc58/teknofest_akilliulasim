# ESP32 GPS Integration for SUMO Ambulance Simulation

## Overview
Bu entegrasyon, ESP32 mikrodenetleyicisinden WiFi/HTTP üzerinden gerçek zamanlı GPS verilerini alarak SUMO trafik simülasyonunda ambulans pozisyonunu kontrol etmeyi sağlar.

## Dosya Yapısı
```
kavşak/
├── runner.py              # Ana SUMO simülasyon dosyası (ESP32 entegrasyonlu)
├── esp32_gps_client.py    # ESP32 HTTP GPS client
├── test_esp32_integration.py  # Entegrasyon test aracı
├── gps-data-2.gpx         # Varsayılan GPS dosyası
└── data/                  # SUMO konfigürasyon dosyaları
```

## ESP32 Tarafı Gereksinimleri

### HTTP Endpoint'ler
ESP32'nizde aşağıdaki HTTP endpoint'ler olmalı:

1. **GET /gps** - GPS verisini döndürür
   ```json
   {
     "latitude": 41.0082,
     "longitude": 28.9784,
     "valid": true,
     "timestamp": "2024-01-20T10:30:00Z"
   }
   ```

2. **GET /status** - Cihaz durumunu döndürür
   ```json
   {
     "status": "ok",
     "gps_connected": true,
     "wifi_connected": true
   }
   ```

### Arduino Kodu Örneği
```cpp
#include <WiFi.h>
#include <WebServer.h>
#include <SoftwareSerial.h>

WebServer server(80);

void setup() {
  // WiFi bağlantısı
  WiFi.begin("SSID", "PASSWORD");
  
  // HTTP endpoint'leri
  server.on("/gps", handleGPS);
  server.on("/status", handleStatus);
  server.begin();
}

void handleGPS() {
  // GPS verisini oku ve JSON döndür
  server.send(200, "application/json", 
    "{\"latitude\":41.0082,\"longitude\":28.9784,\"valid\":true}");
}

void handleStatus() {
  server.send(200, "application/json", 
    "{\"status\":\"ok\",\"gps_connected\":true}");
}
```

## Kullanım Yöntemleri

### 1. Komut Satırından Başlatma

#### ESP32 WiFi/HTTP modunda:
```bash
python runner.py --gps-source esp32 --esp32-ip 192.168.1.100 --esp32-port 80
```

#### GUI olmadan:
```bash
python runner.py --nogui --gps-source esp32 --esp32-ip 192.168.4.1
```

#### Dosyadan GPS verisi (varsayılan):
```bash
python runner.py --gps-source file
```

### 2. İnteraktif Modda

Program normal şekilde başlatıldığında:
```bash
python runner.py
```

Cross ağı tespit edildiğinde kullanıcıya seçenek sunulur:
```
📡 GPS veri kaynağı seçin:
1. Dosyadan oku (gps-data-2.gpx) [varsayılan]
2. ESP32 WiFi/HTTP
3. Serial (ESP32)
4. Socket (WiFi)

Seçiminiz (1-4) [1]: 2
```

Seçenek 2'yi seçtikten sonra:
```
ESP32 IP adresi [192.168.1.100]: 192.168.4.1
ESP32 HTTP portu [80]: 80
```

## Test Araçları

### 1. Entegrasyon Testi
```bash
python test_esp32_integration.py
```

Bu test:
- ESP32 client modülünün import edilebilirliğini kontrol eder
- Runner.py fonksiyonlarıyla entegrasyonu test eder
- GPS koordinat dönüşümünü doğrular

### 2. ESP32 Standalone Test
```bash
python esp32_gps_client.py
```

Bu test:
- ESP32'ye doğrudan bağlantı kurar
- GPS endpoint'lerini test eder
- Gerçek zamanlı veri akışını gösterir

## Ağ Konfigürasyonu

### ESP32 Access Point Modunda
```cpp
WiFi.softAP("ESP32_GPS", "password123");
IPAddress IP = WiFi.softAPIP();  // Genelde 192.168.4.1
```
Runner parametresi: `--esp32-ip 192.168.4.1`

### ESP32 Station Modunda
```cpp
WiFi.begin("WiFi_SSID", "WiFi_Password");
// DHCP ile IP alır, örn: 192.168.1.100
```
Runner parametresi: `--esp32-ip 192.168.1.100`

## Simülasyon Davranışı

### GPS Koordinat Dönüşümü
- ESP32'den gelen GPS koordinatları (enlem/boylam) SUMO koordinatlarına (x/y) dönüştürülür
- Cross ağı için sabit doğrusal rota kullanılır: X(450→570), Y=510
- Ambulans smooth ve tahmin edilebilir şekilde hareket eder

### Güncelleme Sıklığı
- ESP32'den 1 saniyede bir GPS verisi çekilir
- SUMO simülasyonunda her 15 adımda bir ambulans pozisyonu güncellenir
- Bu, stabilite ve performans dengesi sağlar

### Hata Durumları
- ESP32'ye bağlanılamazsa otomatik olarak dosya moduna geçer
- Bağlantı kesilirse son bilinen pozisyonda kalır
- Geçersiz GPS verisi durumunda önceki konum kullanılır

## Debug ve Monitoring

### Terminal Çıktısı
```
📡 ESP32 GPS Client hazırlandı: http://192.168.1.100:80
🔗 ESP32'ye bağlanılıyor: 192.168.1.100:80
✅ ESP32 bağlantı testi başarılı
✅ GPS callback fonksiyonu ayarlandı
✅ ESP32 WiFi GPS okuyucu başlatıldı: 192.168.1.100:80
📡 ESP32 GPS: 41.008200, 28.978400
🎯 GPS Mapping Debug #1: ...
```

### CSV Export
Ambulans pozisyonları simülasyon sonunda CSV dosyasına aktarılır:
```
step,vehicle_id,sumo_x,sumo_y,gps_lat,gps_lon
10,ambulance_0,450.0,510.0,41.0082,28.9784
25,ambulance_0,455.2,510.0,41.0083,28.9785
...
```

## Sorun Giderme

### 1. ESP32'ye Bağlanılamıyor
- ESP32'nin WiFi'ye bağlı olduğunu kontrol edin
- IP adresinin doğru olduğunu kontrol edin
- HTTP server'ın çalıştığını kontrol edin
- Firewall ayarlarını kontrol edin

### 2. GPS Verisi Gelmiyor
- ESP32'nin GPS modülünü okuduğunu kontrol edin
- /gps endpoint'inin çalıştığını test edin
- GPS anteninin açık alanda olduğunu kontrol edin

### 3. Simülasyonda Ambulans Hareket Etmiyor
- GPS verilerinin geçerli range'de olduğunu kontrol edin
- Cross ağının yüklendiğini kontrol edin
- Ambulans'ın başlatıldığını kontrol edin (10. saniye)

## Genişletme İmkanları

1. **Çoklu Ambulans**: Birden fazla ESP32 cihazı desteklemek
2. **Dinamik Routing**: GPS verilerine göre rotayı değiştirmek
3. **Sensör Entegrasyonu**: Hız, ivme sensörlerini eklemek
4. **WebSocket**: Daha hızlı veri akışı için WebSocket kullanmak
5. **Harita Entegrasyonu**: Gerçek harita koordinatlarıyla çalışmak
