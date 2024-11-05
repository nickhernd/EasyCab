#!/bin/bash
# Script de despliegue para PC1 (Central, Registry, Kafka)

# Cargar variables de entorno
source .env

# Iniciar Kafka y Zookeeper
echo "Iniciando Kafka y Zookeeper..."
docker-compose -f kafka-compose.yml up -d

# Esperar a que Kafka esté listo
echo "Esperando que Kafka esté listo..."
sleep 30

# Iniciar EC_Central
echo "Iniciando EC_Central..."
python EC_Central/src/main.py $CENTRAL_PORT $KAFKA_BOOTSTRAP_SERVERS

# Iniciar EC_Registry
echo "Iniciando EC_Registry..."
cd EC_Registry
./config/generate_ssl.sh
python src/main.py $REGISTRY_PORT