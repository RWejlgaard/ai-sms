"""
This script listens for incoming SMS messages on a serial device and responds to them using OpenAI's GPT-3.
"""

import serial
import time
import requests
import threading
from queue import Queue
import logging
import emoji
import openai
import conversations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sms_gateway.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def wait_for_response(ser, expected_response, timeout=5):
    """
    Wait for a response from the serial device
    ser: serial.Serial
    expected_response: bytes
    timeout: int
    return: bytes
    """
    response = b""
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        response += ser.read(ser.in_waiting or 1)
        logger.debug(f"Received data: {response}")
        if expected_response in response:
            return response
    raise Exception(f"Timeout waiting for: {expected_response}")

def send_sms_via_serial(device, message_body, phone_number):
    """
    Send an SMS via a serial device
    device: str
    message_body: str
    phone_number: str
    """
    logger.info(f"Preparing to send SMS to {phone_number} via {device}")
    try:
        ser = serial.Serial(device, baudrate=115200, timeout=1)

        # Wait for the device to respond with an "OK" after each command
        ser.write(b'AT\r')
        wait_for_response(ser, b'OK')

        ser.write(b'AT+CMGF=1\r')  # Set SMS mode to text
        wait_for_response(ser, b'OK')

        ser.write(b'AT+CSCS="GSM"\r')  # Set character set to GSM
        wait_for_response(ser, b'OK')

        # Send the SMS
        ser.write(f'AT+CMGS="{phone_number}"\r'.encode())
        wait_for_response(ser, b'>')  # Wait for the '>' prompt

        ser.write(f'{message_body}\r'.encode())
        ser.write(b'\x1A')  # Ctrl+Z to send the SMS
        wait_for_response(ser, b'OK', timeout=60)  # Wait for confirmation of SMS sent

        logger.info(f"SMS sent to {phone_number}")
        ser.close()
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {e}")

def process_message(device, message_data):
    """
    Process an incoming SMS message
    device: str
    message_data: list(dict)
    """
    from_number, body = message_data
    logger.info(f"Processing message from {from_number}: {body}")

    try:

        # Check for special commands
        if body.lower() == "/help":
            reply = """Welcome to ai-sms!
"/clear" - Clear the conversation history
"/system <message>" - Send a system message
"/help" - Show this help message"""
            send_sms_via_serial(device, reply, from_number)
            return
        elif body.lower() == "/clear":
            conversations.delete_messages(from_number)
            send_sms_via_serial(device, "Conversation history cleared.", from_number)
            return
        elif body.lower().startswith("/system"):
            system_message = body[8:].strip()
            conversations.set_default_messages(from_number, system_message)
            send_sms_via_serial(device, f"System message set to: {system_message}", from_number)
            return

        # Add the message to the conversation history
        messages = conversations.add_message(from_number, body, "user")

        # Get a response from OpenAI
        assistant_response = openai.get_response_from_openai(messages, logger)
        
        # Add the assistant's response to the conversation history
        conversations.add_message(from_number, assistant_response, "system")
        
        logger.info(f"Received response for {from_number}: {assistant_response}")

        # replace emojis with "[emoji]" to avoid encoding issues
        assistant_response = emoji.demojize(assistant_response, delimiters=("[", "]"))

        # sanitize the assistant_response for GSM encoding
        assistant_response = assistant_response.encode('ascii', 'ignore').decode('ascii')

        # if assistant_response is longer than 300 characters, split it into multiple messages
        if len(assistant_response) > 300:
            words = assistant_response.split()
            current_message = ""
            
            for word in words:
                # Check if adding the next word would exceed the limit
                if len(current_message) + len(word) + 1 > 300:
                    send_sms_via_serial(device, current_message.strip(), from_number)
                    current_message = word + " "  # Start a new message with the current word
                else:
                    current_message += word + " "  # Add the word to the current message
            
            # Send any remaining text as the last message
            if current_message.strip():
                send_sms_via_serial(device, current_message.strip(), from_number)
        else:
            # Send reply back to the sender normally
            send_sms_via_serial(device, assistant_response, from_number)
    except requests.RequestException as e:
        logger.error(f"Failed to send request for message from {from_number}: {e}")


def listen_for_sms(device):
    """
    Listen for incoming SMS messages
    device: str
    """
    logger.info("Starting SMS listener...")
    try:
        ser = serial.Serial(device, baudrate=115200, timeout=10)
        time.sleep(1)  # Wait for the serial connection to initialize
        ser.write(b'AT\r')  # Check if device is ready
        wait_for_response(ser, b'OK')

        ser.write(b'AT+CMGF=1\r')  # Set SMS mode to text
        wait_for_response(ser, b'OK')
        
        # AT+CNMI=2,1,0,0,0 makes the device notify us of new messages with a +CMTI: <mem>,<index> response
        ser.write(b'AT+CNMI=2,1,0,0,0\r')
        wait_for_response(ser, b'OK')

        # Create a message queue to handle incoming messages
        message_queue = Queue()

        # Define a function to handle incoming messages
        def message_handler():
            while True:
                message_data = message_queue.get() # Wait for a message to be added to the queue
                if message_data is None:
                    break
                process_message(device, message_data)
                message_queue.task_done() # Mark the message as processed

        # Start a separate thread to handle incoming messages
        threading.Thread(target=message_handler, daemon=True).start()

        while True:
            if ser.in_waiting > 0:
                # Read incoming data from the serial device
                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                logger.debug(f"Received data: {data}")

                # Check for new SMS notifications, +CMTI: <mem>,<index>
                if '+CMTI:' in data:
                    # New SMS notification received, extract message index
                    # index is the location of the message in the memory
                    index = data.split(',')[1].strip()
                    logger.info(f"New message notification at index {index}")

                    # Read the message at the specified index
                    ser.write(f'AT+CMGR={index}\r'.encode())
                    time.sleep(1)  # Wait for the message to be read, wait_for_response can't be used here
                    
                    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    logger.debug(f"Message read response: {response}")

                    try:
                        from_number = response.split(',')[1].strip().replace('"', '') # Extract the sender's phone number
                        body = response.split('\n')[2].strip() # Extract the message body
                        message_queue.put((from_number, body)) # Add the message to the queue
                        logger.info(f"Queued message from {from_number}")
                    except IndexError:
                        logger.error("Failed to parse incoming message.")

            time.sleep(1)  # Add a small delay to avoid high CPU usage

    except Exception as e:
        logger.error(f"Error in SMS listener: {e}")
    finally:
        ser.close()
        logger.info("SMS listener stopped.")

# Start listening for incoming SMS messages
device = '/dev/ttyS0'
listen_for_sms(device)