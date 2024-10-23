import json
import os

class LocationsManager:
    def __init__(self, json_path="locations.json"):
        self.json_path = json_path
        self.locations = {}
        self.load_locations()

    def load_locations(self):
        """Carga las ubicaciones desde el archivo JSON"""
        try:
            with open(self.json_path, 'r') as file:
                data = json.load(file)
                for loc in data.get('locations', []):
                    loc_id = loc['Id']
                    x, y = map(int, loc['POS'].split(','))
                    self.locations[loc_id] = {
                        'id': loc_id,
                        'x': x,
                        'y': y
                    }
                print(f"Ubicaciones cargadas: {self.locations}")
        except FileNotFoundError:
            print(f"Archivo de ubicaciones no encontrado: {self.json_path}")
            raise
        except Exception as e:
            print(f"Error cargando ubicaciones: {e}")
            raise

    def get_location_coordinates(self, location_id):
        """Obtiene las coordenadas de una ubicación"""
        if location_id in self.locations:
            loc = self.locations[location_id]
            return [loc['x'], loc['y']]
        return None

    def get_all_locations(self):
        """Devuelve todas las ubicaciones"""
        return self.locations

    def exists(self, location_id):
        """Verifica si existe una ubicación"""
        return location_id in self.locations