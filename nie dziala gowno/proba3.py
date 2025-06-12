import serial
import time
import re

# Ustawienia portu szeregowego
ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=3)
time.sleep(1)

def send_command(command, delay=1):
    ser.write((command + '\r').encode())
    time.sleep(delay)
    response = ser.readlines()
    return [line.decode().strip() for line in response]

def init_modem():
    send_command('AT')               # Test komunikacji
    send_command('AT+CMGF=1')        # Tryb tekstowy
    send_command('AT+CNMI=2,2,0,0,0') # Odbiór SMS natychmiast, do terminala

def wait_for_sms():
    print("Oczekiwanie na SMS...")
    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if line.startswith('+CMT:'):
            header = line
            body = ser.readline().decode(errors='ignore').strip()
            # Wyodrębnij numer telefonu
            match = re.search(r'"\+?(\d+)"', header)
            number = match.group(1) if match else "Nieznany"
            print(f"\n📩 SMS od: +{number}")
            print(f"📨 Treść: {body}\n")

try:
    init_modem()
    wait_for_sms()
except KeyboardInterrupt:
    print("Zamknięcie programu.")
finally:
    ser.close()
