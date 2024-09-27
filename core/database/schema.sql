CREATE DATABASE IF NOT EXISTS easycab;
USE easycab;

-- Tabla de taxis
CREATE TABLE IF NOT EXISTS taxis (
    id INT PRIMARY KEY,
    status ENUM('AVAILABLE', 'BUSY', 'OFFLINE') NOT NULL DEFAULT 'OFFLINE',
    position_x INT NOT NULL,
    position_y INT NOT NULL
);

-- Tabla de localizaciones
CREATE TABLE IF NOT EXISTS locations (
    id CHAR(1) PRIMARY KEY,
    position_x INT NOT NULL,
    position_y INT NOT NULL
);

-- Tabla de servicios
CREATE TABLE IF NOT EXISTS services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    taxi_id INT,
    customer_id VARCHAR(50),
    start_location CHAR(1),
    end_location CHAR(1),
    status ENUM('REQUESTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELED') NOT NULL DEFAULT 'REQUESTED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (taxi_id) REFERENCES taxis(id),
    FOREIGN KEY (start_location) REFERENCES locations(id),
    FOREIGN KEY (end_location) REFERENCES locations(id)
);