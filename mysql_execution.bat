@echo off
set MYSQL_USER=root
set MYSQL_PASSWORD=JAHEDE11
set PROJECT_PATH=C:\Users\ramaj\OneDrive - UNIVERSIDAD ALICANTE\PROYECTOS\EasyCab

mysql -u %MYSQL_USER% -p%MYSQL_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS easycab;"
mysql -u %MYSQL_USER% -p%MYSQL_PASSWORD% easycab < %PROJECT_PATH%\core\database\schema.sql
mysql -u %MYSQL_USER% -p%MYSQL_PASSWORD% easycab < %PROJECT_PATH%\core\database\initial_data.sql

echo Base de datos inicializada correctamente.