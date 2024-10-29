FROM python:3.9-slim
WORKDIR /app

# Instalar dependencias
COPY taxi/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copiar código
COPY common ./common
COPY taxi ./taxi

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV TAXI_PORT=50053

# Exponer puerto
EXPOSE ${TAXI_PORT}

# Comando de inicio
CMD ["python", "-u", "taxi/EC_DE.py", \
     "--central-host", "${CENTRAL_HOST}", \
     "--central-port", "50051", \
     "--kafka-host", "${KAFKA_HOST}", \
     "--kafka-port", "9092", \
     "--taxi-id", "${TAXI_ID:-1}", \
     "--taxi-port", "${TAXI_PORT}"]