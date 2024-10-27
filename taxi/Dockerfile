FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias
COPY taxi/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copiar código
COPY common ./common
COPY taxi ./taxi

# Variable de entorno para debug
ENV PYTHONUNBUFFERED=1

# Comando de inicio
CMD ["python", "-u", "taxi/EC_DE.py", "1", "5000"]