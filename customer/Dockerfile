# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the customer application code into the container
COPY EC_Customer.py .
COPY destinations.txt .

# Set environment variables
ENV KAFKA_BROKER kafka:9092
ENV CUSTOMER_ID 1

# Run the customer application when the container launches
CMD ["python", "EC_Customer.py"]