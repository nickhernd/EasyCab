import os

# Kafka Configuration
KAFKA_HOST = os.getenv('KAFKA_HOST', '192.168.56.123')
KAFKA_PORT = os.getenv('KAFKA_PORT', '9092')
KAFKA_BOOTSTRAP_SERVERS = f'{KAFKA_HOST}:{KAFKA_PORT}'

# Kafka Topics
TOPICS = {
    'TAXI_POSITIONS': 'taxi_positions',
    'CUSTOMER_REQUESTS': 'customer_requests',
    'TAXI_STATUS': 'taxi_status',
    'MAP_UPDATES': 'map_updates',
    'SENSOR_DATA': 'sensor_data'
}

# Map Configuration
MAP_SIZE = 20

# Central Server Configuration
CENTRAL_HOST = os.getenv('CENTRAL_HOST', '192.168.56.123')
CENTRAL_PORT = int(os.getenv('CENTRAL_PORT', '50051'))

# Colors for terminal output
COLORS = {
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'BLUE': '\033[94m',
    'YELLOW': '\033[93m',
    'END': '\033[0m'
}

# Service States
SERVICE_STATES = {
    'PENDING': 'PENDING',
    'ACCEPTED': 'ACCEPTED',
    'IN_PROGRESS': 'IN_PROGRESS',
    'COMPLETED': 'COMPLETED',
    'REJECTED': 'REJECTED'
}

# Taxi States
TAXI_STATES = {
    'AVAILABLE': 'AVAILABLE',
    'BUSY': 'BUSY',
    'STOPPED': 'STOPPED',
    'OFFLINE': 'OFFLINE'
}