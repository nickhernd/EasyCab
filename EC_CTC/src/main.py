# EC_CTC/src/main.py
import sys
import json
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import requests
from fastapi import FastAPI, HTTPException
import uvicorn
from pydantic import BaseModel
import asyncio
from datetime import datetime

class WeatherResponse(BaseModel):
    status: str
    temperature: float
    city: str
    timestamp: str

class CityTrafficControl:
    def __init__(self, api_port: int, weather_api_key: str):
        self.api_port = api_port
        self.weather_api_key = weather_api_key
        self.current_city = "Madrid"  # Ciudad por defecto
        self.running = True
        self.last_temperature = None
        self.traffic_status = "OK"
        
        # Crear aplicación FastAPI
        self.app = FastAPI(title="EC_CTC API")
        self.setup_api_routes()
        
        # Inicializar GUI
        self.setup_gui()
        
        # Iniciar thread para actualizaciones periódicas
        self.update_thread = None

    def setup_gui(self):
        """Configurar interfaz gráfica"""
        self.root = tk.Tk()
        self.root.title("EC_CTC (City Traffic Control)")
        self.root.geometry("600x500")

        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Ciudad actual
        city_frame = ttk.Frame(main_frame)
        city_frame.grid(row=0, column=0, columnspan=2, pady=5)
        
        ttk.Label(city_frame, text="Ciudad actual:").grid(row=0, column=0, padx=5)
        self.city_entry = ttk.Entry(city_frame)
        self.city_entry.insert(0, self.current_city)
        self.city_entry.grid(row=0, column=1, padx=5)
        
        ttk.Button(
            city_frame,
            text="Cambiar ciudad",
            command=self.change_city
        ).grid(row=0, column=2, padx=5)

        # Estado del tráfico
        ttk.Label(main_frame, text="Estado del tráfico:").grid(row=1, column=0, sticky=tk.W)
        self.status_label = ttk.Label(main_frame, text="Consultando...")
        self.status_label.grid(row=1, column=1, sticky=tk.W)

        # Temperatura
        ttk.Label(main_frame, text="Temperatura:").grid(row=2, column=0, sticky=tk.W)
        self.temp_label = ttk.Label(main_frame, text="Consultando...")
        self.temp_label.grid(row=2, column=1, sticky=tk.W)

        # Última actualización
        ttk.Label(main_frame, text="Última actualización:").grid(row=3, column=0, sticky=tk.W)
        self.update_label = ttk.Label(main_frame, text="-")
        self.update_label.grid(row=3, column=1, sticky=tk.W)

        # Log de eventos
        ttk.Label(main_frame, text="Log de eventos:").grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(10,0))
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=60)
        self.log_text.grid(row=5, column=0, columnspan=2, pady=5)

        # Estado del servidor
        self.server_status = ttk.Label(main_frame, text="Servidor: Iniciando...")
        self.server_status.grid(row=6, column=0, columnspan=2, pady=5)

    def setup_api_routes(self):
        """Configurar rutas de la API"""
        @self.app.get("/status")
        async def get_status():
            if not self.last_temperature:
                raise HTTPException(status_code=503, detail="Weather data not available yet")
                
            return WeatherResponse(
                status=self.traffic_status,
                temperature=self.last_temperature,
                city=self.current_city,
                timestamp=datetime.now().isoformat()
            )

    def log_event(self, message: str):
        """Agregar mensaje al log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"{timestamp}: {message}\n")
        self.log_text.see(tk.END)

    def change_city(self):
        """Cambiar la ciudad actual"""
        new_city = self.city_entry.get().strip()
        if new_city:
            self.current_city = new_city
            self.log_event(f"Ciudad cambiada a: {new_city}")
            self.update_weather()

    def get_weather(self):
        """Obtener datos del tiempo de OpenWeather"""
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': self.current_city,
                'appid': self.weather_api_key,
                'units': 'metric'  # Para obtener temperatura en Celsius
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            temperature = data['main']['temp']
            
            return temperature
        except Exception as e:
            self.log_event(f"Error obteniendo datos del tiempo: {e}")
            return None

    def update_weather(self):
        """Actualizar datos del tiempo y estado del tráfico"""
        temperature = self.get_weather()
        if temperature is not None:
            self.last_temperature = temperature
            self.temp_label.config(text=f"{temperature:.1f}°C")
            
            # Actualizar estado del tráfico basado en la temperatura
            if temperature < 0:
                self.traffic_status = "KO"
                self.status_label.config(text="KO - Temperatura bajo cero", foreground="red")
            else:
                self.traffic_status = "OK"
                self.status_label.config(text="OK - Circulación normal", foreground="green")
            
            current_time = time.strftime("%H:%M:%S")
            self.update_label.config(text=current_time)
            self.log_event(f"Actualización: {temperature:.1f}°C - Estado: {self.traffic_status}")

    def periodic_update(self):
        """Actualización periódica del tiempo"""
        while self.running:
            self.update_weather()
            time.sleep(10)  # Actualizar cada 10 segundos

    async def start_server(self):
        """Iniciar servidor FastAPI"""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.api_port,
            log_level="error"
        )
        server = uvicorn.Server(config)
        await server.serve()

    def run_server(self):
        """Ejecutar servidor en un thread separado"""
        asyncio.run(self.start_server())

    def run(self):
        """Iniciar la aplicación"""
        # Iniciar thread del servidor
        server_thread = threading.Thread(target=self.run_server)
        server_thread.daemon = True
        server_thread.start()
        self.server_status.config(text=f"Servidor: Ejecutando en puerto {self.api_port}")
        
        # Iniciar thread de actualizaciones
        self.update_thread = threading.Thread(target=self.periodic_update)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # Iniciar GUI
        self.log_event("Sistema CTC iniciado")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Manejar cierre de la aplicación"""
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python main.py <puerto_api> <api_key_openweather>")
        print("Ejemplo: python main.py 8002 abc123def456")
        sys.exit(1)

    try:
        api_port = int(sys.argv[1])
        weather_api_key = sys.argv[2]

        ctc = CityTrafficControl(api_port, weather_api_key)
        ctc.run()
    except ValueError:
        print("Error: El puerto debe ser un número entero")
        sys.exit(1)
    except Exception as e:
        print(f"Error iniciando CTC: {e}")
        sys.exit(1)