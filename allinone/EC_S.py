import socket
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = 'localhost'
PORT = 8010

def send_sensor_data(data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            logger.info(f"Connected to ECDE at {HOST}:{PORT}")
            
            msg = data.encode('utf-8')
            logger.info(f"Sending: {data}")
            s.send(msg)
            
            response = s.recv(4096)
            logger.info(f"Received response: {response.decode('utf-8')}")
    except Exception as e:
        logger.error(f"Error in sensor communication: {str(e)}")

if __name__ == "__main__":
    try:
        while True:
            sensor_input = input("Enter sensor data (s: red light, p: pedestrian, x: flat tire, q: quit): ")
            if sensor_input.lower() == 'q':
                break
            if sensor_input in ['s', 'p', 'x']:
                send_sensor_data(sensor_input)
            else:
                logger.warning("Invalid input. Please use 's', 'p', or 'x'.")
    except KeyboardInterrupt:
        logger.info("Sensor simulation terminated.")