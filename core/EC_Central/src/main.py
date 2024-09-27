from db_connector import DBConnector

# Configuración de la base de datos (deberías cargar estos valores desde un archivo de configuración)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'easycab',
    'user': 'your_username',
    'password': 'your_password'
}

# Crear una instancia de DBConnector
db = DBConnector(**DB_CONFIG)

# Ejemplo de uso
taxis = db.fetch_data("SELECT * FROM taxis")
for taxi in taxis:
    print(taxi)

# No olvides cerrar la conexión cuando hayas terminado
db.close_connection()