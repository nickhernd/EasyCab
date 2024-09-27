import mysql.connector
from mysql.connector import Error

class DBConnector:
    def __init__(self, host, database, user, password):
        self.connection = None
        try:
            self.connection = mysql.connector.connect(
                host=host,
                database=database,
                user=user,
                password=password
            )
            print("Database connection successful")
        except Error as e:
            print(f"Error connecting to database: {e}")

    def execute_query(self, query, params=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            self.connection.commit()
            print("Query executed successfully")
            return cursor
        except Error as e:
            print(f"Error executing query: {e}")
            return None
        finally:
            cursor.close()

    def fetch_data(self, query, params=None):
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching data: {e}")
            return None
        finally:
            cursor.close()

    def insert_data(self, table, data):
        placeholders = ', '.join(['%s'] * len(data))
        columns = ', '.join(data.keys())
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute_query(query, tuple(data.values()))

    def update_data(self, table, data, condition):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        return self.execute_query(query, tuple(data.values()))

    def delete_data(self, table, condition):
        query = f"DELETE FROM {table} WHERE {condition}"
        return self.execute_query(query)

    def close_connection(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed")