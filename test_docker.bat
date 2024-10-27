@echo off
echo Limpiando contenedores anteriores...
docker-compose down

echo Construyendo imagenes...
docker-compose build

echo Iniciando servicio central...
docker-compose up central
pause