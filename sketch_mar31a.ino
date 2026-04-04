/*
  =============================================================================
  ПРОЄКТ: ГЛИБИНА 4.0 (LOGICAL STARTUP EDITION) - АДАПТОВАНА ВЕРСІЯ
  ESP32 + MQ-7 + DHT22 + SW-420 + OLED 128x64 (жовта зона: 0-15px, синя: 16-63px)
  =============================================================================
*/

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <Preferences.h>
#include <nvs_flash.h>
#include <esp_wifi.h>
#include <vector>
#include <HTTPUpdate.h>
#include <queue>

// ==========================================
// ФУНКЦІЯ КОНВЕРТАЦІЇ УКРАЇНСЬКОЇ МОВИ (UTF-8 -> CP1251)
// ==========================================

String utf8ukr(const char* source) {
    int i = 0;
    String target = "";
    unsigned char n;

    while (source[i]) {
        n = source[i]; i++;
        if (n >= 0xC0) {
            switch (n) {
                case 0xD0: {
                    n = source[i]; i++;
                    if (n == 0x81) { n = 0xA8; break; } // Ё
                    if (n == 0x84) { n = 0xAA; break; } // Є
                    if (n == 0x86) { n = 0xB1; break; } // І
                    if (n == 0x87) { n = 0xAF; break; } // Ї
                    if (n >= 0x90 && n <= 0xBF) n = n + 0x2F; break;
                }
                case 0xD1: {
                    n = source[i]; i++;
                    if (n == 0x91) { n = 0xB7; break; } // ё
                    if (n == 0x94) { n = 0xB9; break; } // є
                    if (n == 0x96) { n = 0xB2; break; } // і
                    if (n == 0x97) { n = 0xBE; break; } // ї
                    if (n >= 0x80 && n <= 0x8F) n = n + 0x6F; break;
                }
                case 0xD2: {
                    n = source[i]; i++;
                    if (n == 0x90) { n = 0xA5; break; } // Ґ
                    if (n == 0x91) { n = 0xB3; break; } // ґ
                }
            }
        }
        target += (char)n;
    }
    return target;
}

// --- НАЛАШТУВАННЯ СЕРВЕРА ---
const char* SERVER_ADDRESS = "http://bunb.pp.ua";
const char* TELEMETRY_ENDPOINT = "/diploma/api/telemetry/";
const char* WIFI_API_ENDPOINT = "/diploma/api/wifi-networks/";
const char* OTA_CHECK_ENDPOINT = "/diploma/api/ota/check/";
const char* OTA_LOG_ENDPOINT = "/diploma/api/ota/log/";

#define FIRMWARE_VERSION "1.0.0"

// --- ТАЙМЕРИ ТА ІНТЕРВАЛИ ---
#define DATA_SEND_INTERVAL_MS 10000UL         // Інтервал відправки телеметрії (10 сек)
#define NO_MOTION_TIMEOUT_MS 10000UL          // Час без руху до появи попередження (10 сек)
#define SOS_GRACE_PERIOD_MS 5000UL            // Час після попередження до активації SOS (5 сек)
#define LONG_PRESS_SOS_MS 5000UL              // Час утримання кнопки для виклику SOS (5 сек)
#define LONG_PRESS_CALIB_MS 2000UL            // Час утримання кнопки для калібрування (2 сек)
#define WARMUP_DURATION_MS 120000UL           // Час прогріву датчика газу MQ-7 (2 хв)
#define SENSOR_READ_INTERVAL_MS 2000UL        // Інтервал опитування сенсорів (2 сек)
#define UI_UPDATE_INTERVAL_MS 200UL           // Інтервал оновлення екрану (5 FPS)
#define WIFI_SCAN_INTERVAL_MS 10000UL         // Інтервал фонового сканування Wi-Fi для роумінгу (10 сек)
#define OFFLINE_CRITICAL_TIMEOUT_MS 120000UL  // Час без Wi-Fi до критичного напису на екрані (2 хв)
#define OFFLINE_BEEP_INTERVAL_MS 5000UL       // Інтервал звукового сигналу при втраті зв'язку (5 сек)
#define QUEUE_PROCESS_INTERVAL_MS 2000UL      // Інтервал відправки збережених офлайн-пакетів (2 сек)
#define SOS_TELEMETRY_INTERVAL_MS 15000UL     // Інтервал відправки телеметрії в режимі SOS (15 сек)
#define HTTP_TIMEOUT_MS 3000                  // Макс. час очікування відповіді від сервера (3 сек)
#define BTN_CLICK_RESET_MS 1000UL             // Час скидання подвійних/потрійних кліків (1 сек)

// --- ПІНИ ---
#define PIN_MQ7_ANALOG 34
#define PIN_BUTTON_SOS 19
#define PIN_SW420 18
#define PIN_BUZZER 4
#define PIN_DHT 13
#define PIN_BATTERY_ADC 35

// --- СТАНИ СИСТЕМИ ---
enum SystemState {
  PROVISIONING,
  ASK_CALIBRATION,
  WARMING_UP,
  CONNECT_CHECKPOINT,
  READY,
  SOS_MODE
};
SystemState currentState;

// --- ОБ'ЄКТИ ---
Adafruit_SSD1306 display(128, 64, &Wire, -1);
DHT dht(PIN_DHT, DHT22);
Preferences preferences;

// --- WI-FI РОУМІНГ ---
struct KnownNetwork {
  String ssid;
  String password;
};
std::vector<KnownNetwork> knownNetworks;
unsigned long lastWifiScanMs = 0;
bool wifiScanActive = false;

// --- PROVISIONING (Точка доступу) ---
WebServer server(80);
String baseSsid = "";
String basePass = "";

// --- ОФЛАЙН ЧЕРГА ТЕЛЕМЕТРІЇ ---
std::queue<String> telemetryQueue;
const size_t MAX_QUEUE_SIZE = 30;
// Зберігаємо до 30 записів (~5 хвилин офлайну)
unsigned long lastQueueProcessMs = 0;

// --- ГЛОБАЛЬНІ ЗМІННІ ---
unsigned long lastVibrationMs = 0;
unsigned long lastDataSendMs = 0;
unsigned long warningStartMs = 0;
unsigned long btnPressStart = 0;
unsigned long stateStartMs = 0;
unsigned long lastSensorReadMs = 0;
unsigned long lastUiUpdateMs = 0;
unsigned long offlineStartMs = 0;
bool lowBatteryAlertSent = false;

int btnClicks = 0;
unsigned long lastClickMs = 0;
bool immobilityWarning = false;
bool isSosActive = false;
String activeSosReason = "NONE";
String apPass = "ESP32123123";  // Встановлюємо пароль

float cachedTemp = 0.0;
float cachedHum = 0.0;

// Змінна для переривання (Рух)
volatile bool motionDetected = false;

// Змінні для неблокуючого зумера
int buzzerBeepsLeft = 0;
unsigned long buzzerNextToggleMs = 0;
bool buzzerState = false;

// ==========================================
// ⚡ АПАРАТНЕ ПЕРЕРИВАННЯ (Рух)
// ==========================================
void IRAM_ATTR motionISR() {
  motionDetected = true;
}

// ==========================================
// 🔊 НЕБЛОКУЮЧИЙ ЗУМЕР
// ==========================================
void triggerBeep(int count, int duration = 100) {
  buzzerBeepsLeft = count * 2;
  // кожен біп: фаза ON + фаза OFF
  buzzerState = true;
  digitalWrite(PIN_BUZZER, HIGH);
  buzzerNextToggleMs = millis() + duration;
}

void handleBuzzer() {
  if (buzzerBeepsLeft > 0 && millis() >= buzzerNextToggleMs) {
    buzzerBeepsLeft--;
    buzzerState = !buzzerState;
    digitalWrite(PIN_BUZZER, buzzerState ? HIGH : LOW);
    buzzerNextToggleMs = millis() + 100;
  }
}

// Синхронний звук (лише для setup / коротких подій)
void syncBeep(int count, int ms) {
  for (int i = 0; i < count; i++) {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(ms);
    digitalWrite(PIN_BUZZER, LOW);
    if (i < count - 1) delay(ms);
  }
}

// ==========================================
// 💨 ЗЧИТУВАННЯ ГАЗУ (Deadband 100)
// ==========================================
int getCleanGas() {
  int raw = analogRead(PIN_MQ7_ANALOG);
  return (raw <= 100) ? 0 : (raw - 100);
}

// ==========================================
// 🔋 ВІДСОТОК ЗАРЯДУ
// ==========================================
int getBatteryPct() {
  return constrain(map(analogRead(PIN_BATTERY_ADC), 3100, 4095, 0, 100), 0, 100);
}

// ==========================================
// 🌡 ОНОВЛЕННЯ КЕШУ СЕНСОРІВ DHT22
// ==========================================
void updateSensors() {
  if (millis() - lastSensorReadMs < SENSOR_READ_INTERVAL_MS) return;
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) cachedTemp = t;
  if (!isnan(h)) cachedHum = h;
  lastSensorReadMs = millis();
}

// ==========================================
// 🚨 ВІДПРАВКА ДАНИХ НА СЕРВЕР (із таймаутом)
// ==========================================
void sendTelemetry(bool isSos, String reason = "Normal") {
  StaticJsonDocument<384> doc;
  doc["mac_address"] = WiFi.macAddress();  // мак пристрою
  doc["ap_uid"] = WiFi.BSSIDstr();
  // мак репітера
  doc["battery"] = getBatteryPct();
  // відсоток батареї пристрою
  doc["gas_level"] = getCleanGas();
  // метан
  doc["is_sos"] = isSos;
  // сигнал сос
  doc["reason"] = reason;
  // причина сигналу
  doc["rssi"] = WiFi.RSSI();
  // якість зв'язку з репітером
  doc["temperature"] = cachedTemp;
  // температура
  doc["humidity"] = cachedHum;
  // вологість
  doc["fw_version"] = FIRMWARE_VERSION;  // версія прошивки

  doc["is_moving"] = (millis() - lastVibrationMs < NO_MOTION_TIMEOUT_MS);

  String json;
  serializeJson(doc, json);
  if (WiFi.status() != WL_CONNECTED) {
    if (telemetryQueue.size() < MAX_QUEUE_SIZE) telemetryQueue.push(json);
    return;
  }

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);  // таймаут щоб не зависати
  http.begin(String(SERVER_ADDRESS) + TELEMETRY_ENDPOINT);
  http.addHeader("Content-Type", "application/json");
  int httpCode = http.POST(json);

  if (httpCode == 200 || httpCode == 201) {
    lastDataSendMs = millis();
  } else {
    Serial.printf("HTTP Post failed. Code: %d\n", httpCode);
    if (telemetryQueue.size() < MAX_QUEUE_SIZE) telemetryQueue.push(json);
  }
  http.end();
}

void processTelemetryQueue() {
  if (WiFi.status() != WL_CONNECTED || telemetryQueue.empty()) return;

  String json = telemetryQueue.front();
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.begin(String(SERVER_ADDRESS) + TELEMETRY_ENDPOINT);
  http.addHeader("Content-Type", "application/json");
  int httpCode = http.POST(json);

  if (httpCode == 200 || httpCode == 201) {
    telemetryQueue.pop();
    // Видаляємо успішно відправлене
  }
  http.end();
}

// ==========================================
// 🔘 ОБРОБКА КНОПКИ (із debounce та виправленою логікою SOS_CANCELLED)
// ==========================================
void updateButton() {
  bool pressed = (digitalRead(PIN_BUTTON_SOS) == LOW);
  if (pressed) {
    if (btnPressStart == 0) btnPressStart = millis();
    unsigned long held = millis() - btnPressStart;

    // Довге утримання → ручний SOS
    if (held >= LONG_PRESS_SOS_MS && currentState == READY) {
      isSosActive = true;
      activeSosReason = "MANUAL_SOS";
      sendTelemetry(true, "Manual SOS pressed");
      currentState = SOS_MODE;
      btnPressStart = 0;
    }
  } else {
    if (btnPressStart != 0) {
      unsigned long held = millis() - btnPressStart;
      // Захист від брязкоту: 50мс < held < 500мс = один клік
      if (held > 50 && held < 500) {
        btnClicks++;
        lastClickMs = millis();
      }
      btnPressStart = 0;
    }
  }

  // Скидання лічильника кліків через 1 секунду бездіяльності
  if (millis() - lastClickMs > BTN_CLICK_RESET_MS) btnClicks = 0;
  // 3 кліки — скасування SOS або попередження нерухомості
  if (btnClicks >= 3) {
    if (currentState == SOS_MODE || immobilityWarning) {
      // [ВИПРАВЛЕНО] Повідомляємо сервер про скасування SOS
      if (currentState == SOS_MODE) {
        sendTelemetry(false, "SOS_CANCELLED");
      }
      isSosActive = false;
      immobilityWarning = false;
      currentState = READY;
      lastVibrationMs = millis();
      // Зупиняємо зумер (неблокуючий і прямий)
      buzzerBeepsLeft = 0;
      digitalWrite(PIN_BUZZER, LOW);
      syncBeep(2, 50);
    }
    btnClicks = 0;
  }
}

// ==========================================
// 🖼 ГРАФІЧНІ ХЕЛПЕРИ
// ==========================================
void drawYellowHeader(const char* title, const char* rightInfo = nullptr) {
  String cpTitle = utf8ukr(title);
  String cpRight = rightInfo != nullptr ? utf8ukr(rightInfo) : "";

  display.fillRect(0, 0, 128, 16, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(3, 4);
  display.print(cpTitle);

  if (cpRight.length() > 0) {
    int len = cpRight.length() * 6;
    display.setCursor(127 - len, 4);
    display.print(cpRight);
  }
}

void drawProgressBar(int x, int y, int w, int h, float pct) {
  pct = constrain(pct, 0.0f, 1.0f);
  display.drawRect(x, y, w, h, SSD1306_WHITE);
  int fill = (int)((w - 4) * pct);
  if (fill > 0) display.fillRect(x + 2, y + 2, fill, h - 4, SSD1306_WHITE);
}

void drawVLine(int x, int y1, int y2) {
  display.drawLine(x, y1, x, y2, SSD1306_WHITE);
}

// ==========================================
// 🕵️ САМОДІАГНОСТИКА (POST)
// ==========================================
bool runSystemCheck() {
  display.clearDisplay();
  display.setTextSize(1);
  drawYellowHeader("ДІАГНОСТИКА", FIRMWARE_VERSION);
  display.setTextColor(SSD1306_WHITE);
  display.display();
  delay(300);
  bool allGood = true;
  int yPos = 19;
  auto checkLine = [&](const char* label, bool ok) {
    display.setCursor(2, yPos);
    display.setTextColor(SSD1306_WHITE);
    display.print(label);
    display.print(": ");
    if (ok) {
      display.print("OK");
    } else {
      display.print("FAIL!");
      allGood = false;
    }
    display.display();
    yPos += 10;
    delay(400);
  };
  float t = dht.readTemperature();
  checkLine("DHT22", !isnan(t));

  analogRead(PIN_MQ7_ANALOG);
  delay(10);  // Прогрів АЦП
  int mqRaw = analogRead(PIN_MQ7_ANALOG);
  checkLine("MQ-7 ", mqRaw >= 0 && mqRaw <= 4095);

  checkLine("SW420", true);

  display.setCursor(2, yPos);
  display.setTextColor(SSD1306_WHITE);
  display.print("BUZZ : ");
  syncBeep(1, 150);
  display.print("OK");
  display.display();
  delay(400);

  display.clearDisplay();
  drawYellowHeader(allGood ? "ДІАГНОСТИКА ОК" : "ПОМИЛКА ДІАГН.");
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(allGood ? 14 : 8, 26);
  display.println(utf8ukr(allGood ? " ВСЕ ОК!" : " АПАР. ЕРОР"));
  display.setTextSize(1);
  display.display();

  if (allGood) {
    syncBeep(2, 50);
  } else {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(1000);
    digitalWrite(PIN_BUZZER, LOW);
  }
  delay(2000);
  return allGood;
}

// ==========================================
// 🔧 БЕЗПЕЧНЕ ОТРИМАННЯ MAC-АДРЕСИ
// ==========================================
String getSafeMacAddress() {
  String mac = WiFi.macAddress();
  if (mac == "00:00:00:00:00:00") {
    WiFi.mode(WIFI_STA);
    delay(100);
    mac = WiFi.macAddress();
  }
  return mac;
}

// ==========================================
// 📡 УПРАВЛІННЯ WI-FI МЕРЕЖАМИ
// ==========================================
void saveNetworksToPrefs() {
  DynamicJsonDocument doc(4096);
  JsonArray arr = doc.to<JsonArray>();
  for (const auto& net : knownNetworks) {
    JsonObject obj = arr.createNestedObject();
    obj["ssid"] = net.ssid;
    obj["password"] = net.password;
  }
  String out;
  serializeJson(doc, out);
  preferences.begin("device-state", false);
  preferences.putString("wifi_nets", out);
  preferences.end();
}

void loadNetworksFromPrefs() {
  preferences.begin("device-state", true);
  baseSsid = preferences.getString("base_ssid", "");
  basePass = preferences.getString("base_pass", "");
  String in = preferences.getString("wifi_nets", "");
  preferences.end();

  knownNetworks.clear();
  if (in.length() > 0) {
    DynamicJsonDocument doc(4096);
    if (!deserializeJson(doc, in)) {
      for (JsonObject net : doc.as<JsonArray>()) {
        KnownNetwork kn;
        kn.ssid = net["ssid"].as<String>();
        kn.password = net["password"].as<String>();
        if (kn.ssid.length() > 0) {
          knownNetworks.push_back(kn);
        }
      }
    }
  }
}

void fetchKnownNetworks() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.begin(String(SERVER_ADDRESS) + WIFI_API_ENDPOINT);
  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    DynamicJsonDocument doc(4096);
    DeserializationError error = deserializeJson(doc, payload);
    if (!error) {
      knownNetworks.clear();
      for (JsonObject net : doc.as<JsonArray>()) {
        KnownNetwork kn;
        kn.ssid = net["ssid"].as<String>();
        kn.password = net["password"].as<String>();
        if (kn.ssid.length() > 0) {
          knownNetworks.push_back(kn);
        }
      }
      saveNetworksToPrefs();
    }
  }
  http.end();
}

// ==========================================
// 🔄 OTA ОНОВЛЕННЯ ПРОШИВКИ
// ==========================================
void checkFirmwareUpdate() {
  if (WiFi.status() != WL_CONNECTED) return;
  display.clearDisplay();
  drawYellowHeader("ОНОВЛЕННЯ OTA");
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(2, 20);
  display.print(utf8ukr("Пошук оновлень..."));
  display.display();

  Serial.println("Checking for OTA updates...");
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  String url = String(SERVER_ADDRESS) + OTA_CHECK_ENDPOINT + "?mac=" + WiFi.macAddress() + "&version=" + String(FIRMWARE_VERSION);
  http.begin(url);
  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    DynamicJsonDocument doc(1024);
    if (!deserializeJson(doc, payload) && doc.containsKey("url") && doc.containsKey("version")) {
      String newVersion = doc["version"].as<String>();
      String binUrl = doc["url"].as<String>();

      if (newVersion != String(FIRMWARE_VERSION)) {
        Serial.println("New firmware found: " + newVersion);
        display.setCursor(2, 35);
        display.print(utf8ukr("Оновлення: ") + newVersion);
        display.display();

        // --- ПРОГРЕС БАР ЗАВАНТАЖЕННЯ ---
        httpUpdate.onProgress([](int current, int total) {
          float pct = (float)current / (float)total;
          display.clearDisplay();
          drawYellowHeader("ОНОВЛЕННЯ OTA", FIRMWARE_VERSION);

          display.setTextColor(SSD1306_WHITE);
          display.setCursor(2, 20);
          display.print(utf8ukr("Завантаження: ") + String((int)(pct * 100)) + "%");
          drawProgressBar(2, 35, 124, 10, pct);
          display.setCursor(2, 50);

          display.print(current / 1024);
          display.print("KB / ");
          display.print(total / 1024);
          display.print("KB");
          display.display();
        });
        WiFiClient client;
        t_httpUpdate_return ret = httpUpdate.update(client, binUrl);
        if (ret == HTTP_UPDATE_FAILED) {
          String errStr = httpUpdate.getLastErrorString();
          Serial.printf("OTA Failed (%d): %s\n", httpUpdate.getLastError(), errStr.c_str());

          // --- ВІДПРАВКА СТАТУСУ ПОМИЛКИ НА СЕРВЕР ---
          HTTPClient logHttp;
          logHttp.setTimeout(HTTP_TIMEOUT_MS);
          logHttp.begin(String(SERVER_ADDRESS) + OTA_LOG_ENDPOINT);
          logHttp.addHeader("Content-Type", "application/json");
          StaticJsonDocument<256> logDoc;
          logDoc["mac_address"] = WiFi.macAddress();
          logDoc["version"] = newVersion;
          logDoc["status"] = "FAILED";
          logDoc["message"] = errStr;
          String logJson;
          serializeJson(logDoc, logJson);
          logHttp.POST(logJson);
          logHttp.end();

          display.clearDisplay();
          drawYellowHeader("ПОМИЛКА OTA");
          display.setTextColor(SSD1306_WHITE);
          display.setCursor(2, 25);
          display.print(utf8ukr("Помилка:"));
          display.setCursor(2, 35);
          display.print(errStr);
          display.display();
          delay(3000);
        }
      }
    }
  }
  http.end();
}

// ==========================================
//  SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  Serial.println("\n\n========================================");
  Serial.println("ESP32 GLIBYNA 4.0 SYSTEM");
  Serial.println("Type HELP for available commands");
  Serial.println("========================================\n");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true, true);
  delay(100);

  pinMode(PIN_SW420, INPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_BUTTON_SOS, INPUT_PULLUP);

  // Апаратне переривання на датчик руху
  attachInterrupt(digitalPinToInterrupt(PIN_SW420), motionISR, RISING);
  Wire.begin(21, 22);
  Wire.setClock(400000);  // 400kHz для швидшого дисплею

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    for (;;)
      ;
  }
  display.clearDisplay();
  dht.begin();

  loadNetworksFromPrefs();

  preferences.begin("device-state", false);
  bool isProvisioned = preferences.getBool("provisioned", false);
  if (!isProvisioned) {
    currentState = PROVISIONING;
    WiFi.mode(WIFI_AP);
    String mac = getSafeMacAddress();
    String apName = "ESP-" + mac.substring(mac.length() - 5);
    apName.replace(":", "");

    WiFi.softAP(apName.c_str(), apPass.c_str());
    server.on("/", HTTP_GET, []() {
      String html = "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
      html += "<style>body{font-family:sans-serif; padding:20px; background:#121212; color:#fff;} input{width:100%; padding:10px; margin-bottom:15px; border-radius:5px; border:none;} input[type='submit']{background:#8a63d2; color:#fff; font-weight:bold; cursor:pointer;}</style></head><body>";
      html += "<h2>GLYBYNA 4.0 SETUP</h2>";
      html += "<p>MAC Address: <b>" + getSafeMacAddress() + "</b></p>";
      html += "<form action='/save' method='POST'>";

      html += "Checkpoint SSID:<br><input type='text' name='ssid'><br>";
      html += "Checkpoint PASS:<br><input type='text' name='pass'><br>";
      html += "<input type='submit' value='SAVE & RESTART'></form></body></html>";
      server.send(200, "text/html", html);
    });
    server.on("/save", HTTP_POST, []() {
      String ssid = server.arg("ssid");
      String pass = server.arg("pass");
      preferences.putString("base_ssid", ssid);
      preferences.putString("base_pass", pass);
      preferences.putBool("provisioned", true);
      preferences.end();


      server.send(200, "text/html", "<html><body style='background:#121212;color:#fff;'><h2>Saved!</h2><p>Device is restarting...</p></body></html>");
      delay(1000);
      esp_restart();
    });
    server.begin();

    Serial.println("\n=========================================");
    Serial.println("DEVICE IN AP PROVISIONING MODE");
    Serial.println("Connect to WiFi: " + apName);
    Serial.println("Password: " + apPass);
    Serial.println("Open browser: http://192.168.4.1");
    Serial.println("=========================================");
  } else {
    preferences.end();
    bool hwOk = runSystemCheck();
    if (!hwOk) {
      display.clearDisplay();
      drawYellowHeader("!! БЛОКУВАННЯ !!");
      display.setTextColor(SSD1306_WHITE);
      display.setTextSize(1);
      display.setCursor(4, 22);
      display.println(utf8ukr("Апаратна помилка."));
      display.setCursor(4, 33);
      display.println(utf8ukr("Віддайте в ремонт."));
      display.display();
      while (true) {
        digitalWrite(PIN_BUZZER, HIGH);
        delay(100);
        digitalWrite(PIN_BUZZER, LOW);
        delay(5000);
      }
    }
    currentState = ASK_CALIBRATION;
  }
}

// ==========================================
// 📟 ОБРОБКА КОМАНД SERIAL MONITOR
// ==========================================
void handleSerialCommands() {
  if (!Serial.available()) return;

  String command = Serial.readStringUntil('\n');
  command.trim();
  command.toUpperCase();
  if (command.isEmpty()) return;

  Serial.println("\n=== COMMAND RECEIVED ===");
  Serial.print("> ");
  Serial.println(command);
  if (command == "RESET") {
    Serial.println("Resetting device...");
    delay(100);
    esp_restart();
  } else if (command == "CLEAR") {
    Serial.println("Clearing provisioning data...");
    preferences.begin("device-state", false);
    preferences.clear();
    preferences.end();
    Serial.println("Provisioning cleared. Restarting...");
    delay(1000);
    esp_restart();
  } else if (command == "FACTORY") {
    Serial.println("FACTORY RESET - clearing ALL data...");
    preferences.begin("device-state", false);
    preferences.clear();
    preferences.end();
    nvs_flash_erase();
    nvs_flash_init();
    Serial.println("Factory reset complete. Restarting...");
    delay(1000);
    esp_restart();
  } else if (command == "STATUS") {
    Serial.println("\n--- DEVICE STATUS ---");
    Serial.print("State: ");
    switch (currentState) {
      case PROVISIONING:
        Serial.println("PROVISIONING");
        break;
      case ASK_CALIBRATION: Serial.println("ASK_CALIBRATION"); break;
      case WARMING_UP: Serial.println("WARMING_UP"); break;
      case CONNECT_CHECKPOINT: Serial.println("CONNECT_CHECKPOINT"); break;
      case READY:
        Serial.println("READY");
        break;
      case SOS_MODE: Serial.println("SOS_MODE"); break;
    }
    Serial.print("Firmware: ");
    Serial.println(FIRMWARE_VERSION);
    Serial.print("MAC: ");
    Serial.println(getSafeMacAddress());
    Serial.print("WiFi: ");
    Serial.println(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected");
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("IP: ");
      Serial.println(WiFi.localIP());
      Serial.print("RSSI: ");
      Serial.print(WiFi.RSSI());
      Serial.println(" dBm");
    }
    Serial.print("Battery: ");
    Serial.print(getBatteryPct());
    Serial.println("%");
    Serial.print("Gas: ");
    Serial.print(getCleanGas());
    Serial.println("% LEL");
    Serial.print("Temperature: ");
    Serial.print(cachedTemp);
    Serial.println(" C");
    Serial.print("Humidity: ");
    Serial.print(cachedHum);
    Serial.println("%");
    Serial.print("Motion: ");
    Serial.println(motionDetected ? "YES" : "NO");
    Serial.print("SOS Active: ");
    Serial.println(isSosActive ? "YES" : "NO");
    Serial.println("----------------------");
  } else if (command == "HELP") {
    Serial.println("\n=== AVAILABLE COMMANDS ===");
    Serial.println("RESET   - Soft restart device");
    Serial.println("CLEAR   - Clear provisioning only");
    Serial.println("FACTORY - Full factory reset");
    Serial.println("STATUS  - Show current device status");
    Serial.println("SOS     - Manually trigger SOS mode");
    Serial.println("CANCEL  - Cancel SOS mode if active");
    Serial.println("HELP    - Show this help");
    Serial.println("===========================");
  } else if (command == "SOS") {
    if (currentState == READY) {
      Serial.println("Manually triggering SOS...");
      isSosActive = true;
      activeSosReason = "MANUAL_SOS_CMD";
      sendTelemetry(true, "Manual SOS via serial");
      currentState = SOS_MODE;
    } else {
      Serial.println("Cannot trigger SOS in current state");
    }
  } else if (command == "CANCEL") {
    if (currentState == SOS_MODE || immobilityWarning) {
      Serial.println("Cancelling SOS/warning...");
      // Повідомляємо сервер і через serial-команду
      if (currentState == SOS_MODE) {
        sendTelemetry(false, "SOS_CANCELLED");
      }
      isSosActive = false;
      immobilityWarning = false;
      currentState = READY;
      lastVibrationMs = millis();
      buzzerBeepsLeft = 0;
      digitalWrite(PIN_BUZZER, LOW);
      syncBeep(2, 50);
    } else {
      Serial.println("No active SOS/warning to cancel");
    }
  } else if (command == "OTA") {
    Serial.println("Manual OTA update check...");
    checkFirmwareUpdate();
  } else {
    Serial.println("Unknown command. Type HELP for available commands");
  }

  Serial.println("=== COMMAND FINISHED ===\n");
}

// ==========================================
// 🔄 ГОЛОВНИЙ ЦИКЛ
// ==========================================
void loop() {
  handleSerialCommands();
  updateButton();
  handleBuzzer();  // неблокуючий зумер
  updateSensors();

  int gasVal = getCleanGas();
  // Обробка переривання від датчика руху
  // Обробка переривання від датчика руху
  if (motionDetected) {
    motionDetected = false;

    // ЗАХИСТ ВІД ВІБРАЦІЇ ЗУМЕРА
    // Якщо попередження щойно почалося (менше 1.5 сек тому), 
    // ігноруємо цей сигнал, бо це вібрація від самого зумера.
    if (immobilityWarning && (millis() - warningStartMs < 1500)) {
      // Нічого не робимо, це хибне спрацювання
    } else {
      // Дійсний рух
      lastVibrationMs = millis();
      
      if (immobilityWarning && currentState != SOS_MODE) {
        immobilityWarning = false;
        buzzerBeepsLeft = 0;
        digitalWrite(PIN_BUZZER, LOW);
      }
    }
  }

  // --- ОБРОБКА ЧЕРГИ ТЕЛЕМЕТРІЇ ---
  // Відправляємо по 1 збереженому повідомленню кожні 2 секунди
  if (WiFi.status() == WL_CONNECTED && !telemetryQueue.empty() && millis() - lastQueueProcessMs > QUEUE_PROCESS_INTERVAL_MS) {
    processTelemetryQueue();
    lastQueueProcessMs = millis();
  }

  // --- WI-FI ROAMING ТА РЕКОННЕКТ (ФОНОВИЙ РЕЖИМ БЕЗ БЛОКУВАННЯ UI) ---
  if ((currentState == READY || currentState == SOS_MODE) && millis() - lastWifiScanMs > WIFI_SCAN_INTERVAL_MS) {
    if (!wifiScanActive) {
      WiFi.scanNetworks(true);
      // асинхронне сканування
      wifiScanActive = true;
    }
  }

  if (wifiScanActive) {
    int n = WiFi.scanComplete();
    if (n >= 0) {
      int bestRssi = -1000;
      String bestSsid = "";
      String bestPass = "";
      String bestBssid = "";
      for (int i = 0; i < n; ++i) {
        String ssid = WiFi.SSID(i);
        int rssi = WiFi.RSSI(i);
        String bssid = WiFi.BSSIDstr(i);

        if (ssid == baseSsid && rssi > bestRssi) {
          bestRssi = rssi;
          bestSsid = baseSsid;
          bestPass = basePass;
          bestBssid = bssid;
        }

        for (const auto& kn : knownNetworks) {
          if (kn.ssid == ssid && rssi > bestRssi) {
            bestRssi = rssi;
            bestSsid = kn.ssid;
            bestPass = kn.password;
            bestBssid = bssid;
          }
        }
      }

      String currentBssid = WiFi.BSSIDstr();
      bool isDisconnected = (WiFi.status() != WL_CONNECTED);
      
      if (bestSsid != "") {
        if (isDisconnected || (bestBssid != currentBssid && (bestRssi > WiFi.RSSI() + 10 || WiFi.RSSI() < -75))) {
          Serial.println("Roaming/Reconnecting: " + currentBssid + " -> " + bestBssid + " (" + bestSsid + ")");
          WiFi.disconnect();
          WiFi.begin(bestSsid.c_str(), bestPass.c_str());
          // ПРИБРАНО БЛОКУЮЧИЙ ЦИКЛ! Екран не закриватиметься.
          // ESP32 підключиться у фоні, продовжуючи збирати телеметрію в чергу.
        }
      }

      WiFi.scanDelete();
      wifiScanActive = false;
      lastWifiScanMs = millis();
    } else if (n == WIFI_SCAN_FAILED) {
      wifiScanActive = false;
      lastWifiScanMs = millis();
    }
  }

  bool needUiUpdate = (millis() - lastUiUpdateMs > UI_UPDATE_INTERVAL_MS);
  switch (currentState) {

    // ——————————————————————————————————————
    case PROVISIONING:
      {
        server.handleClient();
        // Обов'язково обробляємо веб-запити
        if (!needUiUpdate) break;
        String mac = getSafeMacAddress();
        String apName = "ESP-" + mac.substring(mac.length() - 5);
        apName.replace(":", "");

        display.clearDisplay();
        drawYellowHeader("== НАЛАШТ. AP ==");
        display.setTextColor(SSD1306_WHITE);
        display.setTextSize(1);
        display.setCursor(2, 19);
        display.print("Wi-Fi: ");
        display.print(apName);
        display.setCursor(2, 30);
        display.print(utf8ukr("Пароль: ") + apPass);
        display.drawLine(0, 40, 127, 40, SSD1306_WHITE);
        display.setCursor(2, 45);
        display.print("IP: 192.168.4.1");
        display.setCursor(2, 55);
        display.print(utf8ukr("Чекаю налаштувань..."));
        display.display();

        btnClicks = 0;
        // Скидаємо натискання кнопок, щоб уникнути помилкових спрацювань
        break;
      }

    // ——————————————————————————————————————
    case ASK_CALIBRATION:
      {
        if (!needUiUpdate) break;
        float p = (btnPressStart > 0)
                    ? (float)(millis() - btnPressStart) / LONG_PRESS_CALIB_MS
                    : 0.0f;
        display.clearDisplay();
        drawYellowHeader("ЗАПУСК");
        display.setTextColor(SSD1306_WHITE);
        display.setTextSize(1);
        display.setCursor(2, 19);
        display.print(utf8ukr("Клік = ШВИДКИЙ СТАРТ"));
        display.setCursor(2, 29);
        display.print(utf8ukr("Утрим= КАЛІБРУВАННЯ"));
        display.drawLine(0, 39, 127, 39, SSD1306_WHITE);
        display.setCursor(2, 43);
        display.print(utf8ukr("КАЛІБРУВАННЯ:"));
        drawProgressBar(80, 42, 46, 9, p);
        display.display();
        if (btnClicks == 1) {
          currentState = CONNECT_CHECKPOINT;
          btnClicks = 0;
        }
        if (p >= 1.0f) {
          currentState = WARMING_UP;
          stateStartMs = millis();
          btnPressStart = 0;
        }
        break;
      }

    // ——————————————————————————————————————
    case WARMING_UP:
      {
        if (!needUiUpdate) break;
        unsigned long elapsed = millis() - stateStartMs;
        float pct = (float)elapsed / WARMUP_DURATION_MS;
        if (pct >= 1.0f) currentState = CONNECT_CHECKPOINT;
        unsigned long secLeft = (WARMUP_DURATION_MS - elapsed) / 1000UL;

        display.clearDisplay();
        drawYellowHeader("ПРОГРІВ MQ-7");
        display.setTextColor(SSD1306_WHITE);
        display.setTextSize(1);
        display.setCursor(2, 19);
        display.print(utf8ukr("НАГРІВ СЕНСОРА..."));
        display.setCursor(2, 29);
        display.print(utf8ukr("Будь ласка, зачекайте."));
        display.drawLine(0, 39, 127, 39, SSD1306_WHITE);
        display.setCursor(2, 43);
        display.print(utf8ukr("ЗАЛИШИЛОСЬ:"));
        drawProgressBar(2, 52, 124, 9, pct);
        display.setTextSize(2);
        display.setCursor(80, 41);
        char buf[8];
        sprintf(buf, "%3lus", secLeft);
        display.print(buf);
        display.setTextSize(1);
        display.display();
        break;
      }

    // ——————————————————————————————————————
    case CONNECT_CHECKPOINT:
      {
        display.clearDisplay();
        drawYellowHeader("БАЗА");
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(2, 19);
        display.print(utf8ukr("Пошук WiFi..."));
        drawProgressBar(2, 30, 124, 8, 0.0f);
        display.display();

        wifiScanActive = false;
        lastWifiScanMs = millis();
        int n = WiFi.scanNetworks();
        int bestRssi = -1000;
        String bestSsid = "";
        String bestPass = "";
        for (int i = 0; i < n; ++i) {
          String ssid = WiFi.SSID(i);
          int rssi = WiFi.RSSI(i);

          if (ssid == baseSsid && rssi > bestRssi) {
            bestRssi = rssi;
            bestSsid = baseSsid;
            bestPass = basePass;
          }

          for (const auto& kn : knownNetworks) {
            if (kn.ssid == ssid && rssi > bestRssi) {
              bestRssi = rssi;
              bestSsid = kn.ssid;
              bestPass = kn.password;
            }
          }
        }
        WiFi.scanDelete();
        if (bestSsid == "") {
          bestSsid = baseSsid;
          bestPass = basePass;
        }

        display.clearDisplay();
        drawYellowHeader("БАЗА");
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(2, 19);
        display.print(utf8ukr("Підключення до:"));
        display.setCursor(2, 30);
        display.print(bestSsid);
        display.display();

        WiFi.disconnect();
        WiFi.begin(bestSsid.c_str(), bestPass.c_str());
        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 20) {
          unsigned long t = millis();
          while (millis() - t < 500) {
            handleBuzzer();
            delay(10);
          }
          attempts++;
          display.clearDisplay();
          drawYellowHeader("БАЗА");
          display.setTextColor(SSD1306_WHITE);
          display.setCursor(2, 19);
          display.print(utf8ukr("Підключення..."));
          char dots[5] = "....";
          dots[attempts % 5] = '\0';
          display.print(dots);
          drawProgressBar(2, 30, 124, 8, (float)attempts / 20.0f);
          display.display();
        }

        display.clearDisplay();
        if (WiFi.status() == WL_CONNECTED) {
          Serial.println("Connected to AP MAC (BSSID): " + WiFi.BSSIDstr());
          // Для тестування (вивід MAC мережі)
          fetchKnownNetworks();
          sendTelemetry(false, "CHECKPOINT_ENTRY");

          // --- БЕЗПЕЧНЕ ОНОВЛЕННЯ ПРОШИВКИ ---
          if (WiFi.SSID() == baseSsid) {
            checkFirmwareUpdate();
          } else {
            Serial.println("Connected to internal repeater. Skipping OTA.");
          }

          syncBeep(2, 100);
          display.clearDisplay();  // Фікс накладання тексту IP на повідомлення OTA
          drawYellowHeader("БАЗА  ОК");
          display.setTextColor(SSD1306_WHITE);
          display.setTextSize(1);
          display.setCursor(2, 20);
          display.print(utf8ukr("Вхід записано."));
          display.setCursor(2, 31);
          display.print("IP: ");
          display.print(WiFi.localIP());
          display.setCursor(2, 42);
          display.print("RSSI: ");
          display.print(WiFi.RSSI());
          display.print(" dBm");
          display.drawLine(0, 53, 127, 53, SSD1306_WHITE);
          display.setCursor(20, 57);
          display.print(utf8ukr("Початок роботи..."));
        } else {
          drawYellowHeader("!! НЕМАЄ МЕРЕЖІ");
          display.setTextColor(SSD1306_WHITE);
          display.setCursor(4, 22);
          display.print(utf8ukr("WiFi не знайдено."));
          display.setCursor(4, 33);
          display.print(utf8ukr("Робота ОФЛАЙН."));
          display.setCursor(4, 44);
          display.print(utf8ukr("Дані у черзі."));
        }
        display.display();
        delay(2500);
        btnClicks = 0;
        btnPressStart = 0;
        lastVibrationMs = millis();
        lastDataSendMs = millis();
        currentState = READY;
        break;
      }

    // ——————————————————————————————————————
    case READY:
      {
        // Перевірка газу → SOS
        if (gasVal > 150) {
          isSosActive = true;
          activeSosReason = "GAS_ALARM";
          sendTelemetry(true, "Gas Critical!");
          currentState = SOS_MODE;
          break;
        }

        // Перевірка нерухомості
        if (millis() - lastVibrationMs > NO_MOTION_TIMEOUT_MS && !immobilityWarning) {
          immobilityWarning = true;
          warningStartMs = millis();
          triggerBeep(5);  // неблокуючий — не замерзає loop
        }
        if (immobilityWarning && (millis() - warningStartMs > SOS_GRACE_PERIOD_MS)) {
          isSosActive = true;
          activeSosReason = "NO_MOTION";
          sendTelemetry(true, "NO_MOTION");
          currentState = SOS_MODE;
          break;
        }

        // --- ПЕРЕВІРКА БАТАРЕЇ ---
        int bat = getBatteryPct();
        if (bat <= 10 && !lowBatteryAlertSent) {
          lowBatteryAlertSent = true;
          sendTelemetry(false, "LOW_BATTERY_10");
        } else if (bat > 15) {
          lowBatteryAlertSent = false;
        }

        // --- ПЕРЕВІРКА ВТРАТИ ЗВ'ЯЗКУ (ОФЛАЙН) ---
        if (WiFi.status() != WL_CONNECTED) {
          if (offlineStartMs == 0) offlineStartMs = millis();
          // Якщо офлайн більше 2 хвилин
          if (millis() - offlineStartMs > OFFLINE_CRITICAL_TIMEOUT_MS) {
            // Пікаємо кожні 5 секунд щоб шахтар звернув увагу на екран
            if ((millis() - offlineStartMs) % OFFLINE_BEEP_INTERVAL_MS < 50) {
              triggerBeep(2, 50); 
            }
          }
        } else {
          offlineStartMs = 0;
        }

        if (!needUiUpdate) break;

        display.clearDisplay();
        char rssiStr[12];
        sprintf(rssiStr, "%ddBm", WiFi.RSSI());
        drawYellowHeader("ГЛИБИНА 4.0", WiFi.status() == WL_CONNECTED ? rssiStr : "ОФЛАЙН");

        display.setTextColor(SSD1306_WHITE);
        display.setTextSize(1);

        drawVLine(47, 17, 51);
        drawVLine(92, 17, 51);
        // --- Колонка 1: CO газ ---
        display.setCursor(2, 18);
        display.print(utf8ukr("МЕТАН"));
        display.setTextSize(2);
        display.setCursor(2, 27);
        if (gasVal < 10) display.print("  ");
        else if (gasVal < 100) display.print(" ");
        display.print(gasVal);
        display.setTextSize(1);
        display.setCursor(2, 44);
        display.print("%LEL");
        // --- Колонка 2: Температура + Вологість ---
        display.setCursor(51, 18);
        display.print(utf8ukr("ТЕМП"));
        display.setTextSize(2);
        display.setCursor(51, 27);
        if (cachedTemp >= 0 && cachedTemp < 10) display.print(" ");
        display.print(cachedTemp, 1);
        display.setTextSize(1);
        display.setCursor(51, 44);
        display.print("H:");
        display.print((int)cachedHum);
        display.print("%");

        // --- Колонка 3: Рух ---
        display.setCursor(96, 18);
        display.print(utf8ukr("РУХ"));
        display.setTextSize(2);
        display.setCursor(96, 27);
        display.print((millis() - lastVibrationMs < 2000) ? "OK" : "--");
        display.setTextSize(1);

        display.drawLine(0, 52, 127, 52, SSD1306_WHITE);
        
        // Пріоритет виводу повідомлень унизу екрану
        if (offlineStartMs > 0 && (millis() - offlineStartMs > OFFLINE_CRITICAL_TIMEOUT_MS)) {
          if ((millis() / 500) % 2 == 0) {
            display.setCursor(2, 55); display.print(utf8ukr("!! ВТРАТА ЗВ'ЯЗКУ !!"));
          } else {
            display.setCursor(2, 55); display.print(utf8ukr("ПОВЕРНІТЬСЯ НА БАЗУ!"));
          }
        } else if (immobilityWarning) {
          if ((millis() / 400) % 2 == 0) {
            display.setCursor(2, 55);
            display.print(utf8ukr("!! РУХАЙТЕСЯ !!"));
          }
          drawProgressBar(95, 54, 31, 8, (float)(millis() - warningStartMs) / SOS_GRACE_PERIOD_MS);
        } else if (btnPressStart > 0) {
          display.setCursor(2, 55);
          display.print("SOS:");
          drawProgressBar(26, 54, 100, 8, (float)(millis() - btnPressStart) / LONG_PRESS_SOS_MS);
        } else {
          display.setCursor(2, 55);
          display.print(utf8ukr("БЕЗДІЯЛЬН:"));
          drawProgressBar(64, 54, 62, 8, (float)(millis() - lastVibrationMs) / NO_MOTION_TIMEOUT_MS);
        }
        display.display();

        if (millis() - lastDataSendMs > DATA_SEND_INTERVAL_MS) sendTelemetry(false);
        break;
      }

    // ——————————————————————————————————————
    case SOS_MODE:
      {
        // Зумер SOS (без handleBuzzer — прямий контроль)
        digitalWrite(PIN_BUZZER, (millis() % 400 < 200) ? HIGH : LOW);
        if (!needUiUpdate) break;

        static bool sosFlip = false;
        sosFlip = !sosFlip;

        display.clearDisplay();
        if (sosFlip) {
          display.fillRect(0, 0, 128, 16, SSD1306_WHITE);
          display.setTextColor(SSD1306_BLACK);
        } else {
          display.setTextColor(SSD1306_WHITE);
        }
        display.setTextSize(1);
        display.setCursor(14, 4);
        display.print(utf8ukr("!! SOS ТРИВОГА !!"));

        display.setTextColor(SSD1306_WHITE);
        display.drawLine(0, 16, 127, 16, SSD1306_WHITE);
        display.setCursor(2, 19);
        display.print(utf8ukr("ПРИЧИНА:"));
        display.setCursor(2, 28);
        display.print(activeSosReason);
        if (activeSosReason == "GAS_ALARM") {
          drawVLine(76, 17, 51);
          display.setTextSize(2);
          display.setCursor(80, 20);
          display.print(getCleanGas());
          display.setTextSize(1);
          display.setCursor(80, 39);
          display.print("% LEL");
        }

        display.drawLine(0, 52, 127, 52, SSD1306_WHITE);
        display.setCursor(4, 55);
        display.print(utf8ukr("3x КЛІК = СКАСУВАТИ"));
        display.display();

        // Телеметрія SOS кожні 15 секунд
        if (millis() - lastDataSendMs > SOS_TELEMETRY_INTERVAL_MS) sendTelemetry(true, activeSosReason);
        break;
      }

  }  // end switch

  if (needUiUpdate) lastUiUpdateMs = millis();
}