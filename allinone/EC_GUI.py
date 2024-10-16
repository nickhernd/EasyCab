import os
import sys
import tkinter as tk
from tkinter import ttk
import threading
import time
import logging
import cmd
from confluent_kafka import Consumer, KafkaError
from kafka_utils import receive_kafka_message, create_kafka_consumer
from map_utils import create_empty_map, update_map
from confluent_kafka.admin import AdminClient, NewTopic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECGUI:
    def __init__(self, map_size=20):
        self.root = tk.Tk()
        self.root.title("EasyCab Monitoring System")
        self.root.configure(bg='#f0f0f0')
        
        self.map_size = map_size
        self.map = create_empty_map(map_size)
        self.taxi_info = {}
        self.client_info = {}
        self.location_info = {}
        
        self.setup_gui()
        self.setup_kafka_consumer()
        
    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        title_label = ttk.Label(main_frame, text="EASY CAB Release 1", font=('Helvetica', 18, 'bold'))
        title_label.grid(column=0, row=0, columnspan=2, pady=(0, 20))
        
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(column=0, row=1, columnspan=2, pady=(0, 20), sticky="ew")
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)
        
        self.setup_taxi_frame(info_frame)
        self.setup_client_frame(info_frame)
        
        self.map_canvas = tk.Canvas(main_frame, width=500, height=500, bg="white")
        self.map_canvas.grid(column=0, row=2, columnspan=2, pady=(0, 20), sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        self.setup_status_frame(main_frame)
        
        self.draw_map()
        
    def setup_taxi_frame(self, parent):
        taxi_frame = ttk.LabelFrame(parent, text="Taxis", padding="10")
        taxi_frame.grid(column=0, row=0, padx=(0, 10), sticky="nsew")
        self.taxi_tree = ttk.Treeview(taxi_frame, columns=('Id', 'Position', 'Status'), show='headings', height=5)
        self.taxi_tree.heading('Id', text='Id')
        self.taxi_tree.heading('Position', text='Position')
        self.taxi_tree.heading('Status', text='Status')
        self.taxi_tree.grid(sticky="nsew")
        taxi_frame.columnconfigure(0, weight=1)
        taxi_frame.rowconfigure(0, weight=1)
        
    def setup_client_frame(self, parent):
        client_frame = ttk.LabelFrame(parent, text="Clients", padding="10")
        client_frame.grid(column=1, row=0, padx=(10, 0), sticky="nsew")
        self.client_tree = ttk.Treeview(client_frame, columns=('Id', 'Position', 'Destination'), show='headings', height=5)
        self.client_tree.heading('Id', text='Id')
        self.client_tree.heading('Position', text='Position')
        self.client_tree.heading('Destination', text='Destination')
        self.client_tree.grid(sticky="nsew")
        client_frame.columnconfigure(0, weight=1)
        client_frame.rowconfigure(0, weight=1)
        
    def setup_status_frame(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.grid(column=0, row=3, columnspan=2, pady=(0, 10), sticky="ew")
        ttk.Label(status_frame, text="System Status:", font=('Helvetica', 12, 'bold')).grid(column=0, row=0)
        self.status_var = tk.StringVar(value="Operational")
        ttk.Label(status_frame, textvariable=self.status_var, foreground="green", font=('Helvetica', 12)).grid(column=1, row=0)
        
    def setup_kafka_consumer(self):
        try:
            self.consumer = Consumer({
                'bootstrap.servers': 'kafka:9092',
                'group.id': 'gui-group',
                'auto.offset.reset': 'earliest'
            })
            self.consumer.subscribe(['taxi_updates', 'customer_updates', 'map_updates'])
            logger.info("Kafka consumer configured successfully")
        except Exception as e:
            logger.error(f"Error configuring Kafka consumer: {str(e)}")
            self.status_var.set("Error connecting to Kafka")
        
    def draw_map(self):
        self.map_canvas.delete("all")
        cell_width = 500 // self.map_size
        for i in range(self.map_size):
            for j in range(self.map_size):
                x1, y1 = i * cell_width, j * cell_width
                x2, y2 = x1 + cell_width, y1 + cell_width
                self.map_canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="gray")
                content = self.map[j][i]
                if content != ' ':
                    if isinstance(content, dict):  
                        if 'type' in content:
                            if content['type'] == 'taxi':
                                color = "green" if content.get('status') == 'AVAILABLE' else "red"
                                self.map_canvas.create_oval(x1+4, y1+4, x2-4, y2-4, fill=color)
                                self.map_canvas.create_text((x1+x2)//2, (y1+y2)//2, text=content.get('id', ''), fill="white", font=('Helvetica', 10, 'bold'))
                            elif content['type'] == 'client':
                                self.map_canvas.create_oval(x1+4, y1+4, x2-4, y2-4, fill="yellow")
                                self.map_canvas.create_text((x1+x2)//2, (y1+y2)//2, text=content.get('id', ''), fill="black", font=('Helvetica', 10, 'bold'))
                            elif content['type'] == 'location':
                                self.map_canvas.create_rectangle(x1+4, y1+4, x2-4, y2-4, fill="blue")
                                self.map_canvas.create_text((x1+x2)//2, (y1+y2)//2, text=content.get('id', ''), fill="white", font=('Helvetica', 10, 'bold'))
                    else:  # Si el contenido es una cadena (como en tu implementación original)
                        if content.isdigit():
                            color = "green" if self.taxi_info.get(content, {}).get('status') == 'AVAILABLE' else "red"
                            self.map_canvas.create_oval(x1+4, y1+4, x2-4, y2-4, fill=color)
                            self.map_canvas.create_text((x1+x2)//2, (y1+y2)//2, text=content, fill="white", font=('Helvetica', 10, 'bold'))
                        elif content.isupper():
                            self.map_canvas.create_rectangle(x1+4, y1+4, x2-4, y2-4, fill="blue")
                            self.map_canvas.create_text((x1+x2)//2, (y1+y2)//2, text=content, fill="white", font=('Helvetica', 10, 'bold'))
                        elif content.islower():
                            self.map_canvas.create_oval(x1+4, y1+4, x2-4, y2-4, fill="yellow")
                            self.map_canvas.create_text((x1+x2)//2, (y1+y2)//2, text=content, fill="black", font=('Helvetica', 10, 'bold'))

    def update_gui(self):
        self.draw_map()
        self.update_taxi_info()
        self.update_client_info()
        self.root.update()  # Forzar actualización de la GUI
        
    def update_taxi_info(self):
        for item in self.taxi_tree.get_children():
            self.taxi_tree.delete(item)
        for taxi_id, info in self.taxi_info.items():
            self.taxi_tree.insert('', 'end', values=(taxi_id, f"({info['position'][0]}, {info['position'][1]})", info['status']))
        
    def update_client_info(self):
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)
        for client_id, info in self.client_info.items():
            self.client_tree.insert('', 'end', values=(client_id, f"({info['position'][0]}, {info['position'][1]})", info.get('destination', 'N/A')))
        
    def kafka_listener(self):
        logger.info("Starting Kafka listener")
        while True:
            try:
                logger.info("Polling for messages...")
                msg = self.consumer.poll(1.0)
                if msg is None:
                    logger.info("No message received")
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        self.status_var.set(f"Error: {msg.error()}")
                        continue
                    
                logger.info(f"Received message on topic {msg.topic()}")
                update = receive_kafka_message(msg)
                logger.info(f"Message content: {update}")

                if msg.topic() == 'taxi_updates':
                    self.handle_taxi_update(update)
                elif msg.topic() == 'customer_updates':
                    self.handle_customer_update(update)
                elif msg.topic() == 'map_updates':
                    self.handle_map_update(update)
                else:
                    logger.warning(f"Received message on unknown topic: {msg.topic()}")

                self.root.after(0, self.update_gui)

            except Exception as e:
                logger.error(f"Error in Kafka listener: {str(e)}")
                self.status_var.set(f"Error: {str(e)}")
                time.sleep(5)
    
    def handle_taxi_update(self, update):
        taxi_id = str(update['taxi_id'])
        self.taxi_info[taxi_id] = {
            'position': update['position'],
            'status': update['status']
        }
        self.map = update_map(self.map, update)
        print(f"GUI: Actualización de taxi recibida - ID: {update['taxi_id']}, Posición: {update['position']}, Estado: {update['status']}")

    def handle_customer_update(self, update):
        client_id = update['customer_id']
        self.client_info[client_id] = {
            'position': update['location'],
            'destination': update.get('destination', 'N/A')
        }
        self.map = update_map(self.map, {'position': update['location'], 'customer_id': client_id})
        print(f"GUI: Actualización de cliente recibida - ID: {update['customer_id']}, Posición: {update['location']}")

    def handle_map_update(self, update):
        self.map = update['map']
        print("GUI: Actualización de mapa recibida")
            
    def run(self):
        kafka_thread = threading.Thread(target=self.kafka_listener, daemon=True)
        kafka_thread.start()

        def update_periodically():
            self.update_gui()
            self.root.after(1000, update_periodically)  # Actualizar cada segundo
    
        update_periodically()
        self.root.mainloop()

    def close(self):
        if hasattr(self, 'consumer'):
            self.consumer.close()
        logger.info("ECGUI closed")

    def ensure_topics_exist(bootstrap_servers, topics, max_retries=5, retry_interval=5):
        admin_client = AdminClient({'bootstrap.servers': bootstrap_servers})

        for _ in range(max_retries):
            try:
                existing_topics = admin_client.list_topics(timeout=5).topics
                missing_topics = [topic for topic in topics if topic not in existing_topics]

                if not missing_topics:
                    print("All required topics exist.")
                    return True

                print(f"Missing topics: {missing_topics}. Attempting to create...")
                new_topics = [NewTopic(topic, num_partitions=1, replication_factor=1) for topic in missing_topics]
                admin_client.create_topics(new_topics)
                print("Topics created successfully.")
                return True
            except Exception as e:
                print(f"Error ensuring topics exist: {e}")
                time.sleep(retry_interval)

        print("Failed to ensure topics exist after maximum retries.")
        return False

if __name__ == "__main__":
    kafka_bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    
    if not ECGUI.ensure_topics_exist(kafka_bootstrap_servers, ['taxi_updates', 'customer_updates', 'map_updates']):
        print("Failed to ensure Kafka topics exist. Exiting.")
        sys.exit(1)

    gui = ECGUI()
    try:
        gui.run()
    except KeyboardInterrupt:
        logger.info("GUI interrupted by user")
    finally:
        gui.close()