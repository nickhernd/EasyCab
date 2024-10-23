FROM python:3.9-slim

# Instalar dependencias del sistema incluyendo tkinter
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    build-essential \
    librdkafka-dev \
    python3-tk \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de la aplicación
WORKDIR /app

# Copiar requirements.txt
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY *.py .
COPY locations.json .

# El comando se especificará en docker-compose
CMD ["python"]