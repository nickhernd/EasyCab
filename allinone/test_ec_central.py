import requests

def test_ec_central():
    url = "http://localhost:8001/status"  # Cambiado de 8000 a 8001
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("EC_Central está funcionando correctamente")
            print("Respuesta:", response.json())
        else:
            print(f"Error al conectar con EC_Central. Código de estado: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con EC_Central: {e}")

if __name__ == "__main__":
    test_ec_central()