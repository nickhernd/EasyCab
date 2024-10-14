import tkinter as tk
from tkinter import ttk
import threading
import time
import logging
from confluent_kafka import Consumer
from kafka_utils import receive_kafka_message, create_kafka_consumer
from map_utils import create_empty_map, update_map

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECGUI:
    def __init__(self, map_size=20):
        self.root = tk.Tk()
        self.root.title("Sistema de Monitoreo EasyCab")
        self.root.configure(bg='#f0f0f0')
        
        self.map_size = map_size
        self.map = create_empty_map(map_size)
        self.taxi_info = {}
        self.client_info = {}
        
        self.setup_gui()
        self.setup_kafka_consumer()
        
    def setup_gui(self):
        # Marco principal
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        # Título
        title_label = ttk.Label(main_frame, text="*** EASY CAB Release 1 ***", font=('Helvetica', 16, 'bold'))
        title_label.grid(column=0, row=0, columnspan=2, pady=(0, 10))
        
        # Marco para la información de taxis y clientes
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(column=0, row=1, columnspan=2, pady=(0, 10))
        
        # Información de taxis
        taxi_frame = ttk.LabelFrame(info_frame, text="Taxis")
        taxi_frame.grid(column=0, row=0, padx=(0, 5))
        self.taxi_tree = ttk.Treeview(taxi_frame, columns=('Id', 'Destino', 'Estado'), show='headings', height=5)
        self.taxi_tree.heading('Id', text='Id.')
        self.taxi_tree.heading('Destino', text='Destino')
        self.taxi_tree.heading('Estado', text='Estado')
        self.taxi_tree.grid(column=0, row=0)
        
        # Información de clientes
        client_frame = ttk.LabelFrame(info_frame, text="Clientes")
        client_frame.grid(column=1, row=0, padx=(5, 0))
        self.client_tree = ttk.Treeview(client_frame, columns=('Id', 'Destino', 'Estado'), show='headings', height=5)
        self.client_tree.heading('Id', text='Id.')
        self.client_tree.heading('Destino', text='Destino')
        self.client_tree.heading('Estado', text='Estado')
        self.client_tree.grid(column=0, row=0)
        
        # Mapa
        self.map_canvas = tk.Canvas(main_frame, width=400, height=400, bg="white")
        self.map_canvas.grid(column=0, row=2, columnspan=2)
        
        # Estado del sistema
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(column=0, row=3, columnspan=2, pady=(10, 0))
        ttk.Label(status_frame, text="Estado del Sistema:", font=('Helvetica', 10, 'bold')).grid(column=0, row=0)
        self.status_var = tk.StringVar(value="En funcionamiento")
        ttk.Label(status_frame, textvariable=self.status_var, foreground="green").grid(column=1, row=0)
        
        self.draw_map()
        
    def setup_kafka_consumer(self):
        try:
            self.consumer = create_kafka_consumer('localhost:9092', 'taxi_updates', 'gui-group')
            logger.info("Consumidor Kafka configurado exitosamente")
        except Exception as e:
            logger.error(f"Error al configurar el consumidor Kafka: {str(e)}")
        
    def draw_map(self):
        cell_width = 400 // self.map_size
        for i in range(self.map_size):
            for j in range(self.map_size):
                x1, y1 = i * cell_width, j * cell_width
                x2, y2 = x1 + cell_width, y1 + cell_width
                self.map_canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="gray")
                content = self.map[j][i]
                if content != ' ':
                    color = "blue" if content.isdigit() else "green"
                    self.map_canvas.create_oval(x1+2, y1+2, x2-2, y2-2, fill=color)
                    self.map_canvas.create_text((x1+x2)//2, (y1+y2)//2, text=content, fill="white")

    def update_gui(self):
        self.draw_map()
        self.update_taxi_info()
        self.update_client_info()
        
    def update_taxi_info(self):
        for item in self.taxi_tree.get_children():
            self.taxi_tree.delete(item)
        for taxi_id, info in self.taxi_info.items():
            self.taxi_tree.insert('', 'end', values=(taxi_id, info['destino'], info['estado']))
        
    def update_client_info(self):
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)
        for client_id, info in self.client_info.items():
            self.client_tree.insert('', 'end', values=(client_id, info['destino'], info['estado']))
        
    def kafka_listener(self):
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                update = receive_kafka_message(msg)
                self.map = update_map(self.map, update)
                self.root.after(0, self.update_gui)
        except Exception as e:
            logger.error(f"Error in Kafka listener: {str(e)}")
            
    def run(self):
        kafka_thread = threading.Thread(target=self.kafka_listener, daemon=True)
        kafka_thread.start()
        
        self.root.mainloop()

    def close(self):
        if hasattr(self, 'consumer'):
            self.consumer.close()
        logger.info("ECGUI closed")

if __name__ == "__main__":
    gui = ECGUI()
    try:
        gui.run()
    except KeyboardInterrupt:
        logger.info("GUI interrupted by user")
    finally:
        gui.close()
