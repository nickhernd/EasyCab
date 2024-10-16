#!/bin/bash

# Función para iniciar componentes
iniciar_componente() {
    echo "Iniciando $1..."
    python "$2" "$3" &
    sleep 1  # Espera 1 segundo para asegurar que el componente se inicie correctamente
}

# Inicia el servidor central
iniciar_componente "Servidor Central" "core/EC_Central.py"

# Inicia 3 taxis
for id in {1..3}; do
    iniciar_componente "Taxi $id" "taxi/EC_DE.py" "--id $id"
done

# Inicia 3 sensores
for id in {1..3}; do
    iniciar_componente "Sensor $id" "taxi/EC_S.py" "--id $id"
done

# Inicia 2 clientes
for id in {1..2}; do
    iniciar_componente "Cliente $id" "customer/EC_Customer.py" "--id $id"
done

# Inicia la interfaz gráfica de usuario (GUI)
iniciar_componente "GUI" "gui/EC_GUI.py"

echo "Sistema EasyCab iniciado. Presione cualquier tecla para detener todos los componentes."
read -n 1 -s  # Espera a que el usuario presione una tecla

# Detiene todos los procesos de Python relacionados con EasyCab
echo "Deteniendo el sistema EasyCab..."
pkill -f "python.*EC_"

echo "Sistema EasyCab detenido."