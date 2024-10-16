@echo off
echo Desplegando nuevo taxi...

set TAXI_ID=%1
if "%TAXI_ID%"=="" (
    echo Por favor, proporciona un ID para el nuevo taxi.
    exit /b 1
)

docker-compose run -d --name ec_de_%TAXI_ID% ec_de python EC_DE.py kafka:9092 ec_central:8000 %TAXI_ID%

echo Taxi %TAXI_ID% desplegado.

pause >nul