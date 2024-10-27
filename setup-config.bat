@echo off
echo Configuracion de EasyCab
echo ----------------------
echo 1. PC1 (Central + Kafka)
echo 2. PC2 (Taxis)
echo 3. PC3 (Clientes)
echo.

set /p option="Selecciona el tipo de PC (1-3): "
set /p central_ip="Introduce la IP del PC1 (Central): "

if "%option%"=="1" (
    echo Configurando PC1 (Central + Kafka)...
    set KAFKA_HOST=%central_ip%
    echo KAFKA_HOST=%central_ip% > .env
    
    echo Iniciando servicios...
    docker compose up central kafka zookeeper

) else if "%option%"=="2" (
    echo Configurando PC2 (Taxis)...
    echo KAFKA_HOST=%central_ip% > .env
    echo CENTRAL_HOST=%central_ip% >> .env
    
    echo Iniciando servicios...
    docker compose up taxi

) else if "%option%"=="3" (
    echo Configurando PC3 (Clientes)...
    echo KAFKA_HOST=%central_ip% > .env
    echo CENTRAL_HOST=%central_ip% >> .env
    
    echo Iniciando servicios...
    docker compose up customer
)

pause