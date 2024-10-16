@echo off
REM Iniciar Zookeeper
set KAFKA_HOME=C:\kafka
%KAFKA_HOME%\bin\windows\zookeeper-server-start.bat %KAFKA_HOME%\config\zookeeper.properties