# EC_Customer/src/main.py
import sys
import json
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from kafka import KafkaProducer, KafkaConsumer

class CustomerApp:
    def __init__(self, kafka_server: str, customer_id: str):
        self.kafka_server = kafka_server
        self.customer_id = customer_id
        self.running = True
        self.services_file = "services.txt"
        self.current_service = None
        self.position = None  # Se asignará cuando se lea del mapa
        
        # Inicializar Kafka
        self.setup_kafka()
        
        # Inicializar GUI
        self.setup_gui()
        
        # Cargar servicios del archivo
        self.load_services()
        
        # Iniciar threads
        self.start_threads()

    def setup_kafka(self):
        """Configurar productores y consumidores de Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=[self.kafka_server],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            
            self.consumer = KafkaConsumer(
                'map_updates',
                bootstrap_servers=[self.kafka_server],
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                group_id=f'customer-{self.customer_id}'
            )
            
            self.log_event("Conexión con Kafka establecida")
        except Exception as e:
            self.log_event(f"Error conectando con Kafka: {e}")
            sys.exit(1)

    def setup_gui(self):
        """Configurar interfaz gráfica"""
        self.root = tk.Tk()
        self.root.title(f"EC_Customer - Cliente {self.customer_id}")
        self.root.geometry("600x400")

        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Estado actual
        ttk.Label(main_frame, text="Estado:").grid(row=0, column=0, sticky=tk.W)
        self.status_label = ttk.Label(main_frame, text="Esperando...")
        self.status_label.grid(row=0, column=1, sticky=tk.W)

        # Posición actual
        ttk.Label(main_frame, text="Posición:").grid(row=1, column=0, sticky=tk.W)
        self.position_label = ttk.Label(main_frame, text="Sin asignar")
        self.position_label.grid(row=1, column=1, sticky=tk.W)

        # Próximo destino
        ttk.Label(main_frame, text="Próximo destino:").grid(row=2, column=0, sticky=tk.W)
        self.destination_label = ttk.Label(main_frame, text="Ninguno")
        self.destination_label.grid(row=2, column=1, sticky=tk.W)

        # Botón de solicitud manual
        self.request_button = ttk.Button(
            main_frame,
            text="Solicitar siguiente servicio",
            command=self.request_next_service
        )
        self.request_button.grid(row=3, column=0, columnspan=2, pady=10)

        # Log de eventos
        ttk.Label(main_frame, text="Log de eventos:").grid(row=4, column=0, columnspan=2, sticky=tk.W)
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=60)
        self.log_text.grid(row=5, column=0, columnspan=2, pady=5)

    def log_event(self, message: str):
        """Agregar mensaje al log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"{timestamp}: {message}\n")
        self.log_text.see(tk.END)

    def load_services(self):
        """Cargar servicios desde el archivo"""
        try:
            with open(self.services_file, 'r') as f:
                self.services = [line.strip() for line in f if line.strip()]
            self.log_event(f"Servicios cargados: {len(self.services)} destinos")
            if self.services:
                self.destination_label.config(text=self.services[0])
        except FileNotFoundError:
            self.log_event(f"Archivo {self.services_file} no encontrado")
            self.services = []
        except Exception as e:
            self.log_event(f"Error cargando servicios: {e}")
            self.services = []

    def start_threads(self):
        """Iniciar threads para comunicación"""
        # Thread para recibir actualizaciones del mapa
        self.map_thread = threading.Thread(target=self.receive_map_updates)
        self.map_thread.daemon = True
        self.map_thread.start()

    def receive_map_updates(self):
        """Recibir actualizaciones del mapa via Kafka"""
        for message in self.consumer:
            try:
                map_data = message.value
                self.update_from_map(map_data)
            except Exception as e:
                self.log_event(f"Error procesando actualización del mapa: {e}")

    def update_from_map(self, map_data: dict):
        """Actualizar estado basado en datos del mapa"""
        # Actualizar posición del cliente en el mapa si está disponible
        if 'customers' in map_data and self.customer_id in map_data['customers']:
            self.position = map_data['customers'][self.customer_id]
            self.position_label.config(text=str(self.position))

    def request_next_service(self):
        """Solicitar siguiente servicio"""
        if not self.services:
            self.log_event("No hay más servicios pendientes")
            self.status_label.config(text="Sin servicios pendientes")
            return

        destination = self.services.pop(0)
        self.current_service = destination
        self.status_label.config(text=f"Solicitando viaje a {destination}")
        
        # Enviar solicitud de servicio
        try:
            self.producer.send('customer_events', {
                'type': 'SERVICE_REQUEST',
                'customer_id': self.customer_id,
                'destination': destination,
                'timestamp': time.time()
            })
            self.log_event(f"Servicio solicitado: {destination}")
            
            # Actualizar etiqueta del próximo destino
            next_destination = self.services[0] if self.services else "Ninguno"
            self.destination_label.config(text=next_destination)
            
            # Deshabilitar botón temporalmente
            self.request_button.config(state='disabled')
            self.root.after(4000, self.enable_request_button)  # Habilitar después de 4 segundos
            
        except Exception as e:
            self.log_event(f"Error solicitando servicio: {e}")

    def enable_request_button(self):
        """Habilitar botón de solicitud"""
        self.request_button.config(state='enabled')

    def run(self):
        """Iniciar la aplicación"""
        self.log_event("Aplicación cliente iniciada")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Manejar cierre de la aplicación"""
        self.running = False
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()
        self.root.destroy()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python main.py <kafka_server> <customer_id>")
        print("Ejemplo: python main.py localhost:9092 customer1")
        sys.exit(1)

    try:
        kafka_server = sys.argv[1]
        customer_id = sys.argv[2]

        app = CustomerApp(kafka_server, customer_id)
        app.run()
    except Exception as e:
        print(f"Error iniciando la aplicación: {e}")
        sys.exit(1)