import socket
import subprocess
import sys
import json

def check_port(host, port):
    """Verifica si un puerto está abierto"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

def ping_host(host):
    """Realiza ping a un host"""
    param = '-n' if sys.platform.lower()=='windows' else '-c'
    command = ['ping', param, '1', host]
    return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def get_local_ip():
    """Obtiene la IP local de la máquina"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def check_network_config():
    """Comprueba la configuración de red"""
    local_ip = get_local_ip()
    print(f"IP Local: {local_ip}")

    try:
        with open('network_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: No se encuentra network_config.json")
        return False

    all_ok = True
    
    print("\nComprobando conectividad...")
    for node in config['nodes']:
        ip = node['ip']
        if ip != local_ip:
            print(f"\nVerificando conexión con {node['name']} ({ip}):")
            if ping_host(ip):
                print(f"✓ Ping a {ip} exitoso")
                for service in node['services']:
                    port = service['port']
                    if check_port(ip, port):
                        print(f"✓ Puerto {port} ({service['name']}) accesible")
                    else:
                        print(f"✗ Puerto {port} ({service['name']}) no accesible")
                        all_ok = False
            else:
                print(f"✗ No se puede hacer ping a {ip}")
                all_ok = False

    return all_ok

if __name__ == "__main__":
    if check_network_config():
        print("\n✓ Configuración de red correcta")
        sys.exit(0)
    else:
        print("\n✗ Hay problemas con la configuración de red")
        sys.exit(1)