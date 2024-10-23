import mysql.connector
from mysql.connector import Error
import json
import os
from typing import Dict, List, Optional

class DatabaseManager:
    def __init__(self, host: str, user: str, password: str, database: str):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.connection = None
        self.connect()

    def connect(self):
        """Establece conexión con la base de datos"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            print("Conexión a MySQL establecida")
        except Error as e:
            print(f"Error conectando a MySQL: {e}")
            raise

    def load_locations(self, filename: str) -> List[Dict]:
        """Carga ubicaciones desde archivo y las guarda en la BD"""
        locations = []
        try:
            with open(filename, 'r') as file:
                for line in file:
                    loc_id, x, y = line.strip().split()
                    locations.append({
                        'id': loc_id,
                        'x': int(x),
                        'y': int(y)
                    })
                    self.insert_location(loc_id, int(x), int(y))
            return locations
        except Exception as e:
            print(f"Error cargando ubicaciones: {e}")
            return []

    def insert_location(self, loc_id: str, x: int, y: int):
        """Inserta una nueva ubicación"""
        query = """
        INSERT INTO locations (id_location, coordenada_x, coordenada_y)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
        coordenada_x = VALUES(coordenada_x),
        coordenada_y = VALUES(coordenada_y)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (loc_id, x, y))
            self.connection.commit()

    def update_taxi_status(self, taxi_id: str, estado: str, pos_x: int, pos_y: int, 
                          current_ride: Optional[str] = None):
        """Actualiza el estado de un taxi"""
        query = """
        INSERT INTO taxis (id, estado, posicion_x, posicion_y, current_ride_id)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        estado = VALUES(estado),
        posicion_x = VALUES(posicion_x),
        posicion_y = VALUES(posicion_y),
        current_ride_id = VALUES(current_ride_id),
        ultima_actualizacion = CURRENT_TIMESTAMP
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (taxi_id, estado, pos_x, pos_y, current_ride))
            self.connection.commit()

    def insert_ride(self, ride_id: str, taxi_id: str, customer_id: str,
                   pickup: List[int], destination: List[int], estado: str):
        """Registra un nuevo viaje"""
        query = """
        INSERT INTO rides (ride_id, taxi_id, customer_id, pickup_x, pickup_y,
                         destination_x, destination_y, estado, start_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (ride_id, taxi_id, customer_id,
                                 pickup[0], pickup[1],
                                 destination[0], destination[1],
                                 estado))
            self.connection.commit()

    def get_active_taxis(self) -> List[Dict]:
        """Obtiene lista de taxis activos"""
        query = "SELECT * FROM taxis WHERE is_active = TRUE"
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def get_location_coordinates(self, loc_id: str) -> Optional[List[int]]:
        """Obtiene coordenadas de una ubicación"""
        query = "SELECT coordenada_x, coordenada_y FROM locations WHERE id_location = %s"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (loc_id,))
            result = cursor.fetchone()
            return list(result) if result else None

    def log_event(self, event_type: str, event_data: Dict):
        """Registra un evento del sistema"""
        query = """
        INSERT INTO system_events (event_type, event_data)
        VALUES (%s, %s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (event_type, json.dumps(event_data)))
            self.connection.commit()

    def close(self):
        """Cierra la conexión"""
        if self.connection and self.connection.is_connected():
            self.connection.close()