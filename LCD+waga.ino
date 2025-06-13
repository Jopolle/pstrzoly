#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "HX711.h"

// ---------- Piny HX711 ----------
const int dt  = 10;
const int sck = 3;

// ---------- Piny przycisków ----------
const int dispPin   = 7;  // włącz/wyłącz LCD
const int savePin   = 6;  // podgląd bieżącej masy
const int zeroPin   = 4;  // zerowanie wagi
const int thermoPin = 5;  // pomiar termistora

// ---------- Debounce ----------
const unsigned long debounceDelay = 50;
unsigned long lastDebounceTime1 = 0;
unsigned long lastDebounceTime2 = 0;
unsigned long lastDebounceTime3 = 0;
unsigned long lastDebounceTime4 = 0;

// ---------- Stany przycisków ----------
bool dispState       = false, dispStateLast       = HIGH;
bool saveState       = false, saveStateLast       = HIGH;
bool zeroState       = false, zeroStateLast       = HIGH;
bool thermoState     = false, thermoStateLast     = HIGH;

// ---------- LCD ----------
LiquidCrystal_I2C lcd(0x27, 16, 2);
bool backlightFlag = true;

// ---------- Tensometr ----------
HX711 scale;
float last_mass = 0.0;
const float CHANGE_THRESHOLD = 0.1;  // kg

void setup() {
  // Inicjalizacja I²C i LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();

  // Konfiguracja pinów przycisków ze wbudowanym pull-upem
  pinMode(dispPin,   INPUT_PULLUP);
  pinMode(savePin,   INPUT_PULLUP);
  pinMode(zeroPin,   INPUT_PULLUP);
  pinMode(thermoPin, INPUT_PULLUP);

  // Serial i HX711
  Serial.begin(9600);
  while (!Serial);

  scale.begin(dt, sck);
  Serial.println("Kalibracja HX711...");
  scale.set_scale(22500.0); // ustaw swoją kalibrację
  scale.tare();             // zerowanie
  Serial.println("Gotowy do pomiaru!");
}

void loop() {
  // ---------- POMIAR MASY ----------
  float mass = scale.get_units(10);
  float rounded_mass = round(mass * 1000.0) / 1000.0;
  if (rounded_mass < 0.0) rounded_mass = 0.0;

  if (abs(rounded_mass - last_mass) >= CHANGE_THRESHOLD) {
    last_mass = rounded_mass;
    // Wyjście na Serial
    Serial.print("Masa: ");
    Serial.print(rounded_mass, 3);
    Serial.println(" kg");
    // Jeżeli LCD włączone, pokaż masę
    if (backlightFlag) {
      lcd.clear();
      lcd.print("Masa: ");
      lcd.print(rounded_mass, 3);
      lcd.print(" kg");
    }
  }

  // ---------- PRZYCISK DISP (toggle backlight) ----------
  int dispRead = digitalRead(dispPin);
  if (dispRead != dispStateLast) lastDebounceTime1 = millis();
  if (millis() - lastDebounceTime1 > debounceDelay) {
    if (dispRead == LOW && !dispState) {
      // przycisk wciśnięty
      backlightFlag = !backlightFlag;
      if (backlightFlag) lcd.backlight();
      else              lcd.noBacklight();
      lcd.clear();
      dispState = true;
    } else if (dispRead == HIGH && dispState) {
      // przycisk puszczony
      dispState = false;
    }
  }
  dispStateLast = dispRead;

  // ---------- PRZYCISK SAVE (podgląd masy) ----------
  int saveRead = digitalRead(savePin);
  if (saveRead != saveStateLast) lastDebounceTime2 = millis();
  if (millis() - lastDebounceTime2 > debounceDelay) {
   
      lcd.clear();
      lcd.print("Masa: ");
      lcd.print(rounded_mass, 3);
      Serial.println(rounded_mass);
      lcd.print(" kg");
      saveState = true;
    

    
  }
  saveStateLast = saveRead;

  // ---------- PRZYCISK ZERO (zerowanie) ----------
  int zeroRead = digitalRead(zeroPin);
  if (zeroRead != zeroStateLast) lastDebounceTime3 = millis();
  if (millis() - lastDebounceTime3 > debounceDelay) {
    if (zeroRead == LOW && !zeroState) {
      scale.tare();
      lcd.clear();
      lcd.print("Zerowanie...");
      zeroState = true;
    } else if (zeroRead == HIGH && zeroState) {
      zeroState = false;
    }
  }
  zeroStateLast = zeroRead;

  // ---------- PRZYCISK THERMO (pomiar A0–A1) ----------
  int thermoRead = digitalRead(thermoPin);
  if (thermoRead != thermoStateLast) lastDebounceTime4 = millis();
  if (millis() - lastDebounceTime4 > debounceDelay) {
    if (thermoRead == LOW && !thermoState) {
      int tempRaw = analogRead(A0) - analogRead(A1);
      lcd.clear();
      lcd.print("Temp A0-A1:");
      lcd.setCursor(0,1);
      lcd.print(tempRaw);
      thermoState = true;
    } else if (thermoRead == HIGH && thermoState) {
      thermoState = false;
    }
  }
  thermoStateLast = thermoRead;

  delay(50);
}
 