from db_connector import DBConnector

DB_CONFIG = {
    'host': 'localhost',
    'database': 'easycab',
    'user': 'nickhernd',
    'password': '123456'
}

db = DBConnector(**DB_CONFIG)

taxis = db.fetch_data("SELECT * FROM taxis")
for taxi in taxis:
    print(taxi)

db.close_connection()