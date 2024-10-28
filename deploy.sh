#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}EasyCab Deployment Script${NC}"

# Función para verificar dependencias
check_dependencies() {
    echo -e "${GREEN}Verificando dependencias...${NC}"
    
    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python3 no encontrado. Instalando...${NC}"
        if [ -f /etc/debian_version ]; then
            sudo apt update && sudo apt install -y python3 python3-pip
        elif [ -f /etc/fedora-release ]; then
            sudo dnf install -y python3 python3-pip
        fi
    fi
    
    # Instalar dependencias Python
    pip3 install kafka-python
}

# Función para configurar red
setup_network() {
    echo -e "${GREEN}Configurando red...${NC}"
    echo "IP actual:"
    ip addr show
    
    echo -e "${GREEN}Probando conectividad con central...${NC}"
    ping -c 3 $CENTRAL_IP
}

# Función para iniciar componentes
start_component() {
    case $1 in
        "central")
            echo -e "${GREEN}Iniciando Central...${NC}"
            python3 easycab_launcher.py central
            ;;
        "taxi")
            echo -e "${GREEN}Iniciando Taxi...${NC}"
            python3 easycab_launcher.py taxi $CENTRAL_IP
            ;;
        "customer")
            echo -e "${GREEN}Iniciando Cliente...${NC}"
            python3 easycab_launcher.py customer $CENTRAL_IP
            ;;
        *)
            echo -e "${RED}Componente desconocido${NC}"
            ;;
    esac
}

# Main
if [ "$#" -ne 1 ]; then
    echo "Uso: $0 [central|taxi|customer]"
    exit 1
fi

# Cargar configuración
if [ -f config.env ]; then
    source config.env
else
    echo -e "${RED}Archivo config.env no encontrado${NC}"
    exit 1
fi

check_dependencies
setup_network
start_component $1