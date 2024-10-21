import socket
from Taxi import taxi

class DigitalEngine:
    def __init__(self, ec_central_ip, ec_central_port, broker_ip, broker_port, ec_s_ip, ec_s_port, taxi_id):
        self.ec_central_ip = ec_central_ip
        self.ec_central_port = ec_central_port
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.ec_s_ip = ec_s_ip
        self.ec_s_port = ec_s_port
        self.taxi = taxi(taxi_id)
        self.authenticated = False

    def authenticate_with_ec_central(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.ec_central_ip, self.ec_central_port))
                s.sendall(f"AUTH TAXI_ID:{self.taxi.taxi_id}".encode())
                data = s.recv(1024).decode()
                if data == "AUTH_SUCCESS":
                    self.authenticated = True
                    print(f"Taxi {self.taxi.taxi_id} autenticado correctamente.")
                else:
                    print(f"Error de autenticación para el taxi {self.taxi.taxi_id}.")
        except Exception as e:
            print(f"Error al conectarse a EC_Central: {e}")

    def wait_for_service_request(self):
        if not self.authenticated:
            print("El taxi no está autenticado. No puede recibir solicitudes de servicio.")
            return

        print(f"Taxi {self.taxi.taxi_id} esperando solicitudes de servicio...")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.broker_ip, self.broker_port))
                while True:
                    data = s.recv(1024).decode()
                    if data.startswith("SERVICE_REQUEST"):
                        print(f"Solicitud de servicio recibida: {data}")
        except Exception as e:
            print(f"Error al conectarse al broker: {e}")

# Aquí podrías inicializar el DigitalEngine, por ejemplo:
if __name__ == "__main__":
    # Datos de ejemplo (deben recibirse por la línea de comandos normalmente)
    ec_central_ip = "127.0.0.1"
    ec_central_port = 8000
    broker_ip = "127.0.0.1"
    broker_port = 9000
    ec_s_ip = "127.0.0.1"
    ec_s_port = 10000
    taxi_id = 1

    engine = DigitalEngine(ec_central_ip, ec_central_port, broker_ip, broker_port, ec_s_ip, ec_s_port, taxi_id)
    engine.authenticate_with_ec_central()
    engine.wait_for_service_request()