from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from common.config import MAP_SIZE, COLORS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Location:
    id: str
    x: int
    y: int

@dataclass
class Taxi:
    id: int
    x: int
    y: int
    state: str
    destination: Optional[Tuple[int, int]] = None

class MapManager:
    def __init__(self):
        self.size = MAP_SIZE
        self.grid = [[None for _ in range(self.size)] for _ in range(self.size)]
        self.locations: Dict[str, Location] = {}
        self.taxis: Dict[int, Taxi] = {}

    def add_location(self, location_id: str, x: int, y: int) -> bool:
        """Añadir una nueva localización al mapa"""
        if not self.is_valid_position(x, y) or self.grid[y][x] is not None:
            return False
        
        location = Location(location_id, x, y)
        self.locations[location_id] = location
        self.grid[y][x] = ('location', location_id)
        logger.info(f"Localización {location_id} añadida en ({x}, {y})")
        return True

    def add_taxi(self, taxi_id: int, x: int, y: int, state: str) -> bool:
        """Añadir o actualizar la posición de un taxi"""
        if not self.is_valid_position(x, y):
            return False

        if taxi_id in self.taxis:
            old_taxi = self.taxis[taxi_id]
            self.grid[old_taxi.y][old_taxi.x] = None

        taxi = Taxi(taxi_id, x, y, state)
        self.taxis[taxi_id] = taxi
        self.grid[y][x] = ('taxi', taxi_id)
        logger.info(f"Taxi {taxi_id} añadido/actualizado en ({x}, {y})")
        return True

    def remove_taxi(self, taxi_id: int) -> bool:
        """Eliminar un taxi del mapa"""
        if taxi_id in self.taxis:
            taxi = self.taxis[taxi_id]
            self.grid[taxi.y][taxi.x] = None
            del self.taxis[taxi_id]
            logger.info(f"Taxi {taxi_id} eliminado del mapa")
            return True
        return False

    def move_taxi(self, taxi_id: int, new_x: int, new_y: int) -> bool:
        """Mover un taxi a una nueva posición"""
        if not self.is_valid_position(new_x, new_y) or taxi_id not in self.taxis:
            return False

        taxi = self.taxis[taxi_id]
        self.grid[taxi.y][taxi.x] = None
        taxi.x, taxi.y = new_x, new_y
        self.grid[new_y][new_x] = ('taxi', taxi_id)
        logger.info(f"Taxi {taxi_id} movido a ({new_x}, {new_y})")
        return True

    def is_valid_position(self, x: int, y: int) -> bool:
        """Verificar si una posición está dentro de los límites del mapa"""
        return 0 <= x < self.size and 0 <= y < self.size

    def print_map(self) -> None:
        """Imprimir el estado actual del mapa"""
        print("\n=== Estado actual del mapa ===")
        for y in range(self.size):
            row = []
            for x in range(self.size):
                cell = self.grid[y][x]
                if cell is None:
                    row.append('.')
                elif cell[0] == 'taxi':
                    taxi = self.taxis[cell[1]]
                    color = COLORS['GREEN'] if taxi.state == 'BUSY' else COLORS['RED']
                    row.append(f"{color}{taxi.id:02d}{COLORS['END']}")
                elif cell[0] == 'location':
                    row.append(f"{COLORS['BLUE']}{cell[1]}{COLORS['END']}")
            print(' '.join(row))
        print("===========================\n")