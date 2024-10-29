FROM python:3.9-slim
WORKDIR /app

# Instalar dependencias
COPY customer/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copiar código y datos
COPY common ./common
COPY customer ./customer
COPY data ./data

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV CUSTOMER_PORT=50052

# Exponer puerto
EXPOSE ${CUSTOMER_PORT}

# Comando de inicio
CMD ["python", "-u", "customer/EC_Customer.py", \
     "--central-host", "${CENTRAL_HOST}", \
     "--central-port", "50051", \
     "--kafka-host", "${KAFKA_HOST}", \
     "--kafka-port", "9092", \
     "--customer-id", "${CUSTOMER_ID:-1}"]