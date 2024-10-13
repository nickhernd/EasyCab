def update_map(map, update):
    """
    Actualiza el mapa con la nueva información.
    """
    if 'taxi_id' in update:
        x, y = update['position']
        if 0 <= x < len(map[0]) and 0 <= y < len(map):
            map[y][x] = str(update['taxi_id'])
        else:
            raise ValueError(f"Posición inválida: ({x}, {y})")
    elif 'location_id' in update:
        x, y = update['position']
        if 0 <= x < len(map[0]) and 0 <= y < len(map):
            map[y][x] = update['location_id']
        else:
            raise ValueError(f"Posición inválida: ({x}, {y})")
    return map