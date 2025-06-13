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
const int DISP_PIN   = 6;  // toggle backlight
const int CHSC_PIN   = 5;  // jednorazowy podgląd masy
const int ZERO_PIN   = 7;  // tare
const int RX_PIN = 4;  // trigger odczytu DHT11

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



int elapsed_time = 0;
const int LOOP_COUNT = 2;

bool weight_temp_flag = true;




enum {
  NONE = 0,
  TOGGLE_BACKLIGHT,
  TOGGLE_SCREEN,
  TRIGGER_RX,
  SCALE_TARE
};
int STATE = TOGGLE_SCREEN;


void setup() {
  Serial.begin(9600);


  if (!rf_driver.init()) {
    Serial.println("RF init failed");
  }
  scale.begin(10, 3);               // DT, SCK
  delay(3000);                     // stabilizacja

  scale.set_scale(23600.0);       // <- Tego nie zmieniajcie to jest git
  scale.tare();                    // zerowanie

  lcd.init();
  lcd.backlight();
  lcd.clear();

  pinMode(DISP_PIN,   INPUT_PULLUP);
  pinMode(CHSC_PIN,   INPUT_PULLUP);
  pinMode(ZERO_PIN,   INPUT_PULLUP);
  pinMode(RX_PIN, INPUT_PULLUP);


  dht1.begin();
  dht2.begin();



  Serial.println("Gotowy do pomiaru!");

 

}

void loop() {
     // 1) Pomiar masy
    float mass = scale.get_units(10);                    // uśrednienie
    float rounded_mass = round(mass * 1000.0) / 1000.0;  // zaokrąglenie

    if (rounded_mass < 0.0) {
        rounded_mass = 0.0;
    }
    //Serial.print("Masa: ");
    //Serial.print(rounded_mass, 3);
    //Serial.println(" kg");

    last_mass = rounded_mass;

    //Pomiar temperatury
    delay(2000);
    float h1 = dht1.readHumidity();
    float t1 = dht1.readTemperature();
    float h2 = dht2.readHumidity();
    float t2 = dht2.readTemperature();




  unsigned long now = millis();
  STATE = NONE;
  if (now - lastDisp > DEBOUNCE) {
    if (digitalRead(DISP_PIN) == LOW) {
      STATE = TOGGLE_BACKLIGHT;
      lastDisp = now;
    }
  }
  // przycisk CHSC_PIN
  if (now - lastSave > DEBOUNCE) {
    if (digitalRead(CHSC_PIN) == LOW) {
      STATE = TOGGLE_SCREEN;
      lastSave = now;
    }
  }
  // przycisk ZERO_PIN
  if (now - lastZero > DEBOUNCE) {
    if (digitalRead(ZERO_PIN) == LOW) {
      STATE = TRIGGER_RX;
      lastZero = now;
    }
  }
  // przycisk RX_PIN
  if (now - lastThermo > DEBOUNCE) {
    if (digitalRead(RX_PIN) == LOW) {
      STATE = SCALE_TARE;
      lastThermo = now;
    }
  }





  
    switch (STATE) {
    case TOGGLE_BACKLIGHT:
      Serial.println("Toggle backlight");
      // tu daj kod do przełączania podświetlenia
      backlightOn = !backlightOn;
      backlightOn ? lcd.backlight() : lcd.noBacklight();
      lcd.clear();
      STATE = TOGGLE_SCREEN;
      break;
    case TOGGLE_SCREEN:
      Serial.println("Toggle Screen");
      // tu daj kod do jednorazowego podglądu masy
        if(weight_temp_flag){
            lcd.clear();
            lcd.print("Masa: ");
            lcd.print(mass,3);
            lcd.print(" kg");
        }
        else{
            lcd.clear();
            if (isnan(t1)||isnan(h1)) lcd.print("Blad DHT1");
            else {
                lcd.print("T1:"); lcd.print(t1,1); lcd.print("C H1:"); lcd.print(h1,0); lcd.print("%");
            }
            lcd.setCursor(0,1);
            if (isnan(t2)||isnan(h2)) lcd.print("Blad DHT2");
            else {
                lcd.print("T2:"); lcd.print(t2,1); lcd.print("C H2:"); lcd.print(h2,0); lcd.print("%");
            }
        }
        weight_temp_flag = !weight_temp_flag;
      break;
    case TRIGGER_RX:
        Serial.println("Trigger RX");
        // 
        elapsed_time = LOOP_COUNT;
        lcd.clear();
        lcd.print("Zerowanie...");
        delay(3000);
        lcd.clear();
        STATE = TOGGLE_SCREEN;
        break;
    case SCALE_TARE:
        Serial.println("Tare");
        // tu daj kod wyzwalający odczyt DHT11
        scale.tare();
        lcd.clear();
        lcd.print("Zerowanie...");
        delay(3000);
        lcd.clear();
        STATE = TOGGLE_SCREEN;
        break;
    default:
      // nic do zrobienia
      break;
  }


elapsed_time++;

  if(elapsed_time > LOOP_COUNT)
  {
    // upewniamy się, że mamy aktualne wartości z DHT (może od poprzedniego naciśnięcia)
    h1 = isnan(h1) ? dht1.readHumidity() : h1;
    t1 = isnan(t1) ? dht1.readTemperature() : t1;
    h2 = isnan(h2) ? dht2.readHumidity() : h2;
    t2 = isnan(t2) ? dht2.readTemperature() : t2;



    String msg = "" + String(mass, 3) + "kg " + String(t1, 1)
           + "C " + String(h1, 1) + "% " + String(t2, 1)
           + "C " + String(h2, 1) + "%";

  rf_driver.send((uint8_t*)msg.c_str(), msg.length());
  rf_driver.waitPacketSent();
    // debug
    Serial.print("RF-> "); Serial.print(msg); Serial.print("   "); Serial.println(h1);
    elapsed_time = 0;
  }

  // 3) SAVE: pokaz jednorazowo masę
  
  /*
  bool s = digitalRead(CHSC_PIN);
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
  bool t = digitalRead(RX_PIN);
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



    String msg = "Masa ula:  " + String(mass, 3) + "kg T1:" + String(t1, 1)
           + "C H1:" + String(h1, 1) + "% T2:" + String(t2, 1)
           + "C H2:" + String(h2, 1) + "%";

  rf_driver.send((uint8_t*)msg.c_str(), msg.length());
  rf_driver.waitPacketSent();
    // debug
    //Serial.print("RF-> "); Serial.print(msg); Serial.print("   "); Serial.println(h1); 
  }
  */
  delay(2000);
}



