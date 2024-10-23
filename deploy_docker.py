import os
import socket
import subprocess
import sys

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def deploy():
    # Obtener IP local
    HOST_IP = get_local_ip()
    
    # Solicitar IP del servidor central si es necesario
    if len(sys.argv) > 1:
        CENTRAL_IP = sys.argv[1]
    else:
        CENTRAL_IP = input("Ingrese la IP del servidor central (Enter si este es el servidor central): ").strip()
        if not CENTRAL_IP:
            CENTRAL_IP = HOST_IP

    # Configurar variables de entorno
    os.environ['HOST_IP'] = HOST_IP
    os.environ['CENTRAL_IP'] = CENTRAL_IP
    
    # Determinar qué compose file usar
    if HOST_IP == CENTRAL_IP:
        compose_file = 'docker-compose.central.yml'
        print("Desplegando como servidor central...")
    elif len(sys.argv) > 2 and sys.argv[2] == 'taxi':
        compose_file = 'docker-compose.taxi.yml'
        print("Desplegando como nodo de taxis...")
    else:
        compose_file = 'docker-compose.client.yml'
        print("Desplegando como nodo de clientes...")

    # Detener contenedores existentes
    subprocess.run(['docker-compose', '-f', compose_file, 'down'])

    # Iniciar nuevos contenedores
    subprocess.run(['docker-compose', '-f', compose_file, 'up', '--build', '-d'])

    # Mostrar logs
    subprocess.run(['docker-compose', '-f', compose_file, 'logs', '-f'])

if __name__ == "__main__":
    deploy()