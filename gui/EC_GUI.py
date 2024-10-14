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
        self.root.title("EasyCab System Monitor")
        
        self.map_size = map_size
        self.map = create_empty_map(map_size)
        
        self.setup_gui()
        self.setup_kafka_consumer()
        
    def setup_gui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="3 3 12 12")
        main_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        # Mapa
        self.map_canvas = tk.Canvas(main_frame, width=400, height=400, bg="white")
        self.map_canvas.grid(column=0, row=0, columnspan=2)
        
        # Estado del sistema
        ttk.Label(main_frame, text="System Status:").grid(column=0, row=1, sticky=tk.W)
        self.status_var = tk.StringVar(value="Running")
        ttk.Label(main_frame, textvariable=self.status_var).grid(column=1, row=1, sticky=tk.W)
        
        # Información de taxis
        self.taxi_info = tk.Text(main_frame, width=50, height=10)
        self.taxi_info.grid(column=0, row=2, columnspan=2)
        
        self.draw_map()
        
    def setup_kafka_consumer(self):
        try:
            self.consumer = create_kafka_consumer('localhost:9092', 'taxi_updates', 'gui-group')
            logger.info("Kafka consumer set up successfully")
        except Exception as e:
            logger.error(f"Error setting up Kafka consumer: {str(e)}")
        
    def draw_map(self):
        cell_width = 400 // self.map_size
        for i in range(self.map_size):
            for j in range(self.map_size):
                x1, y1 = i * cell_width, j * cell_width
                x2, y2 = x1 + cell_width, y1 + cell_width
                self.map_canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="gray")
                content = self.map[j][i]
                if content != ' ':
                    self.map_canvas.create_text((x1+x2)//2, (y1+y2)//2, text=content)

    def update_gui(self):
        self.draw_map()
        self.taxi_info.delete('1.0', tk.END)
        for i in range(self.map_size):
            for j in range(self.map_size):
                if self.map[i][j] != ' ':
                    self.taxi_info.insert(tk.END, f"Taxi {self.map[i][j]} at position ({j}, {i})\n")
        
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
