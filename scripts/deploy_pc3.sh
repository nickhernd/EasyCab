#!/bin/bash
# Script de despliegue para PC3 (Taxis y Clientes)

# Cargar variables de entorno
source .env

# Iniciar Digital Engine y Sensores para cada taxi
for i in {1..3}; do
    echo "Iniciando Taxi $i..."
    python EC_DE/src/main.py $PC1_IP $CENTRAL_PORT $i &
    sleep 2
    python EC_S/src/main.py $PC1_IP $((5001 + $i)) &
done

# Iniciar clientes
for i in {1..2}; do
    echo "Iniciando Cliente $i..."
    python EC_Customer/src/main.py $KAFKA_BOOTSTRAP_SERVERS "customer$i" &
    sleep 2
done