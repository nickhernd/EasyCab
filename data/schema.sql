-- Crear base de datos
CREATE DATABASE IF NOT EXISTS easycab;
USE easycab;

-- Tabla de localizaciones (puntos de interés en el mapa)
CREATE TABLE locations (
    id VARCHAR(1) PRIMARY KEY,
    coord_x INT NOT NULL,
    coord_y INT NOT NULL,
    description VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (coord_x BETWEEN 1 AND 20),
    CHECK (coord_y BETWEEN 1 AND 20)
);

-- Tabla de taxis
CREATE TABLE taxis (
    id INT PRIMARY KEY,
    current_x INT NOT NULL,
    current_y INT NOT NULL,
    status ENUM('AVAILABLE', 'BUSY', 'OFFLINE', 'STOPPED') NOT NULL DEFAULT 'OFFLINE',
    last_status_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (current_x BETWEEN 1 AND 20),
    CHECK (current_y BETWEEN 1 AND 20)
);

-- Tabla de clientes
CREATE TABLE customers (
    id VARCHAR(1) PRIMARY KEY,
    last_service_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_services INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de servicios
CREATE TABLE services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(1),
    taxi_id INT,
    pickup_x INT NOT NULL,
    pickup_y INT NOT NULL,
    destination_id VARCHAR(1),
    status ENUM('REQUESTED', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED') NOT NULL,
    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acceptance_time TIMESTAMP NULL,
    pickup_time TIMESTAMP NULL,
    completion_time TIMESTAMP NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (taxi_id) REFERENCES taxis(id),
    FOREIGN KEY (destination_id) REFERENCES locations(id),
    CHECK (pickup_x BETWEEN 1 AND 20),
    CHECK (pickup_y BETWEEN 1 AND 20)
);

-- Tabla de movimientos de taxis
CREATE TABLE taxi_movements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    taxi_id INT,
    service_id INT NULL,
    from_x INT NOT NULL,
    from_y INT NOT NULL,
    to_x INT NOT NULL,
    to_y INT NOT NULL,
    movement_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (taxi_id) REFERENCES taxis(id),
    FOREIGN KEY (service_id) REFERENCES services(id),
    CHECK (from_x BETWEEN 1 AND 20),
    CHECK (from_y BETWEEN 1 AND 20),
    CHECK (to_x BETWEEN 1 AND 20),
    CHECK (to_y BETWEEN 1 AND 20)
);

-- Tabla de incidencias de sensores
CREATE TABLE sensor_incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    taxi_id INT,
    service_id INT NULL,
    incident_type VARCHAR(50) NOT NULL,
    coord_x INT NOT NULL,
    coord_y INT NOT NULL,
    incident_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolution_time TIMESTAMP NULL,
    FOREIGN KEY (taxi_id) REFERENCES taxis(id),
    FOREIGN KEY (service_id) REFERENCES services(id),
    CHECK (coord_x BETWEEN 1 AND 20),
    CHECK (coord_y BETWEEN 1 AND 20)
);