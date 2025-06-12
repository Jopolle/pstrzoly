
# Raspberry Pi Python Script (receiver_and_sms.py)
# ----------------------------------------------
# Odbiera dane z Arduino, loguje i na żądanie SMS zwraca ostatni ping.
# Używa /dev/serial0 (alias do głównego UART na Pi3) zamiast /dev/ttyS0.
# Wymagania: pip3 install pyserial

#!/usr/bin/env python3
import serial
import time
from datetime import datetime
import re

# ==============================================
# Ustawienia UART dla Waveshare SIM868 HAT na Raspberry Pi 3B+
# 1) Wyłącz konsolę na UART (raspi-config -> Interfacing > Serial
#    - Login shell: Disabled
#    - Serial port hardware: Enabled
# 2) Zrestartuj Pi
# 3) Sprawdź urządzenie: ls -l /dev/serial0 oraz dmesg | grep ttyAMA0
#    /dev/serial0 powinien wskazywać na ttyAMA0
# ==============================================

# Porty i prędkości
ARDUINO_SERIAL_PORT = '/dev/ttyACM0'
ARDUINO_BAUDRATE = 9600
GSM_SERIAL_PORT     = '/dev/serial0'  # główny UART (/dev/ttyAMA0)
GSM_BAUDRATE        = 115200

LOG_FILENAME = 'arduino_log.txt'

# Inicjalizacja GSM: text mode SMS, charset, CMTI dla +CMTI

def init_gsm(ser):
    cmds = [
        b'AT\r',
        b'AT+CMGF=1\r',        # tryb tekstowy
        b'AT+CSCS="GSM"\r',  # charset GSM 7bit
        b'AT+CNMI=2,2,0,0,0\r' # powiadomienia +CMTI z indeksem
    ]
    for cmd in cmds:
        ser.write(cmd)
        time.sleep(0.5)
        resp = ser.read(ser.in_waiting or 1)
        print(f"GSM init response: {resp}")

# Wyślij SMS

def send_sms(ser, number, message):
    ser.write(f'AT+CMGS="{number}"\r'.encode())
    time.sleep(0.5)
    ser.write(message.encode() + b'\r')
    ser.write(bytes([26]))  # Ctrl+Z
    time.sleep(3)
    resp = ser.read(ser.in_waiting or 1)
    print(f"SMS send response: {resp}")

# Odczytaj SMS pod indeksem

def read_sms_index(ser, idx):
    ser.write(f'AT+CMGR={idx}\r'.encode())
    time.sleep(0.5)
    lines = []
    while ser.in_waiting:
        lines.append(ser.readline())
    return lines

# Obsługa powiadomień +CMTI

def handle_cmt_notifications(ser, last_ping):
    while ser.in_waiting:
        raw = ser.readline()
        try:
            line = raw.decode().strip()
        except UnicodeDecodeError:
            line = raw.decode('latin-1').strip()
        print(f"GSM raw: {repr(raw)} -> {line}")
        m = re.match(r'\+CMTI: \"\w+\",(\d+)', line)
        if m:
            idx = m.group(1)
            sms_lines = read_sms_index(ser, idx)
            # sms_lines[0] header, sms_lines[1] text
            try:
                header = sms_lines[0].decode().strip()
                body = sms_lines[1].decode().strip().lower()
            except:
                header = sms_lines[0].decode('latin-1').strip()
                body = sms_lines[1].decode('latin-1').strip().lower()
            print(f"SMS header: {header}")
            print(f"SMS body: {body}")
            sender = header.split(',')[1].replace('"','')
            if 'status' in body and last_ping is not None:
                send_sms(ser, sender, f'Last ping: {last_ping}')


def main():
    # Serial do Arduino
    ard = serial.Serial(ARDUINO_SERIAL_PORT, ARDUINO_BAUDRATE, timeout=1)
    time.sleep(2)
    # Serial do GSM HAT
    gsm = serial.Serial(GSM_SERIAL_PORT, GSM_BAUDRATE, timeout=1)
    time.sleep(2)
    init_gsm(gsm)

    last_ping = None
    with open(LOG_FILENAME, 'a') as log_file:
        try:
            while True:
                # Odczyt z Arduino
                raw = ard.readline()
                try:
                    line = raw.decode().strip()
                except:
                    line = raw.decode('latin-1').strip()
                if line.isdigit():
                    last_ping = line
                    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    entry = f"{ts}, {last_ping}\n"
                    print(entry, end='')
                    log_file.write(entry)
                    log_file.flush()
                # Obsługa SMS
                handle_cmt_notifications(gsm, last_ping)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nZakończono.")
        finally:
            ard.close()
            gsm.close()

if __name__ == '__main__':
    main()
