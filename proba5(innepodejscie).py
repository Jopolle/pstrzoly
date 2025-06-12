import serial
import time
import re

# ---- KONFIGURACJA ----
SERIAL_PORT = '/dev/ttyAMA0'  # lub '/dev/serial0', '/dev/ttyS0' – dostosuj
BAUDRATE = 115200
CHECK_INTERVAL = 30          # co ile sekund sprawdzać nowe SMS
TARGET_NUMBER = '+48665464949'
TRIGGER_TEXT = 'status'
REPLY_TEXT = 'hello'


def send_at(cmd, ser, timeout=2):
    """Wyślij komendę AT i zwróć odpowiedź jako listę linii."""
    ser.write((cmd + '\r').encode())
    time.sleep(timeout)
    lines = []
    while ser.in_waiting:
        line = ser.readline().decode(errors='ignore').strip()
        if line:
            lines.append(line)
    return lines


def init_modem(ser):
    """Ustaw modem w tryb tekstowego SMS."""
    send_at('AT', ser)
    send_at('ATE0', ser)             # wyłącz echo
    send_at('AT+CMGF=1', ser)        # SMS Text Mode
    send_at('AT+CSCS="GSM"', ser)    # charset
    # opcjonalnie: send_at('AT+CNMI=2,1,0,0,0', ser)  # powiadomienia o nowych SMS


def parse_cmgl(lines):
    """
    Parsuje wyjście AT+CMGL="ALL".
    Zwraca listę słowników: {'index': idx, 'status': stat, 'sender': num, 'date': date, 'text': txt}
    """
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
            # treść SMS to następna linia (lub kilka – tu zakładamy jednowierszową)
            txt = lines[i+1] if i+1 < len(lines) else ''
            messages.append({
                'index': idx,
                'status': status,
                'sender': sender,
                'date': date,
                'text': txt.strip()
            })
            i += 2
        else:
            i += 1
    return messages


def delete_message(idx, ser):
    """Usuń SMS o podanym indexie."""
    send_at(f'AT+CMGD={idx}', ser)


def send_sms(number, text, ser):
    """Wyślij SMS na numer number z treścią text."""
    send_at('AT+CMGS="{}"'.format(number), ser)
    ser.write(text.encode() + b'\x1A')  # Ctrl+Z kończy wiadomość
    # czekaj na potwierdzenie
    time.sleep(5)
    # opcjonalnie: odczytaj odpowiedź
    resp = []
    while ser.in_waiting:
        resp.append(ser.readline().decode(errors='ignore').strip())
    return resp


def main():
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    time.sleep(1)
    init_modem(ser)
    print("Modem zainicjalizowany, start pętli sprawdzania SMS...")

    try:
        while True:
            # 1) pobierz wszystkie SMS
            lines = send_at('AT+CMGL="ALL"', ser, timeout=3)
            msgs = parse_cmgl(lines)

            # 2) przetwarzaj
            for m in msgs:
                print(f"> SMS#{m['index']} od {m['sender']}: {m['text']}")
                if (m['sender'] == TARGET_NUMBER and
                        m['text'].lower() == TRIGGER_TEXT.lower()):
                    print("-> Znaleziono komendę status – wysyłam odpowiedź")
                    send_sms(TARGET_NUMBER, REPLY_TEXT, ser)

                # 3) usuń każdy odczytany SMS, aby zrobić miejsce
                delete_message(m['index'], ser)
                print(f"-> Usunięto SMS#{m['index']}")

            # 4) pauza przed następnym sprawdzeniem
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("Przerwano przez użytkownika.")
    finally:
        ser.close()


if __name__ == '__main__':
    main()
