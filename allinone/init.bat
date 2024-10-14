@echo off
REM Inicialización del programa EasyCab

REM Configuración de variables de entorno
set KAFKA_HOME=C:\kafka
set TOPIC_NAME=easycab
set MYSQL_USER=root
set MYSQL_PASSWORD=JAHEDE11
set PROJECT_PATH=C:\Users\ramaj\OneDrive - UNIVERSIDAD ALICANTE\PROYECTOS\EasyCab

REM Iniciar Zookeeper
echo Iniciando Zookeeper...
start "" %KAFKA_HOME%\bin\windows\zookeeper-server-start.bat %KAFKA_HOME%\config\zookeeper.properties
timeout /t 10 /nobreak >nul

REM Iniciar Kafka
echo Iniciando Kafka...
start "" %KAFKA_HOME%\bin\windows\kafka-server-start.bat %KAFKA_HOME%\config\server.properties
timeout /t 10 /nobreak >nul

REM Crear el topic
echo Creando topic '%TOPIC_NAME%'...
%KAFKA_HOME%\bin\windows\kafka-topics.bat --create --topic %TOPIC_NAME% --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
if %ERRORLEVEL% neq 0 (
    echo Error al crear el topic. Saliendo...
    exit /b 1
)

echo Kafka y Zookeeper están en ejecución, y el topic '%TOPIC_NAME%' ha sido creado.

REM Configuración de la base de datos
echo Configurando la base de datos...
mysql -u %MYSQL_USER% -p%MYSQL_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS easycab;"
if %ERRORLEVEL% neq 0 (
    echo Error al crear la base de datos. Saliendo...
    exit /b 1
)

echo Configurando la estructura de la base de datos...
mysql -u %MYSQL_USER% -p%MYSQL_PASSWORD% easycab < %PROJECT_PATH%\core\database\schema.sql
mysql -u %MYSQL_USER% -p%MYSQL_PASSWORD% easycab < %PROJECT_PATH%\core\database\initial_data.sql

REM Iniciar componentes del programa
echo Iniciando componentes del programa...
start cmd /k python central.py
start cmd /k python taxi.py 1
start cmd /k python taxi.py 2
start cmd /k python taxi.py 3
start cmd /k python ec_de.py
start cmd /k python ec_s.py
start cmd /k python gui.py

echo Inicialización completada con éxito.
echo Todos los componentes del programa han sido iniciados.

pause
