#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
pi_serial_logger.py

Program w Pythonie, który odczytuje dane z portu szeregowego (Arduino przez USB)
i dopisuje je linia po linii do pliku logu.

1. Upewnij się, że masz zainstalowany pakiet 'pyserial':
     sudo apt update
     sudo apt install python3-pip
     pip3 install pyserial

2. Sprawdź, pod jaką ścieżką pojawia się Arduino:
     ls /dev/ttyACM*   lub   ls /dev/ttyUSB*
   Domyślnie najczęściej będzie: /dev/ttyACM0

3. Uruchom skrypt (np.):
     chmod +x pi_serial_logger.py
     ./pi_serial_logger.py /dev/ttyACM0 115200 dane_log.csv

   Argumenty:
     1) ścieżka do portu szeregowego (np. /dev/ttyACM0)
     2) prędkość transmisji (baudrate), np. 115200
     3) ścieżka do pliku, w który będziemy dopisywać log
"""

import sys
import serial
import time

def main():
    if len(sys.argv) != 4:
        print("Użycie: {} <port_szeregowy> <baudrate> <plik_z_logiem>".format(sys.argv[0]))
        sys.exit(1)

    port_name = sys.argv[1]
    baud_rate = int(sys.argv[2])
    log_filename = sys.argv[3]

    try:
        ser = serial.Serial(port=port_name, baudrate=baud_rate, timeout=1)
    except serial.SerialException as e:
        print(f"Błąd otwarcia portu szeregowego: {e}")
        sys.exit(1)

    print(f"Otwarto port {port_name} z baudrate {baud_rate}. Log będzie zapisywany do '{log_filename}'.")

    # Główna pętla odbierająca dane:
    try:
        with open(log_filename, "a", buffering=1) as logfile:  # buffering=1 -> linia po linii
            while True:
                try:
                    line = ser.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        # Domyślnie linie już zawierają newline, więc strip() usuwa \r\n
                        timestamp_pi = time.strftime("%Y-%m-%d %H:%M:%S")
                        # Możemy zapisać: <timestamp_pi>;<dane_z_arduino>
                        zapis = f"{timestamp_pi};{line}\n"
                        logfile.write(zapis)
                        print(f"Zapisano: {zapis.strip()}")
                except serial.SerialException as e:
                    print(f"Błąd odczytu z portu: {e}")
                    break
                except UnicodeDecodeError:
                    # Ignorujemy linie, których nie da się zdekodować
                    continue
    except KeyboardInterrupt:
        print("Przerwano działanie skryptu przez użytkownika (CTRL+C).")
    finally:
        ser.close()
        print("Zamknięto port szeregowy.")

if __name__ == "__main__":
    main()
