# ESP32 GPS Ambulance Server - Kurulum ve Kullanım Kılavuzu

## 🎯 Genel Bakış

Bu proje ESP32'yi GPS modülü ile birlikte kullanarak SUMO trafik simülasyonuna gerçek zamanlı GPS verisi sağlar. ESP32 HTTP server olarak çalışır ve Python SUMO scripti ile iletişim kurar.

## 🔧 Gerekli Malzemeler

### Temel Kurulum:
- **ESP32 Development Board** (ESP32-WROOM-32 önerilen)
- **USB Kablo** (programlama ve güç için)
- **WiFi Bağlantısı**

### Gelişmiş Kurulum (GPS ile):
- **GPS Modülü** (NEO-6M, NEO-8M önerilen)
- **LED** (trafik ışığı sinyali için)
- **Buzzer** (ambulans sinyali için)
- **Breadboard ve Jumper kablolar**

## 📐 Hardware Bağlantıları

### ESP32 Pin Bağlantıları:

```
ESP32 Pin    ->    Bağlantı
=================================
GPIO 2       ->    LED (Anode)
GPIO 4       ->    Buzzer (+)
GPIO 0       ->    Test Button (dahili)
GPIO 16      ->    GPS RX (GPS TX'e)
GPIO 17      ->    GPS TX (GPS RX'e)
3.3V         ->    GPS VCC, LED/Buzzer (+)
GND          ->    GPS GND, LED/Buzzer (-)
```

### GPS Modülü Bağlantıları:
```
GPS Pin      ->    ESP32 Pin
=================================
VCC          ->    3.3V
GND          ->    GND
TX           ->    GPIO 16 (RX2)
RX           ->    GPIO 17 (TX2)
```

## 💻 Arduino IDE Kurulumu

### 1. Arduino IDE Yükleme
- [Arduino IDE](https://www.arduino.cc/en/software) indir ve yükle

### 2. ESP32 Board Package Ekleme
1. Arduino IDE'yi aç
2. **File > Preferences** git
3. "Additional Boards Manager URLs" alanına ekle:
   ```
   https://dl.espressif.com/dl/package_esp32_index.json
   ```
4. **Tools > Board > Boards Manager** git
5. "esp32" ara ve yükle

### 3. Kütüphane Kurulumu

#### Gerekli Kütüphaneler:
- **WiFi** (ESP32 ile birlikte gelir)
- **WebServer** (ESP32 ile birlikte gelir)
- **ArduinoJson** (gelişmiş versiyon için)

#### ArduinoJson Kurulumu:
1. **Sketch > Include Library > Manage Libraries**
2. "ArduinoJson" ara
3. Benoit Blanchon tarafından geliştirilen versiyonu yükle

## 🚀 Kod Yükleme ve Konfigürasyon

### 1. Kod Versiyonları

**Basit Versiyon (`ESP32_GPS_Simple.ino`):**
- GPS modülü gerektirmez
- Sadece temel kütüphaneler
- Test koordinatları ile çalışır
- Yeni başlayanlar için ideal

**Gelişmiş Versiyon (`ESP32_GPS_Complete.ino`):**
- Gerçek GPS modülü desteği
- ArduinoJson kütüphanesi gerekir
- Web interface ile tam kontrol
- Profesyonel kullanım için

### 2. WiFi Konfigürasyonu

Kod dosyasında bu satırları düzenle:

```cpp
// WiFi Ayarları - BURAYA KENDİ BİLGİLERİNİZİ YAZIN
const char* ssid = "YOUR_WIFI_NAME";        // WiFi ağ adınız
const char* password = "YOUR_WIFI_PASSWORD"; // WiFi şifreniz
```

### 3. Kod Yükleme

1. ESP32'yi USB ile bağla
2. Arduino IDE'de **Tools > Board > ESP32 Arduino > ESP32 Dev Module** seç
3. **Tools > Port** menüsünden doğru COM portunu seç
4. Kodu aç ve **Upload** butonuna bas
5. Serial Monitor'ü aç (115200 baud)

## 📱 Kullanım

### 1. ESP32 Başlatma

1. ESP32'yi güçlendir
2. Serial Monitor'dan IP adresini not al
3. Web browser'da IP adresine git

Örnek output:
```
📶 WiFi'ye bağlanılıyor: YOUR_WIFI
✅ WiFi bağlandı!
📍 IP Adresi: 192.168.1.100
🌐 HTTP Server başlatıldı!
```

### 2. Web Interface

Browser'da ESP32'nin IP adresine git (örn: `http://192.168.1.100`)

Web interface özellikleri:
- **Gerçek zamanlı GPS verisi**
- **LED kontrol butonları**
- **Buzzer test**
- **Sistem durumu**
- **API endpoint linkleri**

### 3. SUMO Entegrasyonu

ESP32 hazır olduktan sonra SUMO scriptini çalıştır:

```bash
# ESP32 IP adresini kullan
python runner.py --gps-source esp32 --esp32-ip 192.168.1.100

# Port belirtmek için
python runner.py --gps-source esp32 --esp32-ip 192.168.1.100 --esp32-port 80
```

## 🔍 API Endpoints

ESP32 aşağıdaki HTTP endpoint'leri sağlar:

### GPS Verisi
```
GET /gps
Response: {
  "latitude": 41.008200,
  "longitude": 28.978400,
  "valid": true,
  "satellites": 8,
  "timestamp": "20/01/24 10:30:00"
}
```

### Sistem Durumu
```
GET /status
Response: {
  "device": "ESP32_GPS_001",
  "wifi_connected": true,
  "ip_address": "192.168.1.100",
  "uptime": 123456,
  "gps_valid": true
}
```

### Kontrol Komutları
```
GET /led_on      - LED'i aç (trafik ışığı sinyali)
GET /led_off     - LED'i kapat
GET /buzzer      - Buzzer çal (ambulans sinyali)
GET /restart     - ESP32'yi yeniden başlat
```

## 🧪 Test Etme

### 1. ESP32 Bağlantı Testi
```bash
# Ping testi
ping 192.168.1.100

# HTTP testi
curl http://192.168.1.100/status
```

### 2. GPS Veri Testi
```bash
# GPS endpoint testi
curl http://192.168.1.100/gps
```

### 3. SUMO Entegrasyon Testi
```bash
# Integration test script
python test_esp32_integration.py
```

## 🔧 Sorun Giderme

### WiFi Bağlantı Sorunları

**Problem:** ESP32 WiFi'ye bağlanamıyor
**Çözüm:**
- WiFi SSID ve şifresini kontrol et
- 2.4GHz ağ kullandığından emin ol (5GHz desteklenmez)
- Router menzili içinde ol

**Problem:** IP adresi değişiyor
**Çözüm:**
- Router'da ESP32 MAC adresine sabit IP ver
- Serial Monitor'dan her seferinde IP'yi kontrol et

### GPS Sorunları

**Problem:** GPS verisi alınamıyor
**Çözüm:**
- GPS modülü bağlantılarını kontrol et
- GPS anteni açık havada test et
- GPS lock için 2-5 dakika bekle

**Problem:** GPS verisi yanlış
**Çözüm:**
- GPS modülü kalibrasyonunu kontrol et
- Test modunu kullan (`/test_mode_on`)

### SUMO Bağlantı Sorunları

**Problem:** SUMO ESP32'ye bağlanamıyor
**Çözüm:**
```bash
# ESP32 durumunu kontrol et
python -c "import requests; print(requests.get('http://192.168.1.100/status').json())"

# Firewall kontrolü
# Windows Firewall'da Python'a izin ver
```

**Problem:** GPS verisi güncellenmeme
**Çözüm:**
- ESP32 Serial Monitor'u kontrol et
- Test modunu aktif et
- Network latency'sini kontrol et

## 📊 Performans Optimizasyonu

### WiFi Sinyali İyileştirme
- ESP32'yi router'a yaklaştır
- WiFi anteni kaliteli olan ESP32 kullan
- 2.4GHz kanal trafiğini azalt

### GPS Hassasiyeti Artırma
- External GPS anteni kullan
- GPS modülünü metal yüzeylerden uzak tut
- Clear sky view sağla

### HTTP Response Hızı
- JSON response boyutunu minimize et
- Keep-alive connections kullan
- Cache headers ekle

## 🔐 Güvenlik

### Ağ Güvenliği
- WPA2/WPA3 şifrelemeli WiFi kullan
- ESP32'yi guest network'e bağla
- Firewall kuralları ekle

### API Güvenliği
- HTTP Basic Auth ekle (isteğe bağlı)
- HTTPS kullan (gelişmiş kurulum)
- Rate limiting uygula

## 📈 Gelişmiş Özellikler

### OTA (Over-The-Air) Update
```cpp
#include <ArduinoOTA.h>
// OTA setup kodları...
```

### MQTT Desteği
```cpp
#include <PubSubClient.h>
// MQTT client kodları...
```

### SD Card Logging
```cpp
#include <SD.h>
// GPS log kaydetme...
```

## 🎯 Kullanım Senaryoları

### 1. Laboratuvar Testi
- ESP32 + Basit kod
- Test koordinatları
- WiFi bağlantısı

### 2. Sahada Test
- ESP32 + GPS modülü
- Gerçek koordinatlar
- Portable power bank

### 3. Prodüksiyon
- ESP32 + GPS + Enclosure
- 24/7 çalışma
- Remote monitoring

## 📞 Destek ve Geliştirme

### Debugging
```cpp
// Serial debug açma
#define DEBUG 1
#if DEBUG
  Serial.println("Debug message");
#endif
```

### Log Seviyeleri
- **INFO:** Normal operasyon
- **DEBUG:** Detaylı bilgi
- **ERROR:** Hata durumları

### Kod Geliştirme
- GitHub repository kullan
- Version control yap
- Test-driven development

---

## ✅ Hızlı Başlangıç Checklist

- [ ] ESP32 hardware hazır
- [ ] Arduino IDE kurulu
- [ ] ESP32 board package eklendi
- [ ] WiFi bilgileri kod içinde güncellendi
- [ ] Kod başarıyla yüklendi
- [ ] Serial Monitor'da IP adresi görünüyor
- [ ] Web interface erişilebiliyor
- [ ] SUMO script ESP32'ye bağlanabiliyor
- [ ] GPS verisi akıyor

**🎉 Tebrikler! ESP32 GPS Ambulance Server çalışıyor!**
