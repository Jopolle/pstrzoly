#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "HX711.h"
#include "DHT.h"
#include <RH_ASK.h>
#include <SPI.h> // dla kompilacji RH_ASK

// ---------- Piny HX711 ----------
const int DT_PIN     = 10;
const int SCK_PIN    = 3;

// ---------- Piny przycisków ----------
const int DISP_PIN   = 7;  // toggle backlight
const int SAVE_PIN   = 6;  // jednorazowy podgląd masy
const int ZERO_PIN   = 4;  // tare
const int THERMO_PIN = 5;  // trigger odczytu DHT11

// ---------- DHT11 (dwa czujniki) ----------
#define DHTTYPE DHT11
DHT dht1(9, DHTTYPE);  // pierwszy DHT11 → D11
DHT dht2(11, DHTTYPE);  // drugi DHT11   → D12

// ---------- Debounce ----------
const unsigned long DEBOUNCE = 50;
unsigned long lastDisp   = 0;
unsigned long lastSave   = 0;
unsigned long lastZero   = 0;
unsigned long lastThermo = 0;

// ---------- Stany przycisków ----------
bool backlightOn = true;
bool dispLast    = HIGH;
bool saveLast    = HIGH;
bool zeroLast    = HIGH;
bool thermoLast  = HIGH;

// ---------- LCD ----------
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ---------- Tensometr ----------
HX711 scale;
float last_mass = 0.0;
const float CHANGE_THRESHOLD = 0.1;  // kg

// ---------- ASK radio ----------
RH_ASK rf_driver;

void setup() {
  // LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();

  // Przyciski z pull-up
  pinMode(DISP_PIN,   INPUT_PULLUP);
  pinMode(SAVE_PIN,   INPUT_PULLUP);
  pinMode(ZERO_PIN,   INPUT_PULLUP);
  pinMode(THERMO_PIN, INPUT_PULLUP);

  // Serial
  Serial.begin(9600);
  while (!Serial);

  // HX711
  scale.begin(DT_PIN, SCK_PIN);
  scale.set_scale(22500.0);
  scale.tare();
  Serial.println("Gotowy do pomiaru!");

  // DHT11
  dht1.begin();
  dht2.begin();

  // RF ASK
  if (!rf_driver.init()) {
    Serial.println("RF init failed");
  }
}

void loop() {
  // 1) Pomiar masy
  float m = scale.get_units(10);
  if (m < 0) m = 0;
  float mass = round(m * 1000.0) / 1000.0;
  if (abs(mass - last_mass) >= CHANGE_THRESHOLD) {
    last_mass = mass;
    Serial.print("Masa: "); Serial.print(mass,3); Serial.println(" kg");
    if (backlightOn) {
      lcd.clear();
      lcd.print("Masa: ");
      lcd.print(mass,3);
      lcd.print(" kg");
    }
  }

  // 2) DISP: toggle podświetlenie
  bool d = digitalRead(DISP_PIN);
  if (d != dispLast && millis() - lastDisp > DEBOUNCE) {
    lastDisp = millis();
    if (d == LOW) {
      backlightOn = !backlightOn;
      backlightOn ? lcd.backlight() : lcd.noBacklight();
      lcd.clear();
    }
  }
  dispLast = d;

  // 3) SAVE: pokaz jednorazowo masę
  bool s = digitalRead(SAVE_PIN);
  if (s != saveLast && millis() - lastSave > DEBOUNCE) {
    lastSave = millis();
    if (s == LOW) {
      lcd.clear();
      lcd.print("Masa: ");
      lcd.print(mass,3);
      lcd.print(" kg");
      delay(1000);
    }
  }
  saveLast = s;

  // 4) ZERO: tare
  bool z = digitalRead(ZERO_PIN);
  if (z != zeroLast && millis() - lastZero > DEBOUNCE) {
    lastZero = millis();
    if (z == LOW) {
      scale.tare();
      lcd.clear();
      lcd.print("Zerowanie...");
      delay(1000);
    }
  }
  zeroLast = z;

  // 5) THERMO: odczyt dwóch DHT11
  bool t = digitalRead(THERMO_PIN);
  float h1, t1, h2, t2;
  //if (t != thermoLast && millis() - lastThermo > DEBOUNCE) {
    lastThermo = millis();
    //if (t == LOW) {
      // DHT11 potrzebuje ~2s między odczytami
      delay(2000);
      h1 = dht1.readHumidity();
      t1 = dht1.readTemperature();
      h2 = dht2.readHumidity();
      t2 = dht2.readTemperature();
      lcd.clear();
      lcd.setCursor(0,0);
      if (isnan(t1)||isnan(h1)) lcd.print("Blad DHT1");
      else {
        lcd.print("T1:"); lcd.print(t1,1); lcd.print("C H1:"); lcd.print(h1,0); lcd.print("%");
      }
      lcd.setCursor(0,1);
      if (isnan(t2)||isnan(h2)) lcd.print("Blad DHT2");
      else {
        lcd.print("T2:"); lcd.print(t2,1); lcd.print("C H2:"); lcd.print(h2,0); lcd.print("%");
      }
      // delay by display time
      delay(2000);
    //}
  //}
  thermoLast = t;

  // 6) Wyślij wszystkie dane przez RF ASK
  {
    // upewniamy się, że mamy aktualne wartości z DHT (może od poprzedniego naciśnięcia)
    h1 = isnan(h1) ? dht1.readHumidity() : h1;
    t1 = isnan(t1) ? dht1.readTemperature() : t1;
    h2 = isnan(h2) ? dht2.readHumidity() : h2;
    t2 = isnan(t2) ? dht2.readTemperature() : t2;



    String msg = "M:" + String(mass, 3) + "kg T1:" + String(t1, 1)
           + "C H1:" + String(h1, 1) + "% T2:" + String(t2, 1)
           + "C H2:" + String(h2, 1) + "%";

  rf_driver.send((uint8_t*)msg.c_str(), msg.length());
  rf_driver.waitPacketSent();
    // debug
    //Serial.print("RF-> "); Serial.print(msg); Serial.print("   "); Serial.println(h1); 
  }

  delay(1000);
}
