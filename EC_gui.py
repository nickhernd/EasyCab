import tkinter as tk
from tkinter import ttk
import json
import threading
import time
import requests
from PIL import Image, ImageTk

class EasyCabGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EasyCab Dashboard")
        self.root.geometry("1200x800")
        
        # Configurar el estilo
        self.style = ttk.Style()
        self.style.configure("Header.TLabel", font=('Arial', 14, 'bold'))
        
        # Crear el marco principal
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Inicializar componentes
        self.setup_header()
        self.setup_stats()
        self.setup_map()
        self.setup_taxi_list()
        
        # Iniciar actualizaciones
        self.update_thread = threading.Thread(target=self.update_data_loop, daemon=True)
        self.update_thread.start()

    def setup_header(self):
        header = ttk.Label(
            self.main_frame,
            text="EasyCab Control Panel",
            style="Header.TLabel"
        )
        header.grid(row=0, column=0, columnspan=2, pady=10)
        
        self.status_label = ttk.Label(
            self.main_frame,
            text="Sistema Online",
            foreground="green"
        )
        self.status_label.grid(row=0, column=2, pady=10)

    def setup_stats(self):
        stats_frame = ttk.LabelFrame(self.main_frame, text="Estadísticas", padding="5")
        stats_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.active_taxis_label = ttk.Label(stats_frame, text="Taxis Activos: 0")
        self.active_taxis_label.grid(row=0, column=0, padx=10)
        
        self.active_rides_label = ttk.Label(stats_frame, text="Viajes Activos: 0")
        self.active_rides_label.grid(row=0, column=1, padx=10)
        
        self.pending_requests_label = ttk.Label(stats_frame, text="Solicitudes Pendientes: 0")
        self.pending_requests_label.grid(row=0, column=2, padx=10)

    def setup_map(self):
        self.map_frame = ttk.LabelFrame(self.main_frame, text="Mapa en Tiempo Real", padding="5")
        self.map_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.map_canvas = tk.Canvas(self.map_frame, width=600, height=600, bg='white')
        self.map_canvas.grid(row=0, column=0)
        
        # Inicializar matriz del mapa
        self.map_cells = []
        cell_size = 30
        for i in range(20):
            row = []
            for j in range(20):
                x1 = j * cell_size
                y1 = i * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                cell = self.map_canvas.create_rectangle(x1, y1, x2, y2, fill='white')
                row.append(cell)
            self.map_cells.append(row)

    def setup_taxi_list(self):
        taxi_frame = ttk.LabelFrame(self.main_frame, text="Taxis Activos", padding="5")
        taxi_frame.grid(row=2, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.taxi_tree = ttk.Treeview(taxi_frame, columns=('ID', 'Estado', 'Posición'))
        self.taxi_tree.heading('ID', text='ID')
        self.taxi_tree.heading('Estado', text='Estado')
        self.taxi_tree.heading('Posición', text='Posición')
        self.taxi_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def update_map(self, map_data):
        for i in range(20):
            for j in range(20):
                cell = map_data[i][j]
                color = 'white'
                if isinstance(cell, str):
                    if cell.startswith('T'):
                        color = 'green' if 'MOVING' in cell else 'red'
                    elif cell.isupper():
                        color = 'blue'  # Destinos
                    elif cell.islower():
                        color = 'yellow'  # Clientes
                self.map_canvas.itemconfig(self.map_cells[i][j], fill=color)

    def update_taxi_list(self, taxis_data):
        # Limpiar lista actual
        for item in self.taxi_tree.get_children():
            self.taxi_tree.delete(item)
        
        # Actualizar con nuevos datos
        for taxi_id, info in taxis_data.items():
            self.taxi_tree.insert(
                '',
                'end',
                values=(
                    taxi_id,
                    info.get('state', 'N/A'),
                    f"[{info.get('position', [0,0])[0]}, {info.get('position', [0,0])[1]}]"
                )
            )

    def update_stats(self, system_status):
        self.active_taxis_label['text'] = f"Taxis Activos: {system_status.get('taxis', {}).get('active', 0)}"
        self.active_rides_label['text'] = f"Viajes Activos: {system_status.get('active_rides', 0)}"
        self.pending_requests_label['text'] = f"Solicitudes Pendientes: {system_status.get('pending_requests', 0)}"

    def fetch_data(self):
        try:
            # Obtener datos del mapa
            map_response = requests.get('http://localhost:8000/map')
            map_data = map_response.json()
            
            # Obtener estado del sistema
            status_response = requests.get('http://localhost:8000/system/status')
            status_data = status_response.json()
            
            # Obtener datos de taxis
            taxis_response = requests.get('http://localhost:8000/taxis')
            taxis_data = taxis_response.json()
            
            return map_data, status_data, taxis_data.get('taxis', {})
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None, None, None

    def update_data_loop(self):
        while True:
            map_data, status_data, taxis_data = self.fetch_data()
            
            if map_data is not None:
                self.root.after(0, self.update_map, map_data)
            if status_data is not None:
                self.root.after(0, self.update_stats, status_data)
            if taxis_data is not None:
                self.root.after(0, self.update_taxi_list, taxis_data)
            
            time.sleep(1)

def main():
    root = tk.Tk()
    app = EasyCabGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()