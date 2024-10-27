#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Iniciando prueba local de Docker para EasyCab...${NC}"

# Detener contenedores anteriores si existen
echo -e "\n${GREEN}Deteniendo contenedores anteriores...${NC}"
docker-compose down
docker-compose -f docker-compose.kafka.yml down

# Configurar variables de entorno para prueba local
export KAFKA_HOST=localhost
export CENTRAL_HOST=localhost

# Iniciar Kafka
echo -e "\n${GREEN}Iniciando Kafka...${NC}"
docker-compose -f docker-compose.kafka.yml up -d

# Esperar a que Kafka esté listo
echo "Esperando a que Kafka esté listo..."
sleep 20

# Iniciar los servicios
echo -e "\n${GREEN}Iniciando servicios...${NC}"
docker-compose up --build

# Función para limpiar al salir
cleanup() {
    echo -e "\n${GREEN}Deteniendo servicios...${NC}"
    docker-compose down
    docker-compose -f docker-compose.kafka.yml down
}

# Registrar función de limpieza
trap cleanup EXIT

# Mantener script ejecutándose
echo -e "\n${GREEN}Servicios iniciados. Presiona Ctrl+C para detener...${NC}"
tail -f /dev/null