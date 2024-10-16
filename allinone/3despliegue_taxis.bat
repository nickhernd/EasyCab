@echo off
echo Desplegando componentes...

REM Remplazar IP
set KAFKA_IP=kafka
set CENTRAL_IP=ec_central

REM Asegurar que la red existe
docker network create easycab_network || true

REM Desplegar Zookeeper y Kafka si no están en ejecución
docker-compose up -d zookeeper kafka
timeout /t 10 /nobreak

REM Verificar tópicos de Kafka
docker-compose exec kafka kafka-topics.sh --list --bootstrap-server kafka:9092

REM Construir y ejecutar contenedores Docker para EC_DE
docker-compose up -d --build ec_de_1 ec_de_2

REM Iniciar EC_S en contenedores
docker-compose up -d ec_s_1 ec_s_2

echo Despliegue en PC3 completado (taxis).

pause >nul