#!/bin/bash

# Configuración de red para EasyCab
# Ejecutar en cada PC con los valores correspondientes

# Variables
PC1_IP="192.168.1.100"  # Ejemplo - ajustar según tu red
PC2_IP="192.168.1.101"
PC3_IP="192.168.1.102"

# Configurar rutas si es necesario
sudo ip route add $PC1_IP/32 dev eth0  # Ajustar la interfaz según tu configuración
sudo ip route add $PC2_IP/32 dev eth0
sudo ip route add $PC3_IP/32 dev eth0

# Abrir puertos necesarios en el firewall
sudo ufw allow 2181/tcp  # Zookeeper
sudo ufw allow 9092/tcp  # Kafka
sudo ufw allow 50051/tcp # Central

# Verificar conectividad
echo "Verificando conectividad..."
ping -c 3 $PC1_IP
ping -c 3 $PC2_IP
ping -c 3 $PC3_IP