/*
  Arduino_PingSender.ino

  Ten przykładowy sketch co określony interwał (np. co 5 sekund) 
  wysyła przez Serial (USB) "ping" wraz z prostymi danymi 
  (tu: odczyt z A0 i wartość timera).
  
  - Baud rate: 115200
  - Wysyłane dane w formacie CSV: <timestamp_ms>,<analogRead(A0)>
  
  Aby działało:
    1. Podłącz Arduino Uno do Raspberry Pi kablem USB.
    2. Upewnij się, że w Raspberry Pi port szeregowy (/dev/ttyACM0 lub /dev/ttyUSB0) 
       ma odpowiednie uprawnienia (dodanie użytkownika do grupy dialout lub 
       uruchomienie skryptu z sudo).
*/

const unsigned long INTERVAL_MS = 5000; // co 5000 ms = 5 sekund
unsigned long lastSend = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // czekaj, aż Serial zostanie aktywowany (tylko dla niektórych płytek)
  }
  pinMode(A0, INPUT);
}

void loop() {
  unsigned long now = millis();
  if (now - lastSend >= INTERVAL_MS) {
    lastSend = now;

    // Przykładowe dane:
    int analogValue = analogRead(A0);
    unsigned long timestamp = now;

    // Sformatuj linię CSV: "<timestamp_ms>,<analogValue>\n"
    Serial.print(timestamp);
    Serial.print(",");
    Serial.println(analogValue);
  }
  // Można tu ewentualnie dodać dodatkowe zadania w tle
}
