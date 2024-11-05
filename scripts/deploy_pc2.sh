#!/bin/bash
# Script de despliegue para PC2 (CTC)

# Cargar variables de entorno
source .env

# Iniciar EC_CTC
echo "Iniciando EC_CTC..."
python EC_CTC/src/main.py $CTC_PORT $OPENWEATHER_API_KEY