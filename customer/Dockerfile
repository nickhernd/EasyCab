# Dockerfile para EC_Customer
FROM python:3.9-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar los archivos de la aplicación
COPY customer /app/customer
COPY common /app/common
COPY data /app/data

# Instalar las dependencias
RUN pip install -r /app/customer/requirements.txt

# Exponer el puerto de EC_Customer si es necesario
EXPOSE 50052

# Comando de ejecución
CMD ["python", "/app/customer/EC_Customer.py", "${CENTRAL_IP}", "50051", "${KAFKA_IP}", "9092", "${CUSTOMER_ID}"]
