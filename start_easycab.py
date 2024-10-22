import subprocess
import time
import os

def start_service(command, name):
    print(f"Starting {name}...")
    try:
        process = subprocess.Popen(command, shell=True)
        time.sleep(2)  # Esperar a que el servicio inicie
        return process
    except Exception as e:
        print(f"Error starting {name}: {e}")
        return None

def main():
    # Asegurarse de que Kafka está corriendo
    print("Checking if Kafka is running...")
    try:
        subprocess.run("docker-compose ps", shell=True, check=True)
    except subprocess.CalledProcessError:
        print("Starting Kafka...")
        subprocess.run("docker-compose up -d", shell=True)
        time.sleep(10)  # Esperar a que Kafka inicie

    # Iniciar servicios
    services = [
        ("python EC_Central.py", "Central Service"),
        ("TAXI_ID=1 python EC_DE.py", "Digital Engine 1"),
        ("TAXI_ID=1 python EC_S.py", "Sensors 1"),
        ("TAXI_ID=2 python EC_DE.py", "Digital Engine 2"),
        ("TAXI_ID=2 python EC_S.py", "Sensors 2"),
        ("CUSTOMER_ID=1 python EC_Customer.py", "Customer 1"),
        ("python EC_gui.py", "GUI")
    ]

    processes = []
    for command, name in services:
        process = start_service(command, name)
        if process:
            processes.append((process, name))

    print("\nAll services started. Press Ctrl+C to stop all services.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all services...")
        for process, name in processes:
            print(f"Stopping {name}...")
            process.terminate()
            process.wait()

if __name__ == "__main__":
    main()