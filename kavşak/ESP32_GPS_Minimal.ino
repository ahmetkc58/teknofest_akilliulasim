/*
 * ESP32 Minimal GPS HTTP Server - SUMO Integration
 * Sadece GPS modülü ile HTTP üzerinden GPS verisi sağlar
 * 
 * Hardware Bağlantıları:
 * - GPS TX -> GPIO 16 (ESP32 RX2)
 * - GPS RX -> GPIO 17 (ESP32 TX2)
 * - GPS VCC -> 3.3V
 * - GPS GND -> GND
 * 
 * SUMO Kullanımı:
 * python runner.py --gps-source esp32 --esp32-ip [ESP32_IP_ADRESI]
 */

#include <WiFi.h>
#include <WebServer.h>
#include <HardwareSerial.h>

// ================================
// AYARLAR
// ================================

// WiFi Ayarları - Buraya kendi WiFi bilgilerinizi yazın
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// GPS Ayarları
#define GPS_RX_PIN 16     // GPS TX -> ESP32 RX
#define GPS_TX_PIN 17     // GPS RX -> ESP32 TX
#define GPS_BAUD 9600

// Hardware
HardwareSerial gpsSerial(2);  // UART2
WebServer server(80);

// ================================
// GPS VERİSİ
// ================================

struct GPSData {
  double latitude = 0.0;
  double longitude = 0.0;
  bool valid = false;
  String timestamp = "";
  int satellites = 0;
};

GPSData currentGPS;
unsigned long lastGPSUpdate = 0;

// ================================
// SETUP
// ================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("ESP32 GPS Server - SUMO Integration");
  Serial.println("====================================");
  
  // GPS başlat
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("GPS Serial başlatıldı");
  
  // WiFi bağlan
  connectToWiFi();
  
  // HTTP endpoints
  server.on("/gps", handleGPS);
  server.on("/status", handleStatus);
  server.on("/", handleRoot);
  
  // Server başlat
  server.begin();
  Serial.println("HTTP Server başlatıldı");
  Serial.println("====================================");
  printConnectionInfo();
}

// ================================
// MAIN LOOP
// ================================

void loop() {
  server.handleClient();
  readGPSData();
  delay(100);
}

// ================================
// WiFi BAĞLANTI
// ================================

void connectToWiFi() {
  Serial.print("WiFi'ye bağlanılıyor: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi bağlantısı başarılı!");
  } else {
    Serial.println("\nWiFi bağlantısı başarısız!");
  }
}

// ================================
// GPS OKUMA
// ================================

void readGPSData() {
  while (gpsSerial.available()) {
    String sentence = gpsSerial.readStringUntil('\n');
    sentence.trim();
    
    if (sentence.startsWith("$GPGGA") || sentence.startsWith("$GNGGA")) {
      parseGGASentence(sentence);
    } else if (sentence.startsWith("$GPRMC") || sentence.startsWith("$GNRMC")) {
      parseRMCSentence(sentence);
    }
  }
  
  // GPS timeout kontrolü (5 saniye)
  if (millis() - lastGPSUpdate > 5000) {
    currentGPS.valid = false;
  }
}

void parseGGASentence(String sentence) {
  // $GPGGA,time,lat,N/S,lon,E/W,quality,satellites,hdop,altitude,M,geoid,M,,checksum
  
  int commaPos[15];
  int commaCount = 0;
  
  // Virgül pozisyonlarını bul
  for (int i = 0; i < sentence.length() && commaCount < 15; i++) {
    if (sentence.charAt(i) == ',') {
      commaPos[commaCount++] = i;
    }
  }
  
  if (commaCount >= 6) {
    // Latitude
    String latStr = sentence.substring(commaPos[1] + 1, commaPos[2]);
    String latDir = sentence.substring(commaPos[2] + 1, commaPos[3]);
    
    // Longitude
    String lonStr = sentence.substring(commaPos[3] + 1, commaPos[4]);
    String lonDir = sentence.substring(commaPos[4] + 1, commaPos[5]);
    
    // Quality ve Satellites
    String quality = sentence.substring(commaPos[5] + 1, commaPos[6]);
    String satStr = sentence.substring(commaPos[6] + 1, commaPos[7]);
    
    // Geçerli GPS verisi kontrolü
    if (latStr.length() > 0 && lonStr.length() > 0 && quality.toInt() > 0) {
      currentGPS.latitude = convertDMToDD(latStr, latDir);
      currentGPS.longitude = convertDMToDD(lonStr, lonDir);
      currentGPS.satellites = satStr.toInt();
      currentGPS.valid = true;
      lastGPSUpdate = millis();
      
      // Debug - her 5 saniyede bir yazdır
      static unsigned long lastPrint = 0;
      if (millis() - lastPrint > 5000) {
        Serial.printf("GPS: %.6f, %.6f (Sat: %d)\n", 
                     currentGPS.latitude, currentGPS.longitude, currentGPS.satellites);
        lastPrint = millis();
      }
    }
  }
}

void parseRMCSentence(String sentence) {
  // $GPRMC,time,A,lat,N/S,lon,E/W,speed,course,date,mag_var,mag_var_dir,checksum
  
  int commaPos[12];
  int commaCount = 0;
  
  for (int i = 0; i < sentence.length() && commaCount < 12; i++) {
    if (sentence.charAt(i) == ',') {
      commaPos[commaCount++] = i;
    }
  }
  
  if (commaCount >= 9) {
    // Timestamp oluştur
    String timeStr = sentence.substring(commaPos[0] + 1, commaPos[1]);
    String dateStr = sentence.substring(commaPos[8] + 1, commaPos[9]);
    
    if (timeStr.length() >= 6 && dateStr.length() >= 6) {
      currentGPS.timestamp = formatDateTime(timeStr, dateStr);
    }
  }
}

// Derece-Dakika formatını Ondalık Dereceye çevir
double convertDMToDD(String coordinate, String direction) {
  if (coordinate.length() < 4) return 0.0;
  
  double degrees, minutes;
  
  if (coordinate.length() == 9) {  // Longitude (dddmm.mmmm)
    degrees = coordinate.substring(0, 3).toDouble();
    minutes = coordinate.substring(3).toDouble();
  } else {  // Latitude (ddmm.mmmm)
    degrees = coordinate.substring(0, 2).toDouble();
    minutes = coordinate.substring(2).toDouble();
  }
  
  double decimal = degrees + (minutes / 60.0);
  
  if (direction == "S" || direction == "W") {
    decimal = -decimal;
  }
  
  return decimal;
}

String formatDateTime(String timeStr, String dateStr) {
  if (timeStr.length() >= 6 && dateStr.length() >= 6) {
    String time = timeStr.substring(0, 2) + ":" + 
                  timeStr.substring(2, 4) + ":" + 
                  timeStr.substring(4, 6);
    
    String date = dateStr.substring(0, 2) + "/" + 
                  dateStr.substring(2, 4) + "/" + 
                  dateStr.substring(4, 6);
    
    return date + " " + time;
  }
  return "";
}

// ================================
// HTTP ENDPOINTS
// ================================

void handleGPS() {
  // JSON formatında GPS verisi döndür (SUMO için)
  String json = "{";
  json += "\"latitude\":" + String(currentGPS.latitude, 6) + ",";
  json += "\"longitude\":" + String(currentGPS.longitude, 6) + ",";
  json += "\"valid\":" + String(currentGPS.valid ? "true" : "false") + ",";
  json += "\"timestamp\":\"" + currentGPS.timestamp + "\",";
  json += "\"satellites\":" + String(currentGPS.satellites);
  json += "}";
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
  
  // Log
  Serial.printf("GPS Request: %.6f, %.6f (Valid: %s)\n", 
               currentGPS.latitude, currentGPS.longitude,
               currentGPS.valid ? "Yes" : "No");
}

void handleStatus() {
  // Sistem durumu
  String json = "{";
  json += "\"wifi_connected\":" + String(WiFi.status() == WL_CONNECTED ? "true" : "false") + ",";
  json += "\"ip_address\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"uptime\":" + String(millis()) + ",";
  json += "\"free_heap\":" + String(ESP.getFreeHeap()) + ",";
  json += "\"gps_valid\":" + String(currentGPS.valid ? "true" : "false") + ",";
  json += "\"gps_satellites\":" + String(currentGPS.satellites);
  json += "}";
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

void handleRoot() {
  // Basit web arayüzü
  String html = "<!DOCTYPE html><html><head><title>ESP32 GPS Server</title>";
  html += "<meta charset='UTF-8'><style>";
  html += "body{font-family:Arial;margin:20px;background:#f0f0f0;}";
  html += ".container{max-width:600px;margin:0 auto;background:white;padding:20px;border-radius:10px;}";
  html += ".status{background:#e9ecef;padding:10px;border-radius:5px;margin:10px 0;}";
  html += "</style></head><body>";
  
  html += "<div class='container'>";
  html += "<h1>ESP32 GPS Server</h1>";
  html += "<p>SUMO Traffic Simulation GPS Data Provider</p>";
  
  html += "<div class='status'>";
  html += "<h3>Current GPS Data</h3>";
  html += "<p><strong>Latitude:</strong> " + String(currentGPS.latitude, 6) + "</p>";
  html += "<p><strong>Longitude:</strong> " + String(currentGPS.longitude, 6) + "</p>";
  html += "<p><strong>Valid:</strong> " + String(currentGPS.valid ? "Yes" : "No") + "</p>";
  html += "<p><strong>Satellites:</strong> " + String(currentGPS.satellites) + "</p>";
  html += "<p><strong>Timestamp:</strong> " + currentGPS.timestamp + "</p>";
  html += "</div>";
  
  html += "<div class='status'>";
  html += "<h3>API Endpoints</h3>";
  html += "<p><a href='/gps'>/gps</a> - GPS data (JSON)</p>";
  html += "<p><a href='/status'>/status</a> - System status (JSON)</p>";
  html += "</div>";
  
  html += "<div class='status'>";
  html += "<h3>SUMO Usage</h3>";
  html += "<p><code>python runner.py --gps-source esp32 --esp32-ip " + WiFi.localIP().toString() + "</code></p>";
  html += "</div>";
  
  html += "</div>";
  html += "<script>setTimeout(function(){location.reload();}, 5000);</script>";
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

// ================================
// YARDIMCI FONKSIYONLAR
// ================================

void printConnectionInfo() {
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("IP Adresi: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Web Interface: http://%s\n", WiFi.localIP().toString().c_str());
    Serial.printf("GPS Endpoint: http://%s/gps\n", WiFi.localIP().toString().c_str());
    Serial.printf("SUMO Command: python runner.py --gps-source esp32 --esp32-ip %s\n", 
                 WiFi.localIP().toString().c_str());
  } else {
    Serial.println("WiFi bağlantısı yok!");
  }
  Serial.println("====================================");
}
