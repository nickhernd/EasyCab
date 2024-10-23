#!/bin/bash

# Obtener la IP del host
get_host_ip() {
    # En Linux
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        ip addr show | grep -w inet | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1 | head -n1
    # En macOS
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        ipconfig getifaddr en0
    # En Windows con Git Bash
    else
        ipconfig | grep -m 1 "IPv4" | awk '{print $NF}'
    fi
}

# Configurar acceso X11 para GUI
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xhost +local:docker
fi

# Obtener IP del host
HOST_IP=$(get_host_ip)
export HOST_IP

# Detener contenedores existentes
docker-compose -f docker-compose.pc2.yml down

# Iniciar servicios
docker-compose -f docker-compose.pc2.yml up -d

# Mostrar logs
docker-compose -f docker-compose.pc2.yml logs -f