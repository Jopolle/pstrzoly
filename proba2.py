import serial
import time

# Configuration
SERIAL_PORT = "/dev/ttyS0"    # UART port connected to SIM868; adjust if using /dev/ttyAMA0 or USB-serial
BAUD_RATE = 115200             # Baud rate for SIM868
DEFAULT_REPLY_NUMBER = "+48123456789"  # Fallback number if you want to send to a fixed one

# Initialize serial connection (opened in main)
ser = None

def send_at_command(cmd: str, timeout: float = 1.0) -> str:
    """
    Send an AT command to the SIM868 and return its entire response.
    """
    ser.write((cmd + '\r').encode())
    time.sleep(timeout)
    resp = ser.read_all().decode(errors='ignore')
    return resp


def send_sms(number: str, message: str) -> str:
    """
    Send an SMS via SIM868 to the given number.
    """
    # Ensure text mode
    send_at_command('AT+CMGF=1')
    # Begin SMS send
    send_at_command(f'AT+CMGS="{number}"')
    # Write message and Ctrl+Z (0x1A) to send
    ser.write(message.encode() + b"\x1A")
    # Wait for send
    time.sleep(3)
    return ser.read_all().decode(errors='ignore')


def check_unread_sms():
    """
    Poll for unread SMS messages. For each found, if it contains 'status', replies 'hello'.
    Deletes processed messages.
    """
    # Set text mode
    send_at_command('AT+CMGF=1')
    # List unread messages
    resp = send_at_command('AT+CMGL="REC UNREAD"', timeout=2)
    lines = resp.splitlines()

    for i, line in enumerate(lines):
        if line.startswith('+CMGL:'):
            # Parse: +CMGL: <index>,"REC UNREAD","<sender>",,,"<date>"
            parts = line.split(',')
            idx = parts[0].split(':')[1].strip()
            sender = parts[2].strip().strip('"')
            # Next line is the message text
            if i + 1 < len(lines):
                text = lines[i+1].strip()
            else:
                text = ''

            # Remove the message from storage
            send_at_command(f'AT+CMGD={idx}')

            # Check for keyword
            if 'status' in text.lower():
                print(f"Keyword 'status' detected from {sender}, sending reply...")
                target = sender if sender else DEFAULT_REPLY_NUMBER
                result = send_sms(target, "hello")
                print("Send result:", result)


def main():
    global ser

    # Open serial port
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(1)

    # Optional: configure new message indications (directly prints)
    # send_at_command('AT+CNMI=2,1,0,0,0')

    # Test connectivity
    ok = send_at_command('AT', timeout=0.5)
    if 'OK' not in ok:
        print("Error: No response from SIM868. Check connections and port.")
        return
    print("SIM868 is responding.")

    try:
        while True:
            check_unread_sms()
            time.sleep(10)  # Poll interval in seconds
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        ser.close()


if __name__ == '__main__':
    main()
