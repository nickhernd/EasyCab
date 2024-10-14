def update_map(mapa, actualizacion):
    """
    Actualiza el mapa con la nueva información.
    """
    x, y = actualizacion['position']
    if 0 <= x < len(mapa[0]) and 0 <= y < len(mapa):
        if 'taxi_id' in actualizacion:
            mapa[y][x] = str(actualizacion['taxi_id'])
        elif 'location_id' in actualizacion:
            mapa[y][x] = actualizacion['location_id']
        else:
            raise ValueError("La actualización debe contener 'taxi_id' o 'location_id'")
    else:
        raise ValueError(f"Posición inválida: ({x}, {y})")
    return mapa

def create_empty_map(tamaño):
    """
    Crea un mapa vacío con el tamaño especificado.
    """
    return [[' ' for _ in range(tamaño)] for _ in range(tamaño)]