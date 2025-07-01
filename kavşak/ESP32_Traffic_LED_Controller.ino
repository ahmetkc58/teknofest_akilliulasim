/*
 * ESP32 Traffic LED Controller - SUMO Ambulance Integration
 * Bu kod ambulans kavşağa yaklaştığında kırmızı LED'i söndürür
 * SUMO simülasyonundan HTTP sinyali alır ve LED'i kontrol eder
 * 
 * Hardware Bağlantıları:
 * - Kırmızı LED Anot -> GPIO 2 (ESP32)
 * - Kırmızı LED Katot -> 220Ω Resistor -> GND
 * - (Opsiyonel) Status LED -> GPIO 5
 * - (Opsiyonel) Buzzer -> GPIO 4
 * 
 * SUMO Integration:
 * - Ambulans kavşağa yaklaştığında: LED SÖNER (yeşil ışık)
 * - Normal trafik durumunda: LED YANAR (kırmızı ışık)
 * 
 * HTTP Endpoints:
 * - GET /status - Sistem durumu
 * - POST /led/on - LED'i yak (kırmızı ışık)
 * - POST /led/off - LED'i söndür (yeşil ışık - ambulans geçiyor)
 * - POST /ambulance/green - Ambulans yeşil ışık sinyali
 * - POST /ambulance/normal - Normal trafik durumu
 * 
 * Kullanım:
 * SUMO runner.py otomatik olarak bu ESP32'ye sinyal gönderecek
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// ================================
// KONFIGÜRASYON AYARLARI
// ================================

// WiFi Ayarları - Kendi ağınızın bilgilerini yazın
const char* ssid = "YOUR_WIFI_SSID";          // WiFi ağ adı
const char* password = "YOUR_WIFI_PASSWORD";   // WiFi şifresi

// Hardware Pin Tanımları
#define RED_LED_PIN 2        // Kırmızı trafik LED'i (ana LED)
#define STATUS_LED_PIN 5     // Durum LED'i (mavi/yeşil)
#define BUZZER_PIN 4         // Ambulans buzzer'ı (opsiyonel)

// HTTP Server
WebServer server(80);

// ================================
// GLOBAL DEĞİŞKENLER
// ================================

// Sistem Durumu
bool trafficLightRed = true;     // true = Kırmızı ışık (LED yanar)
bool ambulanceActive = false;    // Ambulans aktif durumu
bool systemReady = false;        // Sistem hazır durumu
unsigned long lastSignalTime = 0; // Son sinyal zamanı

// ================================
// SETUP FONKSIYONU
// ================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("========================================");
  Serial.println("🚨 ESP32 Traffic LED Controller v1.0");
  Serial.println("🚑 SUMO Ambulance Integration");
  Serial.println("========================================");
  
  // Pin konfigürasyonu
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Başlangıç durumu - Kırmızı ışık (LED yanar)
  digitalWrite(RED_LED_PIN, HIGH);    // Kırmızı LED yanar
  digitalWrite(STATUS_LED_PIN, LOW);  // Status LED söner
  digitalWrite(BUZZER_PIN, LOW);      // Buzzer kapalı
  
  Serial.println("🔴 Başlangıç: Kırmızı ışık AKTİF (LED yanar)");
  
  // WiFi Bağlantısı
  connectToWiFi();
  
  // HTTP Endpoint'leri ayarla
  setupHTTPEndpoints();
  
  // HTTP Server başlat
  server.begin();
  systemReady = true;
  
  Serial.println("========================================");
  Serial.println("✅ Sistem hazır! SUMO sinyallerini bekliyor...");
  Serial.println("📡 Ambulans yaklaştığında LED sönecek");
  Serial.println("🔄 Normal durumda LED yanacak");
  Serial.println("========================================");
  
  // Başarı sinyali (3 kez yanıp sön)
  for(int i = 0; i < 3; i++) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(200);
    digitalWrite(STATUS_LED_PIN, LOW);
    delay(200);
  }
}

// ================================
// ANA DÖNGÜ
// ================================

void loop() {
  // HTTP isteklerini işle
  server.handleClient();
  
  // Watchdog - 30 saniye sinyal gelmezse normal duruma dön
  if(ambulanceActive && (millis() - lastSignalTime > 30000)) {
    Serial.println("⏰ Watchdog: 30s sinyal yok, normal duruma dönülüyor");
    setNormalTraffic();
  }
  
  // Status LED - sistem durumunu göster
  static unsigned long lastBlink = 0;
  if(millis() - lastBlink > 1000) {
    lastBlink = millis();
    
    if(systemReady) {
      // Sistem hazır - status LED yavaş yanıp söner
      digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
    }
  }
  
  delay(10); // CPU rahatlatma
}

// ================================
// WiFi BAĞLANTI FONKSİYONU
// ================================

void connectToWiFi() {
  Serial.println("📶 WiFi'ye bağlanılıyor...");
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("✅ WiFi bağlantısı başarılı!");
    Serial.print("📍 IP Adresi: ");
    Serial.println(WiFi.localIP());
    Serial.print("📶 Sinyal Gücü: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println();
    Serial.println("❌ WiFi bağlantısı başarısız!");
    Serial.println("⚠️ Offline modda çalışılacak");
  }
}

// ================================
// HTTP ENDPOINT AYARLARI
// ================================

void setupHTTPEndpoints() {
  // Ana sayfa - sistem durumu
  server.on("/", handleRoot);
  
  // LED Kontrol Endpoint'leri
  server.on("/led/on", HTTP_POST, handleLEDOn);       // Kırmızı ışık - LED yak
  server.on("/led/off", HTTP_POST, handleLEDOff);     // Yeşil ışık - LED söndür
  
  // Ambulans Sinyalleri (SUMO'dan gelecek)
  server.on("/ambulance/green", HTTP_POST, handleAmbulanceGreen);   // Ambulans yeşil ışık
  server.on("/ambulance/normal", HTTP_POST, handleAmbulanceNormal); // Normal trafik
  
  // Sistem Durumu
  server.on("/status", HTTP_GET, handleStatus);
  
  // CORS desteği
  server.enableCORS(true);
  
  Serial.println("🌐 HTTP Server endpoint'leri hazırlandı");
}

// ================================
// HTTP HANDLER FONKSİYONLARI
// ================================

void handleRoot() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<title>ESP32 Traffic LED Controller</title>";
  html += "<meta charset='UTF-8'>";
  html += "<style>";
  html += "body{font-family:Arial;margin:20px;background:#f0f0f0;}";
  html += ".container{max-width:600px;margin:0 auto;background:white;padding:20px;border-radius:10px;}";
  html += ".status{background:#e9ecef;padding:15px;border-radius:5px;margin:10px 0;}";
  html += ".red{color:#dc3545;font-weight:bold;}";
  html += ".green{color:#28a745;font-weight:bold;}";
  html += ".button{background:#007bff;color:white;padding:10px 20px;border:none;border-radius:5px;margin:5px;cursor:pointer;}";
  html += ".button:hover{background:#0056b3;}";
  html += "</style></head><body>";
  
  html += "<div class='container'>";
  html += "<h1>🚨 ESP32 Traffic LED Controller</h1>";
  html += "<p>SUMO Ambulance Integration System</p>";
  
  html += "<div class='status'>";
  html += "<h3>Current Status</h3>";
  html += "<p><strong>Traffic Light:</strong> ";
  if(trafficLightRed) {
    html += "<span class='red'>🔴 RED (LED ON)</span>";
  } else {
    html += "<span class='green'>🟢 GREEN (LED OFF)</span>";
  }
  html += "</p>";
  html += "<p><strong>Ambulance:</strong> ";
  html += ambulanceActive ? "🚑 ACTIVE" : "⏸️ INACTIVE";
  html += "</p>";
  html += "<p><strong>System:</strong> ";
  html += systemReady ? "✅ READY" : "⚠️ NOT READY";
  html += "</p>";
  html += "<p><strong>IP Address:</strong> " + WiFi.localIP().toString() + "</p>";
  html += "</div>";
  
  html += "<div class='status'>";
  html += "<h3>Manual Control</h3>";
  html += "<button class='button' onclick='sendCommand(\"/led/on\")'>🔴 Red Light (LED ON)</button>";
  html += "<button class='button' onclick='sendCommand(\"/led/off\")'>🟢 Green Light (LED OFF)</button>";
  html += "</div>";
  
  html += "<div class='status'>";
  html += "<h3>System Info</h3>";
  html += "<p>Last Signal: " + String((millis() - lastSignalTime) / 1000) + " seconds ago</p>";
  html += "<p>Uptime: " + String(millis() / 1000) + " seconds</p>";
  html += "<p>Free Heap: " + String(ESP.getFreeHeap()) + " bytes</p>";
  html += "</div>";
  
  html += "</div>";
  
  html += "<script>";
  html += "function sendCommand(endpoint) {";
  html += "  fetch(endpoint, {method: 'POST'})";
  html += "    .then(response => response.text())";
  html += "    .then(data => {";
  html += "      alert('Command sent: ' + data);";
  html += "      location.reload();";
  html += "    });";
  html += "}";
  html += "</script>";
  
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

void handleStatus() {
  StaticJsonDocument<200> json;
  json["traffic_light"] = trafficLightRed ? "red" : "green";
  json["led_state"] = digitalRead(RED_LED_PIN) ? "on" : "off";
  json["ambulance_active"] = ambulanceActive;
  json["system_ready"] = systemReady;
  json["ip_address"] = WiFi.localIP().toString();
  json["uptime"] = millis() / 1000;
  json["last_signal"] = (millis() - lastSignalTime) / 1000;
  
  String jsonString;
  serializeJson(json, jsonString);
  
  server.send(200, "application/json", jsonString);
  Serial.println("📊 Status bilgisi gönderildi");
}

void handleLEDOn() {
  // Kırmızı ışık - LED'i yak
  digitalWrite(RED_LED_PIN, HIGH);
  trafficLightRed = true;
  lastSignalTime = millis();
  
  Serial.println("🔴 Manual: RED LIGHT ON (LED yanar)");
  server.send(200, "text/plain", "Red light activated");
}

void handleLEDOff() {
  // Yeşil ışık - LED'i söndür
  digitalWrite(RED_LED_PIN, LOW);
  trafficLightRed = false;
  lastSignalTime = millis();
  
  Serial.println("🟢 Manual: GREEN LIGHT ON (LED söner)");
  server.send(200, "text/plain", "Green light activated");
}

void handleAmbulanceGreen() {
  // SUMO'dan ambulans yeşil ışık sinyali
  setAmbulanceGreenLight();
  
  server.send(200, "text/plain", "Ambulance green light activated");
  Serial.println("📡 SUMO Signal: Ambulance green light received");
}

void handleAmbulanceNormal() {
  // SUMO'dan normal trafik sinyali
  setNormalTraffic();
  
  server.send(200, "text/plain", "Normal traffic resumed");
  Serial.println("📡 SUMO Signal: Normal traffic resumed");
}

// ================================
// TRAFIK KONTROL FONKSİYONLARI
// ================================

void setAmbulanceGreenLight() {
  // Ambulans için yeşil ışık - LED'i söndür
  digitalWrite(RED_LED_PIN, LOW);      // Kırmızı LED söner (yeşil ışık)
  digitalWrite(STATUS_LED_PIN, HIGH);  // Status LED yanar (ambulans aktif)
  
  trafficLightRed = false;
  ambulanceActive = true;
  lastSignalTime = millis();
  
  // Ambulans sinyali - kısa buzzer
  digitalWrite(BUZZER_PIN, HIGH);
  delay(100);
  digitalWrite(BUZZER_PIN, LOW);
  
  Serial.println("🚑 AMBULANS YEŞİL IŞIK: Kırmızı LED SÖNDÜRÜLDÜ");
  Serial.println("   └── Ambulans kavşaktan geçiyor...");
}

void setNormalTraffic() {
  // Normal trafik - kırmızı ışık, LED yanar
  digitalWrite(RED_LED_PIN, HIGH);     // Kırmızı LED yanar
  digitalWrite(STATUS_LED_PIN, LOW);   // Status LED söner
  digitalWrite(BUZZER_PIN, LOW);       // Buzzer kapalı
  
  trafficLightRed = true;
  ambulanceActive = false;
  lastSignalTime = millis();
  
  Serial.println("🔄 NORMAL TRAFİK: Kırmızı LED YAKILDI");
  Serial.println("   └── Normal trafik akışı devam ediyor...");
}
