@echo off
title EasyCab Startup Script

REM Configuración inicial
set PYTHON_CMD=python
set CORE_DIR=core\EC_Central
set TAXI_DIR=taxi\EC_DE
set SENSOR_DIR=taxi\EC_S
set CUSTOMER_DIR=customer
set GUI_DIR=gui

REM Inicia EC_Central (componente principal)
echo Iniciando EC_Central...
start cmd /k %PYTHON_CMD% %CORE_DIR%\EC_Central.py

REM Inicia 3 taxis (simulación de vehículos)
echo Iniciando taxis...
for /l %%i in (1,1,3) do (
    start cmd /k %PYTHON_CMD% %TAXI_DIR%\EC_DE.py --id %%i
)

REM Inicia 3 sensores (simulación de sensores en los taxis)
echo Iniciando sensores...
for /l %%i in (1,1,3) do (
    start cmd /k %PYTHON_CMD% %SENSOR_DIR%\EC_S.py --id %%i
)

REM Inicia 2 clientes (simulación de usuarios)
echo Iniciando clientes...
for /l %%i in (1,1,2) do (
    start cmd /k %PYTHON_CMD% %CUSTOMER_DIR%\EC_Customer.py --id %%i
)

REM Inicia la GUI (interfaz gráfica del sistema)
echo Iniciando GUI...
start cmd /k %PYTHON_CMD% %GUI_DIR%\EC_GUI.py

echo Sistema EasyCab iniciado completamente.
echo Presione cualquier tecla para detener todos los componentes.
pause > nul

REM Detiene todos los procesos de Python (cierre del sistema)
echo Deteniendo el sistema EasyCab...
taskkill /F /IM python.exe
echo Sistema EasyCab detenido.