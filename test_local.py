import subprocess
import time
import os
import signal
import sys

def run_command(command, name):
    try:
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True
        )
    except Exception as e:
        print(f"Error iniciando {name}: {e}")
        return None

def main():
    processes = []
    
    print("Iniciando prueba local del sistema EasyCab...")
    
    # Iniciar Central
    print("\n1. Iniciando Servidor Central...")
    central = run_command("python central/EC_Central.py", "Central")
    processes.append(("Central", central))
    time.sleep(2)
    
    # Iniciar Taxi
    print("\n2. Iniciando Taxi...")
    taxi = run_command("python taxi/EC_DE.py 1 5000", "Taxi")
    processes.append(("Taxi", taxi))
    time.sleep(2)
    
    # Iniciar Sensor
    print("\n3. Iniciando Sensor...")
    sensor = run_command("python taxi/EC_S.py 5000", "Sensor")
    processes.append(("Sensor", sensor))
    time.sleep(2)
    
    # Iniciar Cliente
    print("\n4. Iniciando Cliente...")
    customer = run_command("python customer/EC_Customer.py cliente1 data/services.txt", "Cliente")
    processes.append(("Cliente", customer))
    
    print("\nTodos los componentes iniciados. Presiona Ctrl+C para detener...")
    
    try:
        while True:
            time.sleep(1)
            # Verificar si algún proceso ha terminado
            for name, process in processes:
                if process.poll() is not None:
                    print(f"\n¡Error! {name} se ha detenido inesperadamente")
                    return
    except KeyboardInterrupt:
        print("\nDeteniendo todos los componentes...")
        for name, process in processes:
            if process.poll() is None:
                print(f"Deteniendo {name}...")
                process.terminate()
                process.wait()

if __name__ == "__main__":
    main()