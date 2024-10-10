def create_empty_map(size=20):
    """
    Crea un mapa vacío de tamaño especificado.
    """
    return [[' ' for _ in range(size)] for _ in range(size)]

def update_map(map, update):
    """
    Actualiza el mapa con la nueva información.
    """
    if 'taxi_id' in update:
        x, y = update['position']
        map[y][x] = str(update['taxi_id'])
    elif 'location_id' in update:
        x, y = update['position']
        map[y][x] = update['location_id']
    return map

def get_current_map(map):
    """
    Retorna una representación en string del mapa actual.
    """
    return '\n'.join([''.join(row) for row in map])

def load_map_from_file(filename):
    """
    Carga el mapa inicial desde un archivo.
    """
    with open(filename, 'r') as f:
        return [list(line.strip()) for line in f]

def save_map_to_file(map, filename):
    """
    Guarda el mapa actual en un archivo.
    """
    with open(filename, 'w') as f:
        for row in map:
            f.write(''.join(row) + '\n')