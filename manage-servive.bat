@echo off
echo Gestion de Servicios EasyCab
echo ---------------------------
echo 1. Iniciar servicios
echo 2. Detener servicios
echo 3. Ver logs
echo 4. Reiniciar servicios
echo 5. Ver estado de servicios
echo.

set /p option="Selecciona una opcion (1-5): "

if "%option%"=="1" (
    docker compose up -d
) else if "%option%"=="2" (
    docker compose down
) else if "%option%"=="3" (
    echo Selecciona el servicio:
    echo 1. Todos
    echo 2. Central
    echo 3. Taxi
    echo 4. Customer
    echo 5. Kafka
    set /p service="Opcion: "
    
    if "%service%"=="1" docker compose logs --tail=100 -f
    if "%service%"=="2" docker compose logs --tail=100 -f central
    if "%service%"=="3" docker compose logs --tail=100 -f taxi
    if "%service%"=="4" docker compose logs --tail=100 -f customer
    if "%service%"=="5" docker compose logs --tail=100 -f kafka
) else if "%option%"=="4" (
    docker compose down
    docker compose up -d
) else if "%option%"=="5" (
    docker compose ps
)

pause