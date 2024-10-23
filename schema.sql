-- Crear base de datos
CREATE DATABASE IF NOT EXISTS easycab;
USE easycab;

-- Tabla de taxis
CREATE TABLE IF NOT EXISTS taxis (
    id VARCHAR(10) PRIMARY KEY,
    estado VARCHAR(20) NOT NULL,
    posicion_x INT NOT NULL,
    posicion_y INT NOT NULL,
    ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_ride_id VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE
);

-- Tabla de ubicaciones
CREATE TABLE IF NOT EXISTS locations (
    id_location VARCHAR(10) PRIMARY KEY,
    coordenada_x INT NOT NULL,
    coordenada_y INT NOT NULL
);

-- Tabla de viajes
CREATE TABLE IF NOT EXISTS rides (
    ride_id VARCHAR(20) PRIMARY KEY,
    taxi_id VARCHAR(10),
    customer_id VARCHAR(20),
    pickup_x INT,
    pickup_y INT,
    destination_x INT,
    destination_y INT,
    estado VARCHAR(20),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    FOREIGN KEY (taxi_id) REFERENCES taxis(id)
);

-- Tabla de clientes
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    ultima_solicitud TIMESTAMP
);

-- Tabla de eventos del sistema
CREATE TABLE IF NOT EXISTS system_events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50),
    event_data JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);