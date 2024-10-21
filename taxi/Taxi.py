class Taxi:
    def __init__(self, taxi_id, estado, posicion):

        if 0 <= taxi_id <= 99:
            self.taxi_id = taxi_id
        else:
            raise ValueError("El ID del taxi debe estar entre 0 y 99.")
        
        if estado.lower() in ["verde", "rojo"]:
            self.estado = estado.lower()  # Verde para movimiento, Rojo para parado
        else:
            raise ValueError("El estado del taxi debe ser 'verde' o 'rojo'.")
        
        if 1 <= posicion[0] <= 20 and 1 <= posicion[1] <= 20:
            self.posicion = posicion
        else:
            raise ValueError("Las coordenadas deben estar entre 1 y 20 en ambos ejes.")
    
    def mover(self, nueva_posicion):
        if 1 <= nueva_posicion[0] <= 20 and 1 <= nueva_posicion[1] <= 20:
            self.posicion = nueva_posicion
            self.estado = "verde"  # Cambia el estado a en movimiento
        else:
            raise ValueError("Las coordenadas deben estar entre 1 y 20 en ambos ejes.")
    
    def parar(self):
        self.estado = "rojo"
    
    def __str__(self):
        return f"Taxi {self.taxi_id}: Estado={self.estado}, Posición={self.posicion}"
