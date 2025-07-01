/*
 * ESP32 GPS to SUMO Traffic Control System
 * 
 * Bu kod ESP32'yi GPS modülü ile birlikte kullanarak:
 * 1. WiFi'ye bağlanır
 * 2. GPS koordinatlarını okur
 * 3. HTTP server açar
 * 4. SUMO simülasyonuna koordinat gönderir
 * 5. Trafik ışığı kontrolü için LED/Buzzer sinyalleri alır
 */

#include <WiFi.h>
#include <WebServer.h>
#include <SoftwareSerial.h>
#include <ArduinoJson.h>

// WiFi Ayarları - KENDİ AĞIN BİLGİLERİNİ GİR
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// GPS Modülü (Neo-6M gibi)
SoftwareSerial gpsSerial(16, 17); // RX, TX pinleri

// Web Server
WebServer server(80);

// Pin Tanımlamaları
const int LED_PIN = 2;        // Trafik ışığı LED'i
const int BUZZER_PIN = 4;     // Ambulans buzzer'ı
const int STATUS_LED = 5;     // Durum LED'i

// GPS Değişkenleri
float currentLat = 0.0;
float currentLon = 0.0;
bool gpsValid = false;
unsigned long lastGPSUpdate = 0;
unsigned long lastSendTime = 0;

// Sistem Durumu
bool ambulanceActive = false;
bool trafficControlActive = false;

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(9600);
  
  // Pin modları
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);
  
  // Başlangıç sinyali
  digitalWrite(STATUS_LED, HIGH);
  delay(1000);
  digitalWrite(STATUS_LED, LOW);
  
  Serial.println("🚑 ESP32 GPS Ambulans Sistemi Başlatılıyor...");
  
  // WiFi Bağlantısı
  connectToWiFi();
  
  // HTTP Server Routes
  setupWebServer();
  
  Serial.println("✅ Sistem hazır! GPS verileri SUMO'ya gönderilecek.");
  Serial.print("📡 IP Adresi: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  server.handleClient();
  
  // GPS verilerini oku
  readGPS();
  
  // Her 2 saniyede bir SUMO'ya GPS gönder (ambulans aktifse)
  if (ambulanceActive && millis() - lastSendTime > 2000) {
    sendGPSToSUMO();
    lastSendTime = millis();
  }
  
  // Durum LED'i yanıp sönsün
  blinkStatusLED();
  
  delay(100);
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("WiFi'ye bağlanıyor");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("✅ WiFi bağlantısı başarılı!");
    Serial.print("📡 IP Adresi: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("");
    Serial.println("❌ WiFi bağlantısı başarısız!");
  }
}

void setupWebServer() {
  // Ana sayfa - sistem durumu
  server.on("/", handleRoot);
  
  // GPS verilerini döndür
  server.on("/gps", HTTP_GET, handleGPSData);
  
  // Ambulans durumunu al
  server.on("/ambulance/status", HTTP_GET, handleAmbulanceStatus);
  
  // Ambulans aktif/pasif
  server.on("/ambulance/activate", HTTP_POST, handleAmbulanceActivate);
  server.on("/ambulance/deactivate", HTTP_POST, handleAmbulanceDeactivate);
  
  // Trafik ışığı kontrolü (SUMO'dan gelen komutlar)
  server.on("/traffic/led", HTTP_POST, handleTrafficLED);
  server.on("/traffic/buzzer", HTTP_POST, handleTrafficBuzzer);
  
  // CORS headers
  server.enableCORS(true);
  
  server.begin();
  Serial.println("🌐 HTTP Server başlatıldı (Port 80)");
}

void handleRoot() {
  String html = "<!DOCTYPE html><html><head><title>ESP32 GPS Ambulans</title></head><body>";
  html += "<h1>🚑 ESP32 GPS Ambulans Sistemi</h1>";
  html += "<h2>📍 GPS Durumu</h2>";
  html += "<p><strong>Konum:</strong> " + String(currentLat, 6) + ", " + String(currentLon, 6) + "</p>";
  html += "<p><strong>GPS Geçerli:</strong> " + String(gpsValid ? "✅ Evet" : "❌ Hayır") + "</p>";
  html += "<h2>🚨 Ambulans Durumu</h2>";
  html += "<p><strong>Aktif:</strong> " + String(ambulanceActive ? "✅ Evet" : "❌ Hayır") + "</p>";
  html += "<p><strong>Trafik Kontrolü:</strong> " + String(trafficControlActive ? "✅ Aktif" : "❌ Pasif") + "</p>";
  html += "<h2>🔧 Kontroller</h2>";
  html += "<button onclick=\"activateAmbulance()\">Ambulans Aktif</button> ";
  html += "<button onclick=\"deactivateAmbulance()\">Ambulans Pasif</button><br><br>";
  html += "<button onclick=\"testLED()\">LED Test</button> ";
  html += "<button onclick=\"testBuzzer()\">Buzzer Test</button>";
  html += "<script>";
  html += "function activateAmbulance() { fetch('/ambulance/activate', {method: 'POST'}); }";
  html += "function deactivateAmbulance() { fetch('/ambulance/deactivate', {method: 'POST'}); }";
  html += "function testLED() { fetch('/traffic/led', {method: 'POST', body: 'ON'}); }";
  html += "function testBuzzer() { fetch('/traffic/buzzer', {method: 'POST', body: 'ON'}); }";
  html += "setTimeout(() => location.reload(), 5000);"; // 5 saniyede bir yenile
  html += "</script></body></html>";
  
  server.send(200, "text/html", html);
}

void handleGPSData() {
  StaticJsonDocument<200> json;
  json["latitude"] = currentLat;
  json["longitude"] = currentLon;
  json["valid"] = gpsValid;
  json["timestamp"] = millis();
  json["ambulance_active"] = ambulanceActive;
  
  String jsonString;
  serializeJson(json, jsonString);
  
  server.send(200, "application/json", jsonString);
}

void handleAmbulanceStatus() {
  StaticJsonDocument<100> json;
  json["active"] = ambulanceActive;
  json["traffic_control"] = trafficControlActive;
  
  String jsonString;
  serializeJson(json, jsonString);
  
  server.send(200, "application/json", jsonString);
}

void handleAmbulanceActivate() {
  ambulanceActive = true;
  Serial.println("🚨 Ambulans aktif edildi!");
  
  // Ambulans aktifken durum LED'i yanar
  digitalWrite(STATUS_LED, HIGH);
  
  server.send(200, "text/plain", "Ambulans aktif");
}

void handleAmbulanceDeactivate() {
  ambulanceActive = false;
  trafficControlActive = false;
  Serial.println("⏹️ Ambulans pasif edildi!");
  
  // LED'leri söndür
  digitalWrite(STATUS_LED, LOW);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  
  server.send(200, "text/plain", "Ambulans pasif");
}

void handleTrafficLED() {
  String command = server.arg("plain");
  
  if (command == "ON") {
    digitalWrite(LED_PIN, HIGH);
    trafficControlActive = true;
    Serial.println("🟢 Trafik LED'i AÇILDI - Yeşil ışık!");
  } else if (command == "OFF") {
    digitalWrite(LED_PIN, LOW);
    trafficControlActive = false;
    Serial.println("🔴 Trafik LED'i KAPANDI");
  }
  
  server.send(200, "text/plain", "LED updated");
}

void handleTrafficBuzzer() {
  String command = server.arg("plain");
  
  if (command == "ON") {
    digitalWrite(BUZZER_PIN, HIGH);
    Serial.println("🔊 Buzzer AÇILDI - Ambulans geçiyor!");
    
    // Buzzer 500ms açık kal sonra kapan
    delay(500);
    digitalWrite(BUZZER_PIN, LOW);
  }
  
  server.send(200, "text/plain", "Buzzer activated");
}

void readGPS() {
  while (gpsSerial.available()) {
    String nmea = gpsSerial.readStringUntil('\n');
    
    // GPGGA mesajını parse et
    if (nmea.startsWith("$GPGGA")) {
      parseGPGGA(nmea);
    }
  }
  
  // GPS geçerlilik kontrolü (son 10 saniye)
  if (millis() - lastGPSUpdate > 10000) {
    gpsValid = false;
  }
}

void parseGPGGA(String nmea) {
  // Basit GPGGA parser
  // Format: $GPGGA,time,lat,latDir,lon,lonDir,quality,satellites,hdop,altitude,M,geoidHeight,M,,checksum
  
  int commaCount = 0;
  int startIndex = 0;
  String fields[15];
  
  // Virgülle ayrılmış alanları parse et
  for (int i = 0; i < nmea.length(); i++) {
    if (nmea.charAt(i) == ',' || i == nmea.length() - 1) {
      fields[commaCount] = nmea.substring(startIndex, i);
      startIndex = i + 1;
      commaCount++;
      if (commaCount >= 15) break;
    }
  }
  
  // GPS kalitesi kontrolü (0 = geçersiz, 1+ = geçerli)
  int quality = fields[6].toInt();
  
  if (quality > 0 && fields[2].length() > 0 && fields[4].length() > 0) {
    // Latitude dönüştürme (DDMM.MMMM → DD.DDDDDD)
    float lat = fields[2].toFloat();
    int latDeg = (int)(lat / 100);
    float latMin = lat - (latDeg * 100);
    currentLat = latDeg + (latMin / 60.0);
    if (fields[3] == "S") currentLat = -currentLat;
    
    // Longitude dönüştürme (DDDMM.MMMM → DDD.DDDDDD)
    float lon = fields[4].toFloat();
    int lonDeg = (int)(lon / 100);
    float lonMin = lon - (lonDeg * 100);
    currentLon = lonDeg + (lonMin / 60.0);
    if (fields[5] == "W") currentLon = -currentLon;
    
    gpsValid = true;
    lastGPSUpdate = millis();
    
    Serial.println("📍 GPS: " + String(currentLat, 6) + ", " + String(currentLon, 6));
  }
}

void sendGPSToSUMO() {
  if (!gpsValid) return;
  
  // HTTP POST isteği hazırla (SUMO bilgisayarına)
  // Bu kısım SUMO çalışan bilgisayarın IP'sine göre ayarlanacak
  
  Serial.println("📡 GPS verisi SUMO'ya gönderiliyor: " + 
                String(currentLat, 6) + ", " + String(currentLon, 6));
}

void blinkStatusLED() {
  static unsigned long lastBlink = 0;
  static bool ledState = false;
  
  if (!ambulanceActive) return; // Ambulans pasifse LED yanıp sönmesin
  
  if (millis() - lastBlink > 1000) { // 1 saniyede bir
    ledState = !ledState;
    digitalWrite(STATUS_LED, ledState);
    lastBlink = millis();
  }
}
