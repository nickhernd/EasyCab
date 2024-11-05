# EC_Registry/src/main.py
import sys
import json
import time
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn
from pydantic import BaseModel
import secrets
import ssl
from cryptography.fernet import Fernet
import base64
import asyncio

# Modelos de datos
class TaxiRegistration(BaseModel):
    taxi_id: int
    public_key: str  # Para el intercambio de claves

class TaxiResponse(BaseModel):
    status: str
    message: str
    registration_token: str = None

class RegistryDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('registry.db', check_same_thread=False)
        self.setup_database()
        
    def setup_database(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS taxis (
            taxi_id INTEGER PRIMARY KEY,
            public_key TEXT,
            registration_token TEXT,
            status TEXT,
            registered_at TIMESTAMP,
            last_updated TIMESTAMP
        )''')
        self.conn.commit()

    def register_taxi(self, taxi_id: int, public_key: str, registration_token: str):
        cursor = self.conn.cursor()
        now = datetime.now()
        cursor.execute('''
        INSERT OR REPLACE INTO taxis 
        (taxi_id, public_key, registration_token, status, registered_at, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (taxi_id, public_key, registration_token, 'ACTIVE', now, now))
        self.conn.commit()

    def deregister_taxi(self, taxi_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM taxis WHERE taxi_id = ?', (taxi_id,))
        self.conn.commit()

    def get_taxi(self, taxi_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM taxis WHERE taxi_id = ?', (taxi_id,))
        return cursor.fetchone()

    def get_all_taxis(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM taxis')
        return cursor.fetchall()

class RegistryServer:
    def __init__(self, port: int):
        self.port = port
        self.db = RegistryDatabase()
        self.running = True
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Configurar FastAPI
        self.app = FastAPI(title="EC_Registry API")
        self.security = HTTPBasic()
        self.setup_api_routes()
        
        # Configurar GUI
        self.setup_gui()

    def setup_gui(self):
        """Configurar interfaz gráfica"""
        self.root = tk.Tk()
        self.root.title("EC_Registry")
        self.root.geometry("800x600")

        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Estado del servidor
        self.server_status = ttk.Label(main_frame, text="Servidor: Iniciando...")
        self.server_status.grid(row=0, column=0, columnspan=2, pady=5)

        # Lista de taxis registrados
        ttk.Label(main_frame, text="Taxis Registrados:").grid(row=1, column=0, sticky=tk.W)
        
        # Crear Treeview para taxis
        self.taxi_tree = ttk.Treeview(main_frame, columns=('ID', 'Status', 'Registered', 'Last Updated'), show='headings')
        self.taxi_tree.heading('ID', text='Taxi ID')
        self.taxi_tree.heading('Status', text='Estado')
        self.taxi_tree.heading('Registered', text='Fecha Registro')
        self.taxi_tree.heading('Last Updated', text='Última Actualización')
        self.taxi_tree.grid(row=2, column=0, columnspan=2, pady=5)

        # Scrollbar para Treeview
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.taxi_tree.yview)
        scrollbar.grid(row=2, column=2, sticky=(tk.N, tk.S))
        self.taxi_tree.configure(yscrollcommand=scrollbar.set)

        # Log de eventos
        ttk.Label(main_frame, text="Log de eventos:").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10,0))
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=80)
        self.log_text.grid(row=4, column=0, columnspan=2, pady=5)

    def setup_api_routes(self):
        """Configurar rutas de la API"""
        @self.app.post("/register", response_model=TaxiResponse)
        async def register_taxi(taxi: TaxiRegistration, credentials: HTTPBasicCredentials = Depends(self.security)):
            # Verificar credenciales
            if not self.verify_credentials(credentials):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            try:
                # Generar token de registro
                registration_token = secrets.token_urlsafe(32)
                
                # Encriptar token con la clave pública del taxi
                encrypted_token = self.encrypt_token(registration_token, taxi.public_key)
                
                # Registrar taxi en la base de datos
                self.db.register_taxi(taxi.taxi_id, taxi.public_key, registration_token)
                
                self.log_event(f"Taxi {taxi.taxi_id} registrado exitosamente")
                self.update_taxi_list()
                
                return TaxiResponse(
                    status="SUCCESS",
                    message="Taxi registered successfully",
                    registration_token=encrypted_token
                )
            except Exception as e:
                self.log_event(f"Error registrando taxi {taxi.taxi_id}: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/deregister/{taxi_id}")
        async def deregister_taxi(taxi_id: int, credentials: HTTPBasicCredentials = Depends(self.security)):
            if not self.verify_credentials(credentials):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            try:
                self.db.deregister_taxi(taxi_id)
                self.log_event(f"Taxi {taxi_id} dado de baja")
                self.update_taxi_list()
                return TaxiResponse(status="SUCCESS", message="Taxi deregistered successfully")
            except Exception as e:
                self.log_event(f"Error dando de baja taxi {taxi_id}: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/taxi/{taxi_id}")
        async def get_taxi(taxi_id: int, credentials: HTTPBasicCredentials = Depends(self.security)):
            if not self.verify_credentials(credentials):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            taxi = self.db.get_taxi(taxi_id)
            if not taxi:
                raise HTTPException(status_code=404, detail="Taxi not found")
            return {
                "taxi_id": taxi[0],
                "status": taxi[3],
                "registered_at": taxi[4]
            }

    def verify_credentials(self, credentials: HTTPBasicCredentials) -> bool:
        """Verificar credenciales de acceso"""
        # En un entorno real, verificar contra una base de datos segura
        correct_username = secrets.compare_digest(credentials.username, "admin")
        correct_password = secrets.compare_digest(credentials.password, "admin")
        return correct_username and correct_password

    def encrypt_token(self, token: str, public_key: str) -> str:
        """Encriptar token con la clave pública del taxi"""
        try:
            # En un entorno real, usar la clave pública para encriptar
            return base64.b64encode(self.cipher_suite.encrypt(token.encode())).decode()
        except Exception as e:
            self.log_event(f"Error encriptando token: {e}")
            raise

    def log_event(self, message: str):
        """Agregar mensaje al log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"{timestamp}: {message}\n")
        self.log_text.see(tk.END)

    def update_taxi_list(self):
        """Actualizar lista de taxis en la GUI"""
        # Limpiar lista actual
        for item in self.taxi_tree.get_children():
            self.taxi_tree.delete(item)
            
        # Obtener y mostrar taxis registrados
        for taxi in self.db.get_all_taxis():
            self.taxi_tree.insert('', 'end', values=(
                taxi[0],  # ID
                taxi[3],  # Status
                taxi[4],  # Registered At
                taxi[5]   # Last Updated
            ))

    async def start_server(self):
        """Iniciar servidor FastAPI con SSL"""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="error",
            ssl_keyfile="key.pem",    # Generar en producción
            ssl_certfile="cert.pem"    # Generar en producción
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
        
        self.server_status.config(text=f"Servidor: Ejecutando en puerto {self.port} (HTTPS)")
        self.log_event("Servidor Registry iniciado")
        
        # Actualizar lista inicial de taxis
        self.update_taxi_list()
        
        # Iniciar GUI
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Manejar cierre de la aplicación"""
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python main.py <puerto_api>")
        print("Ejemplo: python main.py 8001")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
        registry = RegistryServer(port)
        registry.run()
    except ValueError:
        print("Error: El puerto debe ser un número entero")
        sys.exit(1)
    except Exception as e:
        print(f"Error iniciando Registry: {e}")
        sys.exit(1)