FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias
COPY central/requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copiar código fuente
COPY common common/
COPY central central/
COPY data data/

# Comando para ejecutar la aplicación
CMD ["python", "-u", "central/EC_Central.py"]