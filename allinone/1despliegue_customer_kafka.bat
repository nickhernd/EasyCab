@echo off
echo Desplegando componentes...

REM Asegurar de que la red de Docker exista
docker network create -d bridge easycab_network
::docker network create easycab_network || true

REM Desplegar Zookeeper y Kafka
docker-compose up -d zookeeper kafka
docker-compose exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092

REM Desplegar MySQL
docker-compose up -d mysql


REM Desplegar clientes y otros componentes
docker-compose up -d ec_customer_1 ec_customer_2

echo Despliegue completado.
:: IP Máquina
@echo off
set ip_address_string="IPv4 Address"
rem Uncomment the following line when using older versions of Windows without IPv6 support (by removing "rem")
rem set ip_address_string="IP Address"
echo Network Connection Test
for /f "usebackq tokens=2 delims=:" %%f in (`ipconfig ^| findstr /c:%ip_address_string%`) do echo Your IP Address is: %%f

pause >nul
