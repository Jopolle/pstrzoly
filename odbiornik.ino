#include <RH_ASK.h>
#include <SPI.h> // wymagane przez RadioHead

#define RX_PIN 11

RH_ASK driver(2000, RX_PIN); // bitrate = 2000, RX = pin 11

void setup() {
  Serial.begin(9600);
  if (!driver.init()) {
    Serial.println("Błąd inicjalizacji ODBIORNIKA");
  } else {
    Serial.println("Odbiornik gotowy");
  }
}

void loop() {
  uint8_t buf[RH_ASK_MAX_MESSAGE_LEN];
  uint8_t buflen = sizeof(buf);

  if (driver.recv(buf, &buflen)) {
    buf[buflen] = '\0'; // zakończ string
    Serial.print("Odebrano: ");
    Serial.println((char*)buf);
  }
}
