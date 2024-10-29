import mysql.connector
from mysql.connector import Error
import os

class DatabaseHandler:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        """Establece conexión con la base de datos"""
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'mysql'),
                port=int(os.getenv('DB_PORT', '3306')),
                user=os.getenv('DB_USER', 'easycab'),
                password=os.getenv('DB_PASSWORD', 'easycab123'),
                database=os.getenv('DB_NAME', 'easycab')
            )
            print("Conexión a MySQL establecida correctamente")
        except Error as e:
            print(f"Error conectando a MySQL: {e}")
            raise

    def disconnect(self):
        """Cierra la conexión con la base de datos"""
        if self.connection:
            self.connection.close()

    def get_taxi_status(self, taxi_id):
        """Obtiene el estado actual de un taxi"""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM taxis WHERE id = %s", (taxi_id,))
        return cursor.fetchone()

    def update_taxi_position(self, taxi_id, x, y, status=None):
        """Actualiza la posición y opcionalmente el estado de un taxi"""
        cursor = self.connection.cursor()
        if status:
            cursor.execute("""
                UPDATE taxis 
                SET current_x = %s, current_y = %s, status = %s, last_status_update = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (x, y, status, taxi_id))
        else:
            cursor.execute("""
                UPDATE taxis 
                SET current_x = %s, current_y = %s, last_status_update = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (x, y, taxi_id))
        self.connection.commit()

    def create_service(self, customer_id, pickup_x, pickup_y, destination_id):
        """Crea un nuevo servicio"""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO services 
            (customer_id, pickup_x, pickup_y, destination_id, status)
            VALUES (%s, %s, %s, %s, 'REQUESTED')
        """, (customer_id, pickup_x, pickup_y, destination_id))
        self.connection.commit()
        return cursor.lastrowid

    def get_available_taxis(self):
        """Obtiene lista de taxis disponibles"""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM taxis WHERE status = 'AVAILABLE'")
        return cursor.fetchall()

    def record_sensor_incident(self, taxi_id, service_id, incident_type, x, y):
        """Registra una incidencia de sensor"""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO sensor_incidents 
            (taxi_id, service_id, incident_type, coord_x, coord_y)
            VALUES (%s, %s, %s, %s, %s)
        """, (taxi_id, service_id, incident_type, x, y))
        self.connection.commit()
        return cursor.lastrowid