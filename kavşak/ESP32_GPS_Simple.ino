/*
 * ESP32 GPS HTTP Server - BASIT VERSİYON (Kütüphane gerektirmez)
 * Bu kod ESP32'yi GPS modülü olmadan da test etmenizi sağlar
 * Sadece WiFi ve WebServer kütüphaneleri gerekir
 * 
 * Hardware Bağlantıları:
 * - LED -> GPIO 2 (dahili LED)
 * - Buzzer -> GPIO 4 (opsiyonel)
 * - Button -> GPIO 0 (dahili buton)
 * 
 * Test için hazır GPS koordinatları içerir
 */

#include <WiFi.h>
#include <WebServer.h>

// ================================
// BASIT KONFIGÜRASYON
// ================================

// WiFi Ayarları - BURAYA KENDİ BİLGİLERİNİZİ YAZIN
const char* ssid = "YOUR_WIFI_NAME";        // WiFi adınız
const char* password = "YOUR_WIFI_PASSWORD"; // WiFi şifreniz

// Pin Tanımları
#define LED_PIN 2     // Dahili LED
#define BUZZER_PIN 4  // Buzzer (opsiyonel)
#define BUTTON_PIN 0  // Dahili buton

// HTTP Server
WebServer server(80);

// GPS Test Verisi
double testLat = 41.0082;  // İstanbul test koordinatı
double testLon = 28.9784;
bool gpsValid = true;
int satellites = 8;
unsigned long lastUpdate = 0;

// Sistem Durumu
bool ledState = false;

// ================================
// SETUP
// ================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("========================================");
  Serial.println("🚀 ESP32 GPS Server - BASIT VERSİYON");
  Serial.println("========================================");
  
  // Pin ayarları
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  // Başlangıç LED testi
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  
  // WiFi bağlantısı
  connectWiFi();
  
  // HTTP endpoint'leri
  setupEndpoints();
  
  // Server başlat
  server.begin();
  Serial.println("🌐 HTTP Server başlatıldı!");
  Serial.println("========================================");
}

// ================================
// ANA DÖNGÜ
// ================================

void loop() {
  server.handleClient();
  updateTestGPS();
  handleButton();
  delay(100);
}

// ================================
// WiFi BAĞLANTISI
// ================================

void connectWiFi() {
  Serial.print("📶 WiFi'ye bağlanılıyor: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi bağlandı!");
    Serial.print("📍 IP Adresi: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ WiFi bağlanamadı!");
  }
}

// ================================
// HTTP ENDPOINT'LERİ
// ================================

void setupEndpoints() {
  server.on("/", handleRoot);
  server.on("/gps", handleGPS);
  server.on("/status", handleStatus);
  server.on("/led_on", handleLedOn);
  server.on("/led_off", handleLedOff);
  server.on("/buzzer", handleBuzzer);
  server.onNotFound(handleNotFound);
}

void handleRoot() {
  String html = "<html><head><title>ESP32 GPS Server</title></head><body>";
  html += "<h1>🚑 ESP32 GPS Ambulance Server</h1>";
  html += "<h2>📍 Current GPS Data</h2>";
  html += "<p><strong>Latitude:</strong> " + String(testLat, 6) + "</p>";
  html += "<p><strong>Longitude:</strong> " + String(testLon, 6) + "</p>";
  html += "<p><strong>Valid:</strong> " + String(gpsValid ? "Yes" : "No") + "</p>";
  html += "<p><strong>Satellites:</strong> " + String(satellites) + "</p>";
  html += "<h2>🎛️ Controls</h2>";
  html += "<p><a href='/led_on'>🔴 LED ON</a> | <a href='/led_off'>⚪ LED OFF</a> | <a href='/buzzer'>🔊 Buzzer</a></p>";
  html += "<h2>📡 API Endpoints</h2>";
  html += "<p><a href='/gps'>/gps</a> - GPS data JSON</p>";
  html += "<p><a href='/status'>/status</a> - System status</p>";
  html += "<h2>💻 SUMO Command</h2>";
  html += "<code>python runner.py --gps-source esp32 --esp32-ip " + WiFi.localIP().toString() + "</code>";
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

void handleGPS() {
  // JSON response oluştur (manuel)
  String json = "{";
  json += "\"latitude\":" + String(testLat, 6) + ",";
  json += "\"longitude\":" + String(testLon, 6) + ",";
  json += "\"valid\":" + String(gpsValid ? "true" : "false") + ",";
  json += "\"satellites\":" + String(satellites) + ",";
  json += "\"timestamp\":\"2024-01-20T10:30:00Z\",";
  json += "\"device_id\":\"ESP32_Simple\"";
  json += "}";
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
  
  Serial.printf("📡 GPS Request: %.6f, %.6f\n", testLat, testLon);
}

void handleStatus() {
  String json = "{";
  json += "\"device\":\"ESP32_GPS_Simple\",";
  json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"uptime\":" + String(millis()) + ",";
  json += "\"wifi_connected\":" + String(WiFi.status() == WL_CONNECTED ? "true" : "false") + ",";
  json += "\"led_state\":" + String(ledState ? "true" : "false") + ",";
  json += "\"free_heap\":" + String(ESP.getFreeHeap());
  json += "}";
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

void handleLedOn() {
  digitalWrite(LED_PIN, HIGH);
  ledState = true;
  server.send(200, "text/plain", "LED ON - Traffic Light Signal");
  Serial.println("🔴 LED AÇILDI - Trafik ışığı sinyali!");
}

void handleLedOff() {
  digitalWrite(LED_PIN, LOW);
  ledState = false;
  server.send(200, "text/plain", "LED OFF - Normal Traffic");
  Serial.println("⚪ LED KAPANDI - Normal trafik");
}

void handleBuzzer() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(BUZZER_PIN, LOW);
  server.send(200, "text/plain", "BUZZER ACTIVATED");
  Serial.println("🔊 BUZZER - Ambulans sinyali!");
}

void handleNotFound() {
  server.send(404, "text/plain", "404 Not Found");
}

// ================================
// YARDIMCI FONKSIYONLAR
// ================================

void updateTestGPS() {
  // Her 2 saniyede GPS koordinatlarını biraz değiştir
  if (millis() - lastUpdate > 2000) {
    testLat += 0.0001;  // Kuzey yönünde hareket
    testLon += 0.0001;  // Doğu yönünde hareket
    
    // Sınırları kontrol et
    if (testLat > 41.1) testLat = 41.0;
    if (testLon > 29.1) testLon = 28.9;
    
    lastUpdate = millis();
    Serial.printf("📍 GPS güncellendi: %.6f, %.6f\n", testLat, testLon);
  }
}

void handleButton() {
  static bool lastButtonState = HIGH;
  bool currentButtonState = digitalRead(BUTTON_PIN);
  
  if (lastButtonState == HIGH && currentButtonState == LOW) {
    // Buton basıldı - LED toggle
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
    Serial.printf("🔘 Buton basıldı - LED: %s\n", ledState ? "AÇIK" : "KAPALI");
    
    // Buzzer feedback
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
  }
  
  lastButtonState = currentButtonState;
}
