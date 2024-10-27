@echo off
echo Configurando variables de entorno...
set KAFKA_HOST=localhost

echo Deteniendo contenedores anteriores...
docker compose down

echo Construyendo imagenes...
docker compose build

echo Iniciando el sistema...
docker compose up

pause