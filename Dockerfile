FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY EC_Central.py .
COPY EC_Customer.py .
COPY EC_DE.py .
COPY test_client.py .
COPY test_kafka.py .