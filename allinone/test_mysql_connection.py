import mysql.connector

def test_mysql_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="JAHEDE11",
            database="easycab"
        )
        
        if connection.is_connected():
            print("Conexión exitosa a MySQL")
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM taxis")
            result = cursor.fetchall()
            print("Taxis en la base de datos:")
            for row in result:
                print(row)
    except mysql.connector.Error as e:
        print(f"Error al conectar a MySQL: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexión a MySQL cerrada")

if __name__ == "__main__":
    test_mysql_connection()