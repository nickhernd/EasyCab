# Dockerfile para EC_Central
FROM python:3.9-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar los archivos de la aplicación
COPY central /app/central
COPY common /app/common
COPY data /app/data

# Instalar las dependencias
RUN pip install -r /app/central/requirements.txt

# Variables de entorno para la base de datos
ENV DB_HOST=mysql
ENV DB_PORT=3306
ENV DB_USER=easycab
ENV DB_PASSWORD=easycab123
ENV DB_NAME=easycab

# Exponer el puerto de EC_Central
EXPOSE 50051

# Comando de ejecución
CMD ["python", "/app/central/EC_Central.py", "0.0.0.0", "50051", "${KAFKA_HOST}", "9092", "${DB_HOST}", "${DB_PORT}", "${DB_USER}", "${DB_PASSWORD}", "${DB_NAME}"]
