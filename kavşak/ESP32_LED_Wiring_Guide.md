# ESP32 Traffic LED Controller - Hardware Bağlantıları

## 🔴 Ana Kırmızı LED Bağlantısı (Zorunlu)
```
ESP32 GPIO 2 -----> LED Anot (+)
LED Katot (-) ----> 220Ω Resistor ----> GND
```

## 💡 Status LED (Opsiyonel - sistem durumu için)
```
ESP32 GPIO 5 -----> Status LED Anot (+)
Status LED Katot (-) ----> 220Ω Resistor ----> GND
```

## 🔊 Buzzer (Opsiyonel - ambulans sinyali için)
```
ESP32 GPIO 4 -----> Buzzer (+)
Buzzer (-) --------> GND
```

## 📋 Tam Bağlantı Listesi

| ESP32 Pin | Bağlantı | Açıklama |
|-----------|----------|----------|
| GPIO 2 | Kırmızı LED Anot | Ana trafik LED'i |
| GPIO 5 | Status LED Anot | Sistem durum LED'i |
| GPIO 4 | Buzzer (+) | Ambulans ses sinyali |
| GND | Tüm GND'ler | Ortak toprak |
| 3.3V | (Kullanılmıyor) | Power |

## 🔧 Malzeme Listesi

### Zorunlu:
- 1x ESP32 DevKit
- 1x Kırmızı LED (5mm)
- 1x 220Ω Resistor
- Breadboard ve jumper kablolar

### Opsiyonel:
- 1x Mavi/Yeşil LED (status için)
- 1x 220Ω Resistor (status LED için)
- 1x Buzzer (5V toleranslı)

## ⚡ Güç Tüketimi
- ESP32: ~240mA (WiFi aktif)
- LED'ler: ~20mA (her biri)
- Buzzer: ~30mA
- **Toplam**: ~310mA (USB ile beslenebilir)

## 🔧 Kurulum Adımları

1. **Hardware bağlantısını yap**
2. **Arduino IDE'de WiFi bilgilerini düzenle:**
   ```cpp
   const char* ssid = "WIFI_AGINIZIN_ADI";
   const char* password = "WIFI_SIFRENIZ";
   ```
3. **ESP32'ye kodu yükle**
4. **Serial Monitor'den IP adresini not al**
5. **SUMO runner.py'de ESP32 IP'sini güncelle**

## 🌐 Test Edilecek Endpoint'ler

### Browser'da test:
- `http://[ESP32_IP]/` - Web arayüzü
- `http://[ESP32_IP]/status` - JSON status

### SUMO otomatik kullanacak:
- `POST http://[ESP32_IP]/ambulance/green` - LED söner
- `POST http://[ESP32_IP]/ambulance/normal` - LED yanar
