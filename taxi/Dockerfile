# Dockerfile para EC_DE (Digital Engine)
FROM python:3.9-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar los archivos de la aplicación
COPY taxi /app/taxi
COPY common /app/common

# Instalar las dependencias
RUN pip install -r /app/taxi/requirements.txt

# Exponer el puerto de EC_DE
EXPOSE 50053

# Comando de ejecución
CMD ["python", "/app/taxi/EC_DE.py", "${CENTRAL_IP}", "50051", "${KAFKA_IP}", "9092", "${TAXI_ID}"]
