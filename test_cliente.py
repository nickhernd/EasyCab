import socket
import json
import sys

def test_connection(host, port, client_type='taxi', client_id=1):
    try:
        # Crear socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Conectando a {host}:{port}...")
        sock.connect((host, port))
        
        # Enviar mensaje de prueba
        message = {
            'type': client_type,
            'id': client_id
        }
        print(f"Enviando mensaje: {message}")
        sock.send(json.dumps(message).encode())
        
        # Recibir respuesta
        response = sock.recv(1024).decode()
        print(f"Respuesta recibida: {response}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        sock.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python test_client.py <host> <port> [taxi|customer] [id]")
        sys.exit(1)
        
    host = sys.argv[1]
    port = int(sys.argv[2])
    client_type = sys.argv[3] if len(sys.argv) > 3 else 'taxi'
    client_id = sys.argv[4] if len(sys.argv) > 4 else 1
    
    test_connection(host, port, client_type, client_id)