#!/bin/bash

# Función para obtener la IP del host
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

# Obtener la IP del host
HOST_IP=$(get_host_ip)

# Configurar el tipo de nodo
echo "Seleccione el tipo de nodo:"
echo "1) Servidor Central"
echo "2) Nodo de Clientes"
echo "3) Nodo de Taxis"
read -p "Selección (1-3): " node_type

# Solicitar IP del servidor central si no es el servidor central
if [ "$node_type" != "1" ]; then
    read -p "Ingrese la IP del servidor central: " CENTRAL_IP
else
    CENTRAL_IP=$HOST_IP
fi

# Exportar variables de entorno
export HOST_IP
export CENTRAL_IP

# Detener contenedores existentes
docker-compose down

# Seleccionar el archivo docker-compose correcto y arrancar servicios
case $node_type in
    1)
        echo "Iniciando servidor central en $HOST_IP..."
        docker-compose -f docker-compose.pc2.yml up -d
        ;;
    2)
        echo "Iniciando nodo de clientes, conectando a central en $CENTRAL_IP..."
        docker-compose -f docker-compose.pc1.yml up -d
        ;;
    3)
        echo "Iniciando nodo de taxis, conectando a central en $CENTRAL_IP..."
        docker-compose -f docker-compose.pc3.yml up -d
        ;;
    *)
        echo "Opción no válida"
        exit 1
        ;;
esac

# Mostrar logs
docker-compose logs -f