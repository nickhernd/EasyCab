#!/bin/bash

# Configuración específica para cada PC
PC1_IP="[IP_DE_TU_WINDOWS]"  # Windows - Kafka + Customers
PC2_IP="[IP_DE_LINUX_1]"     # Linux 1 - Central
PC3_IP="[IP_DE_LINUX_2]"     # Linux 2 - Taxis

# Detectar en qué PC estamos ejecutando el script
CURRENT_IP=$(hostname -I | awk '{print $1}')
echo "Ejecutando en máquina con IP: $CURRENT_IP"

# Configurar Docker
if [ ! -x "$(command -v docker)" ]; then
    echo "Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker instalado. Por favor, reinicie la sesión."
fi

# Configurar puertos según el rol
case $CURRENT_IP in
    $PC1_IP)
        echo "Configurando PC1 (Kafka + Customers)..."
        sudo ufw allow 2181/tcp  # Zookeeper
        sudo ufw allow 9092/tcp  # Kafka
        ;;
    $PC2_IP)
        echo "Configurando PC2 (Central)..."
        sudo ufw allow 50051/tcp # Central
        ;;
    $PC3_IP)
        echo "Configurando PC3 (Taxis)..."
        # Añadir puertos específicos para taxis si es necesario
        ;;
esac

# Verificar conectividad
echo "Verificando conectividad..."
ping -c 3 $PC1_IP
ping -c 3 $PC2_IP
ping -c 3 $PC3_IP