import socket
import sys
import os

def test_connection(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        if result == 0:
            print(f"✅ Conexión exitosa a {host}:{port}")
            return True
        else:
            print(f"❌ No se puede conectar a {host}:{port}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        sock.close()

def main():
    if len(sys.argv) < 3:
        print("Uso: python test_connection.py <host> <port>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    test_connection(host, port)

if __name__ == "__main__":
    main()