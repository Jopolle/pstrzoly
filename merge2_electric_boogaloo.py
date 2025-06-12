import os
import re
import datetime
import time
import threading
import serial

# ---- KONFIGURACJA ----
ARDUINO_PORT = '/dev/ttyACM0'    # port Arduino
ARDUINO_BAUDRATE = 115200
MODEM_PORT = '/dev/ttyAMA0'      # port modemu GSM (serial0)
MODEM_BAUDRATE = 115200
CHECK_INTERVAL = 30              # sekundy między sprawdzeniami SMS
TARGET_NUMBER = '+48665464949'   # numer, z którego przychodzi 'status'
TRIGGER_TEXT = 'status'

# Globalne zmienne
last_count = None
run_event = threading.Event()
run_event.set()


def get_log_filename(base_dir='pasieka_logi'):
    """Generuje nową nazwę pliku CSV z numerem sekwencji i datą."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, base_dir)
    os.makedirs(log_dir, exist_ok=True)
    pattern = re.compile(r'^(\d{3})_\d{8}\.csv$')
    seqs = [int(m.group(1)) for fname in os.listdir(log_dir)
            if (m := pattern.match(fname))]
    next_seq = max(seqs) + 1 if seqs else 1
    date_str = datetime.date.today().strftime('%Y%m%d')
    filename = f"{next_seq:03d}_{date_str}.csv"
    return os.path.join(log_dir, filename)


def send_at(cmd, ser, timeout=2):
    """Wyślij komendę AT i zwróć odpowiedź jako listę linii."""
    ser.write((cmd + '\r').encode())
    time.sleep(timeout)
    out = []
    while ser.in_waiting:
        line = ser.readline().decode(errors='ignore').strip()
        if line:
            out.append(line)
    return out


def init_modem(ser):
    """Inicjalizacja modemu GSM w trybie tekstowym SMS."""
    send_at('AT', ser)
    send_at('ATE0', ser)
    send_at('AT+CMGF=1', ser)
    send_at('AT+CSCS="GSM"', ser)


def parse_cmgl(lines):
    """Parsuje odpowiedź AT+CMGL i zwraca listę wiadomości."""
    msgs = []
    header = re.compile(r'^\+CMGL: (\d+),"[^"]+","([^"]+)",.*"([^"]+)"$')
    i = 0
    while i < len(lines):
        if m := header.match(lines[i]):
            idx = int(m.group(1))
            sender = m.group(1+0) if False else m.group(1)  # numer w grupie 1
            # tekst w kolejnej linii
            txt = lines[i+1] if i+1 < len(lines) else ''
            msgs.append({'index': idx, 'sender': sender, 'text': txt.strip()})
            i += 2
        else:
            i += 1
    return msgs


def delete_message(idx, ser):
    """Usuwa SMS o danym idx."""
    send_at(f'AT+CMGD={idx}', ser)


def send_sms(number, text, ser):
    """Wysyła SMS pod numer number z treścią text."""
    send_at(f'AT+CMGS="{number}"', ser)
    ser.write(text.encode() + b'\x1A')
    time.sleep(5)
    # możemy odczytać potwierdzenie, ale nie jest konieczne


def serial_logger(log_path):
    """Czyta dane z Arduino, liczy pingi i zapisuje do pliku CSV."""
    global last_count
    ping_count = 0
    try:
        ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUDRATE, timeout=1)
        with open(log_path, 'a', buffering=1) as f:
            while run_event.is_set():
                raw = ser.readline().decode('utf-8', errors='replace').strip()
                if raw:
                    ping_count += 1
                    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    line = f"{ts};{ping_count}"
                    last_count = str(ping_count)
                    f.write(line + '\n')
                    print(f"Zapisano: {line}")
    except Exception as e:
        print(f"Błąd serial_logger: {e}")
    finally:
        ser.close()


def sms_listener():
    """Nasłuchuje SMS-ów i odpowiada ostatnim stanem pingów."""
    try:
        ser = serial.Serial(MODEM_PORT, MODEM_BAUDRATE, timeout=1)
        time.sleep(1)
        init_modem(ser)
        print("Modem SMS zainicjalizowany.")
        while run_event.is_set():
            resp = send_at('AT+CMGL="ALL"', ser, timeout=3)
            msgs = parse_cmgl(resp)
            for m in msgs:
                print(f"> SMS#{m['index']} od {m['sender']}: {m['text']}")
                if m['sender'] == TARGET_NUMBER and m['text'].lower() == TRIGGER_TEXT:
                    reply = last_count or 'Brak danych'
                    print(f"-> Odpowiadam: {reply}")
                    send_sms(TARGET_NUMBER, reply, ser)
                delete_message(m['index'], ser)
            time.sleep(CHECK_INTERVAL)
    except Exception as e:
        print(f"Błąd sms_listener: {e}")
    finally:
        ser.close()


if __name__ == '__main__':
    log_file = get_log_filename()
    print(f"Logi zapisywane do: {log_file}")

    t_log = threading.Thread(target=serial_logger, args=(log_file,), daemon=True)
    t_sms = threading.Thread(target=sms_listener, daemon=True)
    t_log.start()
    t_sms.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Zakończenie programu...")
        run_event.clear()
        t_log.join()
        t_sms.join()
        print("Program zakończony.")
