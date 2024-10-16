@echo off
echo Desplegando componentes...

REM Usa la IP de tu máquina (192.168.1.100 en este caso)
set KAFKA_IP=localhost
set MYSQL_IP=localhost

REM Desplegar Zookeeper y Kafka
docker-compose up -d zookeeper kafka
docker-compose exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092

docker-compose up -d ec_central

REM Iniciar GUI localmente
start cmd /k "python EC_GUI.py %KAFKA_IP%:9092"

echo Despliegue completado.

pause >nul