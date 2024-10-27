FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias
COPY customer/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copiar código y datos
COPY common ./common
COPY customer ./customer
COPY data ./data

# Variable de entorno para debug
ENV PYTHONUNBUFFERED=1

# Comando de inicio
CMD ["python", "-u", "customer/EC_Customer.py", "cliente1", "data/EC_Requests.json"]