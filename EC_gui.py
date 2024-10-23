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
        self.setup_debug_panel()  # Nuevo panel de debug
        
        # Iniciar actualizaciones
        self.update_thread = threading.Thread(target=self.update_data_loop, daemon=True)
        self.update_thread.start()

    def setup_header(self):
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, columnspan=3, pady=10, sticky="ew")
        
        header = ttk.Label(
            header_frame,
            text="EasyCab Control Panel",
            style="Header.TLabel"
        )
        header.pack(side="left")
        
        self.status_label = ttk.Label(
            header_frame,
            text="Sistema Online",
            foreground="green"
        )
        self.status_label.pack(side="right")

    def setup_stats(self):
        stats_frame = ttk.LabelFrame(self.main_frame, text="Estadísticas", padding="5")
        stats_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        
        self.stats_labels = {
            'taxis': ttk.Label(stats_frame, text="Taxis Activos: 0"),
            'rides': ttk.Label(stats_frame, text="Viajes Activos: 0"),
            'requests': ttk.Label(stats_frame, text="Solicitudes Pendientes: 0")
        }
        
        for i, label in enumerate(self.stats_labels.values()):
            label.grid(row=0, column=i, padx=10)

    def setup_map(self):
        self.map_frame = ttk.LabelFrame(self.main_frame, text="Mapa en Tiempo Real", padding="5")
        self.map_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=5)
        
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
                cell = self.map_canvas.create_rectangle(x1, y1, x2, y2, fill='white', outline='gray')
                text = self.map_canvas.create_text((x1+x2)/2, (y1+y2)/2, text='')
                row.append((cell, text))
            self.map_cells.append(row)

    def setup_taxi_list(self):
        taxi_frame = ttk.LabelFrame(self.main_frame, text="Taxis Activos", padding="5")
        taxi_frame.grid(row=2, column=2, sticky="nsew", pady=5)
        
        # Configurar el Treeview
        columns = ('ID', 'Estado', 'Posición')
        self.taxi_tree = ttk.Treeview(taxi_frame, columns=columns, show='headings')
        
        # Configurar las columnas
        for col in columns:
            self.taxi_tree.heading(col, text=col)
            self.taxi_tree.column(col, width=100)
        
        # Añadir scrollbar
        scrollbar = ttk.Scrollbar(taxi_frame, orient="vertical", command=self.taxi_tree.yview)
        self.taxi_tree.configure(yscrollcommand=scrollbar.set)
        
        self.taxi_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        taxi_frame.columnconfigure(0, weight=1)
        taxi_frame.rowconfigure(0, weight=1)

    def setup_debug_panel(self):
        debug_frame = ttk.LabelFrame(self.main_frame, text="Debug Info", padding="5")
        debug_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        
        self.debug_text = tk.Text(debug_frame, height=5, width=80)
        self.debug_text.grid(row=0, column=0, sticky="ew")
        
        debug_scroll = ttk.Scrollbar(debug_frame, command=self.debug_text.yview)
        debug_scroll.grid(row=0, column=1, sticky="ns")
        
        self.debug_text.configure(yscrollcommand=debug_scroll.set)

    def log_debug(self, message):
        self.debug_text.insert(tk.END, f"{message}\n")
        self.debug_text.see(tk.END)

    def update_map(self, map_data):
        try:
            for i in range(20):
                for j in range(20):
                    cell_rect, cell_text = self.map_cells[i][j]
                    cell_value = map_data[i][j]
                    
                    # Color por defecto
                    color = 'white'
                    text = ''
                    
                    if cell_value:
                        if isinstance(cell_value, str):
                            if cell_value.startswith('T'):
                                # Es un taxi
                                taxi_info = cell_value.split('_')
                                text = taxi_info[0]
                                color = 'green' if len(taxi_info) > 1 and taxi_info[1] == 'MOVING' else 'red'
                            elif cell_value.isupper():
                                # Es una ubicación
                                color = 'blue'
                                text = cell_value
                            elif cell_value.islower():
                                # Es un cliente
                                color = 'yellow'
                                text = cell_value
                    
                    self.map_canvas.itemconfig(cell_rect, fill=color)
                    self.map_canvas.itemconfig(cell_text, text=text)
            
            self.log_debug(f"Mapa actualizado con {len([c for row in map_data for c in row if c])} elementos")
        except Exception as e:
            self.log_debug(f"Error actualizando mapa: {e}")

    def update_taxi_list(self, taxis_data):
        try:
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
            
            self.log_debug(f"Lista de taxis actualizada: {len(taxis_data)} taxis")
        except Exception as e:
            self.log_debug(f"Error actualizando lista de taxis: {e}")

    def update_stats(self, system_status):
        try:
            taxis_info = system_status.get('taxis', {})
            self.stats_labels['taxis'].config(
                text=f"Taxis Activos: {taxis_info.get('active', 0)}/{taxis_info.get('total', 0)}"
            )
            self.stats_labels['rides'].config(
                text=f"Viajes Activos: {taxis_info.get('active', 0)}"
            )
            self.stats_labels['requests'].config(
                text=f"Solicitudes Pendientes: {system_status.get('pending_requests', 0)}"
            )
            
            self.log_debug("Estadísticas actualizadas")
        except Exception as e:
            self.log_debug(f"Error actualizando estadísticas: {e}")

    def fetch_data(self):
        try:
            # Obtener datos del mapa
            map_response = requests.get('http://localhost:8000/map')
            map_data = map_response.json()
            self.log_debug(f"Datos del mapa recibidos: {len(map_data)}x{len(map_data[0])}")
            
            # Obtener estado del sistema
            status_response = requests.get('http://localhost:8000/system/status')
            status_data = status_response.json()
            self.log_debug(f"Estado del sistema recibido: {status_data}")
            
            # Obtener datos de taxis
            taxis_response = requests.get('http://localhost:8000/taxis')
            taxis_data = taxis_response.json()
            self.log_debug(f"Datos de taxis recibidos: {len(taxis_data.get('taxis', {}))}")
            
            return map_data, status_data, taxis_data.get('taxis', {})
        except Exception as e:
            self.log_debug(f"Error obteniendo datos: {e}")
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