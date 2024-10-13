@echo off
set KAFKA_HOME=C:\kafka
set TOPIC_NAME=easycab

REM Iniciar Zookeeper
start "" %KAFKA_HOME%\bin\windows\zookeeper-server-start.bat %KAFKA_HOME%\config\zookeeper.properties
echo Esperando que Zookeeper se inicie completamente...
timeout /t 10

REM Iniciar Kafka
start "" %KAFKA_HOME%\bin\windows\kafka-server-start.bat %KAFKA_HOME%\config\server.properties
echo Esperando que Kafka se inicie completamente...
timeout /t 10

REM Crear el topic
%KAFKA_HOME%\bin\windows\kafka-topics.bat --create --topic %TOPIC_NAME% --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

echo Kafka y Zookeeper están en ejecución, y el topic '%TOPIC_NAME%' ha sido creado.