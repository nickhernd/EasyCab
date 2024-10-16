@echo off
REM Iniciar Kafka
set KAFKA_HOME=C:\kafka
%KAFKA_HOME%\bin\windows\kafka-server-start.bat %KAFKA_HOME%\config\server.properties