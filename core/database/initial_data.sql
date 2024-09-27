USE easycab;

-- Insertar taxis
INSERT INTO taxis (id, status, position_x, position_y) VALUES
(1, 'AVAILABLE', 1, 1),
(2, 'AVAILABLE', 1, 1),
(3, 'AVAILABLE', 1, 1);

-- Insertar localizaciones
INSERT INTO locations (id, position_x, position_y) VALUES
('A', 5, 5),
('B', 10, 10),
('C', 15, 15);

-- Insertar un servicio de ejemplo
INSERT INTO services (taxi_id, customer_id, start_location, end_location, status) VALUES
(1, 'customer1', 'A', 'B', 'REQUESTED');