/*
 * ESP32 GPS HTTP Server - SUMO Ambulance Real-Time Control
 * Bu kod ESP32'yi GPS modülü ile birlikte kullanarak gerçek zamanlı GPS verisi sağlar
 * SUMO simülasyonu ambulansı ESP32'den gelen gerçek GPS koordinatları ile kontrol eder
 * 
 * Gerekli Kütüphaneler:
 * - WiFi
 * - WebServer
 * - HardwareSerial (GPS için)
 * - ArduinoJson
 * 
 * Hardware Bağlantıları:
 * - GPS RX -> GPIO 16 (ESP32 TX2)
 * - GPS TX -> GPIO 17 (ESP32 RX2)
 * 
 * Kullanım: SUMO runner.py --gps-source esp32 --esp32-ip [ESP32_IP]
 * 
 * Yazarlar: SUMO GPS Ambulance Project
 * Tarih: 2024
 */

#include <WiFi.h>
#include <WebServer.h>
#include <HardwareSerial.h>
#include <ArduinoJson.h>

// ================================
// KONFIGÜRASYON AYARLARI
// ================================

// WiFi Ayarları
const char* ssid = "YOUR_WIFI_SSID";          // WiFi ağ adınızı buraya yazın (örnek: "TP-Link_2.4G")
const char* password = "YOUR_WIFI_PASSWORD";   // WiFi şifrenizi buraya yazın

// Hardware Pin Tanımları
#define GPS_RX_PIN 16     // GPS modülü TX -> ESP32 RX
#define GPS_TX_PIN 17     // GPS modülü RX -> ESP32 TX

// GPS Ayarları
#define GPS_BAUD 9600
HardwareSerial gpsSerial(2);  // UART2 kullan

// HTTP Server
WebServer server(80);

// ================================
// GLOBAL DEĞİŞKENLER
// ================================

// GPS Verisi
struct GPSData {
  double latitude = 0.0;
  double longitude = 0.0;
  bool valid = false;
  String timestamp = "";
  int satellites = 0;
  double altitude = 0.0;
  double speed = 0.0;
  double course = 0.0;
};

GPSData currentGPS;
unsigned long lastGPSUpdate = 0;

// ================================
// SETUP FONKSIYONU
// ================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("========================================");
  Serial.println("🚀 ESP32 GPS Real-Time Server Starting");
  Serial.println("========================================");
  
  // GPS Seri Port Başlat
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("📡 GPS Serial başlatıldı (UART2)");
  
  // WiFi Bağlantısı
  connectToWiFi();
  
  // HTTP Endpoint'leri Tanımla
  setupHTTPEndpoints();
  
  // HTTP Server Başlat
  server.begin();
  Serial.println("🌐 HTTP Server başlatıldı!");
  Serial.println("========================================");
  
  // Başlangıç bilgileri yazdır
  printSystemInfo();
}

// ================================
// ANA DÖNGÜ
// ================================

void loop() {
  // HTTP isteklerini işle
  server.handleClient();
  
  // GPS verilerini oku
  readGPSData();
  
  // Kısa bekleme
  delay(100);
}

// ================================
// GPS FONKSIYONLARI
// ================================

void readGPSData() {
  while (gpsSerial.available() > 0) {
    String nmea = gpsSerial.readStringUntil('\n');
    nmea.trim();
    
    if (nmea.startsWith("$GPRMC") || nmea.startsWith("$GNRMC")) {
      parseGPRMC(nmea);
    } else if (nmea.startsWith("$GPGGA") || nmea.startsWith("$GNGGA")) {
      parseGPGGA(nmea);
    }
  }
}

void parseGPRMC(String nmea) {
  // $GPRMC,time,status,lat,latNS,lon,lonEW,speed,course,date,magVar,magVarEW*checksum
  
  int commaIndex[12];
  int commaCount = 0;
  
  // Virgül pozisyonlarını bul
  for (int i = 0; i < nmea.length() && commaCount < 12; i++) {
    if (nmea.charAt(i) == ',') {
      commaIndex[commaCount] = i;
      commaCount++;
    }
  }
  
  if (commaCount < 11) return;
  
  // Status kontrolü (A = aktif, V = geçersiz)
  String status = nmea.substring(commaIndex[1] + 1, commaIndex[2]);
  if (status != "A") {
    currentGPS.valid = false;
    return;
  }
  
  // Enlem
  String latStr = nmea.substring(commaIndex[2] + 1, commaIndex[3]);
  String latDir = nmea.substring(commaIndex[3] + 1, commaIndex[4]);
  if (latStr.length() > 0) {
    double lat = latStr.toDouble();
    // DDMM.MMMM formatından DD.DDDDDD formatına çevir
    int degrees = (int)(lat / 100);
    double minutes = lat - (degrees * 100);
    currentGPS.latitude = degrees + (minutes / 60.0);
    if (latDir == "S") currentGPS.latitude = -currentGPS.latitude;
  }
  
  // Boylam
  String lonStr = nmea.substring(commaIndex[4] + 1, commaIndex[5]);
  String lonDir = nmea.substring(commaIndex[5] + 1, commaIndex[6]);
  if (lonStr.length() > 0) {
    double lon = lonStr.toDouble();
    // DDDMM.MMMM formatından DDD.DDDDDD formatına çevir
    int degrees = (int)(lon / 100);
    double minutes = lon - (degrees * 100);
    currentGPS.longitude = degrees + (minutes / 60.0);
    if (lonDir == "W") currentGPS.longitude = -currentGPS.longitude;
  }
  
  // Hız (knot cinsinden)
  String speedStr = nmea.substring(commaIndex[6] + 1, commaIndex[7]);
  if (speedStr.length() > 0) {
    currentGPS.speed = speedStr.toDouble() * 1.852; // knot'dan km/h'ye çevir
  }
  
  // Yön
  String courseStr = nmea.substring(commaIndex[7] + 1, commaIndex[8]);
  if (courseStr.length() > 0) {
    currentGPS.course = courseStr.toDouble();
  }
  
  // Zaman damgası
  String timeStr = nmea.substring(commaIndex[0] + 1, commaIndex[1]);
  String dateStr = nmea.substring(commaIndex[8] + 1, commaIndex[9]);
  currentGPS.timestamp = dateStr + " " + timeStr;
  
  currentGPS.valid = true;
  lastGPSUpdate = millis();
  
  // Serial çıktı (debug için)
  Serial.printf("GPS: %.6f, %.6f | Speed: %.1f km/h | Course: %.1f°\n", 
                currentGPS.latitude, currentGPS.longitude, currentGPS.speed, currentGPS.course);
}

void parseGPGGA(String nmea) {
  // $GPGGA,time,lat,latNS,lon,lonEW,quality,numSV,HDOP,alt,altUnit,geoidal,geoidalUnit,dgpsAge,dgpsID*checksum
  
  int commaIndex[15];
  int commaCount = 0;
  
  // Virgül pozisyonlarını bul
  for (int i = 0; i < nmea.length() && commaCount < 15; i++) {
    if (nmea.charAt(i) == ',') {
      commaIndex[commaCount] = i;
      commaCount++;
    }
  }
  
  if (commaCount < 10) return;
  
  // Uydu sayısı
  String satStr = nmea.substring(commaIndex[6] + 1, commaIndex[7]);
  if (satStr.length() > 0) {
    currentGPS.satellites = satStr.toInt();
  }
  
  // Yükseklik
  String altStr = nmea.substring(commaIndex[8] + 1, commaIndex[9]);
  if (altStr.length() > 0) {
    currentGPS.altitude = altStr.toDouble();
  }
}

// ================================
// HTTP ENDPOINT FONKSIYONLARI
// ================================

void setupHTTPEndpoints() {
  // Ana GPS endpoint'i
  server.on("/gps", HTTP_GET, handleGPSRequest);
  
  // Sistem bilgisi endpoint'i
  server.on("/", HTTP_GET, handleRootRequest);
  server.on("/status", HTTP_GET, handleStatusRequest);
  
  // 404 handler
  server.onNotFound(handleNotFound);
  
  Serial.println("📝 HTTP Endpoint'leri tanımlandı:");
  Serial.println("   GET /gps     - GPS verisi (JSON)");
  Serial.println("   GET /        - Sistem bilgisi");
  Serial.println("   GET /status  - Detaylı durum");
}

void handleGPSRequest() {
  // CORS header'ları ekle
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  
  // JSON response oluştur
  DynamicJsonDocument doc(512);
  
  // Gerçek GPS modülü yoksa test verisi kullan
  if (!currentGPS.valid) {
    doc["latitude"] = 36.91976667;
    doc["longitude"] = 30.67377500;
    doc["altitude"] = 10.0;
    doc["speed"] = 0.0;
    doc["course"] = 0.0;
    doc["satellites"] = 4;
    doc["valid"] = true;  // Test için true yap
    doc["timestamp"] = millis();
    doc["last_update"] = millis();
    doc["device_id"] = "ESP32_GPS_001";
    doc["test_mode"] = true;
  } else {
    doc["latitude"] = currentGPS.latitude;
    doc["longitude"] = currentGPS.longitude;
    doc["altitude"] = currentGPS.altitude;
    doc["speed"] = currentGPS.speed;
    doc["course"] = currentGPS.course;
    doc["satellites"] = currentGPS.satellites;
    doc["valid"] = currentGPS.valid;
    doc["timestamp"] = currentGPS.timestamp;
    doc["last_update"] = lastGPSUpdate;
    doc["device_id"] = "ESP32_GPS_001";
    doc["test_mode"] = false;
  }
  
  String response;
  serializeJson(doc, response);
  
  server.send(200, "application/json", response);
  
  // Log
  Serial.println("📡 GPS verisi gönderildi: " + response);
}

void handleRootRequest() {
  String html = "<!DOCTYPE html>\n";
  html += "<html><head><title>ESP32 GPS Server</title></head>\n";
  html += "<body><h1>🚗 ESP32 GPS Real-Time Server</h1>\n";
  html += "<p><strong>Status:</strong> " + String(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected") + "</p>\n";
  html += "<p><strong>IP:</strong> " + WiFi.localIP().toString() + "</p>\n";
  html += "<p><strong>GPS Valid:</strong> " + String(currentGPS.valid ? "Yes" : "No") + "</p>\n";
  html += "<p><strong>Satellites:</strong> " + String(currentGPS.satellites) + "</p>\n";
  html += "<h2>Endpoints:</h2>\n";
  html += "<ul>\n";
  html += "<li><a href='/gps'>/gps</a> - GPS data (JSON)</li>\n";
  html += "<li><a href='/status'>/status</a> - System status</li>\n";
  html += "</ul>\n";
  html += "<p><em>SUMO Ambulance Project 2024</em></p>\n";
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

void handleStatusRequest() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  
  DynamicJsonDocument doc(1024);
  
  doc["device_id"] = "ESP32_GPS_001";
  doc["uptime"] = millis();
  doc["wifi_connected"] = (WiFi.status() == WL_CONNECTED);
  doc["wifi_ip"] = WiFi.localIP().toString();
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["gps_valid"] = currentGPS.valid;
  doc["gps_satellites"] = currentGPS.satellites;
  doc["last_gps_update"] = lastGPSUpdate;
  doc["free_heap"] = ESP.getFreeHeap();
  
  String response;
  serializeJson(doc, response);
  
  server.send(200, "application/json", response);
}

void handleNotFound() {
  server.send(404, "text/plain", "404: Not Found");
}

// ================================
// YARDIMCI FONKSIYONLAR
// ================================

void printSystemInfo() {
  Serial.println("📋 Sistem Bilgileri:");
  Serial.println("   Device: ESP32 GPS Real-Time Server");
  Serial.println("   Version: 1.0");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("   IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("   RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  }
  Serial.println("   Endpoints:");
  Serial.println("     GET /gps     - GPS data");
  Serial.println("     GET /status  - System status");
  Serial.println("========================================");
}

// ================================
// WiFi FONKSIYONLARI
// ================================

void connectToWiFi() {
  Serial.print("🔗 WiFi'ye bağlanılıyor: ");
  Serial.print(ssid);
  Serial.println("...");
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi bağlantısı başarılı!");
    Serial.print("📍 IP Adresi: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ WiFi bağlantısı başarısız!");
    Serial.println("Lütfen WiFi ayarlarınızı kontrol edin!");
  }
}


