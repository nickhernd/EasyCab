FROM python:3.9-slim
WORKDIR /app

# Instalar dependencias
COPY central/requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copiar código fuente
COPY common common/
COPY central central/
COPY data data/

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV CENTRAL_PORT=50051

# Exponer puerto
EXPOSE ${CENTRAL_PORT}

# Comando para ejecutar la aplicación
CMD ["python", "-u", "central/EC_Central.py", \
     "--host", "0.0.0.0", \
     "--port", "${CENTRAL_PORT}", \
     "--kafka-host", "${KAFKA_HOST}", \
     "--kafka-port", "9092"]