import os
import re
import datetime
import time
import threading
import serial


def get_log_filename(base_dir='pasieka_logi'):
    # Upewnij się, że katalog istnieje
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, base_dir)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    # Znajdź istniejące pliki z wzorcem "NNN_YYYYMMDD.csv"
    pattern = re.compile(r'^(\d{3})_(\d{8})\.csv$')
    seqs = []
    for fname in os.listdir(log_dir):
        m = pattern.match(fname)
        if m:
            seqs.append(int(m.group(1)))
    next_seq = max(seqs) + 1 if seqs else 1
    date_str = datetime.date.today().strftime('%Y%m%d')
    filename = f"{next_seq:03d}_{date_str}.csv"
    return os.path.join(log_dir, filename)

# Konfiguracja portów i parametrów
ARDUINO_PORT = '/dev/ttyACM0'
ARDUINO_BAUDRATE = 115200
MODEM_PORT = '/dev/serial0'
MODEM_BAUDRATE = 115200
CHECK_INTERVAL = 30  # sekundy między sprawdzeniami SMS
TARGET_NUMBER = '+48665464949'
TRIGGER_TEXT = 'status'

# Zmienne współdzielone\last_line = None
run_event = threading.Event()
run_event.set()

# Funkcje do obsługi modemu GSM

def send_at(cmd, ser, timeout=2):
    ser.write((cmd + '\r').encode())
    time.sleep(timeout)
    lines = []
    while ser.in_waiting:
        line = ser.readline().decode(errors='ignore').strip()
        if line:
            lines.append(line)
    return lines


def init_modem(ser):
    send_at('AT', ser)
    send_at('ATE0', ser)             # wyłącz echo
    send_at('AT+CMGF=1', ser)        # tryb tekstowy SMS
    send_at('AT+CSCS="GSM"', ser)  # charset


def parse_cmgl(lines):
    messages = []
    header_re = re.compile(r'^\+CMGL: (\d+),"([^"]+)","([^"]+)",.*"([^"]+)"$')
    i = 0
    while i < len(lines):
        m = header_re.match(lines[i])
        if m:
            idx = int(m.group(1))
            status = m.group(2)
            sender = m.group(3)
            date = m.group(4)
            txt = lines[i+1] if i+1 < len(lines) else ''
            messages.append({'index': idx, 'status': status, 'sender': sender, 'date': date, 'text': txt.strip()})
            i += 2
        else:
            i += 1
    return messages


def delete_message(idx, ser):
    send_at(f'AT+CMGD={idx}', ser)


def send_sms(number, text, ser):
    send_at(f'AT+CMGS="{number}"', ser)
    ser.write(text.encode() + b'\x1A')  # Ctrl+Z
    time.sleep(5)
    resp = []
    while ser.in_waiting:
        resp.append(ser.readline().decode(errors='ignore').strip())
    return resp

# Wątek logujący dane z Arduino do CSV

def serial_logger(log_path):
    global last_line
    try:
        ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUDRATE, timeout=1)
        with open(log_path, 'a', buffering=1) as logfile:
            while run_event.is_set():
                try:
                    raw = ser.readline().decode('utf-8', errors='replace').strip()
                except serial.SerialException:
                    break
                if raw:
                    # raw zawiera "<timestamp_ms>,<analogValue>"
                    last_line = raw
                    logfile.write(raw + '\n')
                    print(f"Zapisano: {raw}")
    except Exception as e:
        print(f"Błąd w serial_logger: {e}")
    finally:
        ser.close()
        print("serial_logger zakończony.")

# Wątek nasłuchujący SMS i odpowiadający

def sms_listener():
    try:
        ser = serial.Serial(MODEM_PORT, MODEM_BAUDRATE, timeout=1)
        time.sleep(1)
        init_modem(ser)
        print("Modem SMS zainicjalizowany.")
        while run_event.is_set():
            lines = send_at('AT+CMGL="ALL"', ser, timeout=3)
            msgs = parse_cmgl(lines)
            for m in msgs:
                print(f"> SMS#{m['index']} od {m['sender']}: {m['text']}")
                if m['sender'] == TARGET_NUMBER and m['text'].lower() == TRIGGER_TEXT.lower():
                    reply = last_line or 'Brak danych'
                    send_sms(TARGET_NUMBER, reply, ser)
                    print(f"Wysłano odpowiedź: {reply}")
                delete_message(m['index'], ser)
            time.sleep(CHECK_INTERVAL)
    except Exception as e:
        print(f"Błąd w sms_listener: {e}")
    finally:
        ser.close()
        print("sms_listener zakończony.")

if __name__ == '__main__':
    # Przygotowanie pliku logów
    log_file = get_log_filename()
    print(f"Logi będą zapisywane w: {log_file}")

    # Uruchom wątki
    t1 = threading.Thread(target=serial_logger, args=(log_file,), daemon=True)
    t2 = threading.Thread(target=sms_listener, daemon=True)
    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Przerwano działanie programu.")
        run_event.clear()
        t1.join()
        t2.join()
        print("Zamknięto wszystkie wątkami. Program zakończony.")
