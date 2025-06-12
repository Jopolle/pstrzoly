#!/usr/bin/env python3
import serial
import time
import re

def send_cmd(ser, cmd, wait=0.5):
    ser.write((cmd + '\r').encode())
    time.sleep(wait)
    return ser.read_all().decode(errors='ignore')

def main():
    # 1. Otwórz port
    ser = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)
    ser.flushInput()

    # 2. Przełącz w tryb tekstowy SMS
    print(send_cmd(ser, 'AT+CMGF=1'))                      # OK

    # 3. Wskaż magazyn SIM jako główny do odczytu i zapisu
    print(send_cmd(ser, 'AT+CPMS="SM","SM","SM"'))         # OK

    # 4. Przekazuj całą treść przychodzących SMS-ów jako URC +CMT
    print(send_cmd(ser, 'AT+CNMI=2,2,0,0,0'))               # OK

    print("Oczekiwanie na nowe SMS-y… (Ctrl+C aby zakończyć)")

    # wzorzec na URC +CMT: "+numer","data"
    pattern = re.compile(r'^\+CMT: *"(?P<num>[^"]+)",\s*"(?P<ts>[^"]+)"')

    try:
        while True:
            raw = ser.readline()
            if not raw:
                time.sleep(0.1)
                continue

            line = raw.decode(errors='ignore').strip()
            # debug możesz odkomentować:
            # print(f"[RAW] {line}")

            m = pattern.match(line)
            if m:
                # następna linia to treść SMS
                body = ser.readline().decode(errors='ignore').strip()
                print(f"\n### Nowy SMS od {m.group('num')} o {m.group('ts')}")
                print("Treść:", body)
                print("\nOczekiwanie na kolejne SMS-y…")
    except KeyboardInterrupt:
        print("\nKończę działanie, zamykam port.")
    finally:
        ser.close()

if __name__ == '__main__':
    main()
