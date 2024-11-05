#!/bin/bash
# Script para generar certificados SSL para EC_Registry

# Generar clave privada
openssl genrsa -out key.pem 2048

# Generar certificado auto-firmado
openssl req -new -x509 -key key.pem -out cert.pem -days 365 \
    -subj "/C=ES/ST=Alicante/L=Alicante/O=UA/OU=EPS/CN=ec_registry"

# Ajustar permisos
chmod 400 key.pem
chmod 444 cert.pem