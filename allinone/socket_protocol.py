import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STX = b'\x02'
ETX = b'\x03'

def create_message(data):
    """
    Crea un mensaje siguiendo el protocolo especificado.
    """
    try:
        json_data = json.dumps(data).encode('utf-8')
        message = STX + json_data + ETX
        lrc = calculate_lrc(message)
        return message + lrc
    except Exception as e:
        logger.error(f"Error al crear el mensaje: {str(e)}")
        raise

def parse_message(message):
    """
    Parsea un mensaje recibido y verifica su integridad.
    """
    try:
        if message[0] != STX[0] or message[-2] != ETX[0]:
            raise ValueError("Formato de mensaje inválido")
        
        json_data = message[1:-2]
        received_lrc = message[-1]
        calculated_lrc = calculate_lrc(message[:-1])
        
        if received_lrc != calculated_lrc:
            raise ValueError("Verificación LRC fallida")
        
        return json.loads(json_data.decode('utf-8'))
    except Exception as e:
        logger.error(f"Error al parsear el mensaje: {str(e)}")
        raise

def calculate_lrc(message):
    """
    Calcula el LRC (Longitudinal Redundancy Check) de un mensaje.
    """
    lrc = 0
    for byte in message:
        lrc ^= byte
    return bytes([lrc])

def send_ack():
    """
    Crea un mensaje de ACK.
    """
    return create_message({"tipo": "ACK"})

def send_nack():
    """
    Crea un mensaje de NACK.
    """
    return create_message({"tipo": "NACK"})