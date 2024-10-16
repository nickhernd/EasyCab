def update_map(mapa, actualizacion):
    """
    Actualiza el mapa con la nueva información, manejando la geometría esférica.
    """
    x, y = actualizacion['position']
    x = x % len(mapa[0])  # Maneja el wrap-around horizontal
    y = y % len(mapa)     # Maneja el wrap-around vertical
    
    if 'taxi_id' in actualizacion:
        mapa[y][x] = str(actualizacion['taxi_id'])
    elif 'location_id' in actualizacion:
        mapa[y][x] = actualizacion['location_id']
    else:
        raise ValueError("La actualización debe contener 'taxi_id' o 'location_id'")
    return mapa

def create_empty_map(tamaño):
    """
    Crea un mapa vacío con el tamaño especificado.
    """
    return [[' ' for _ in range(tamaño)] for _ in range(tamaño)]

def calculate_distance(pos1, pos2, map_size):
    """
    Calcula la distancia más corta entre dos puntos en un mapa esférico.
    """
    dx = min((pos1[0] - pos2[0]) % map_size, (pos2[0] - pos1[0]) % map_size)
    dy = min((pos1[1] - pos2[1]) % map_size, (pos2[1] - pos1[1]) % map_size)
    return dx + dy

def get_current_map():
    """
    Obtiene el mapa actual.
    """
    return create_empty_map(20)  # Asumimos un tamaño de mapa de 20x20