-- ============================================
-- PROYECTO FLEETLOGIX
-- ============================================

-- ============================================
-- 1. CREACIÓN DE TABLAS MAESTRAS
-- ============================================

-- Tabla: vehicles
CREATE TABLE vehicles (
   vehicle_id SERIAL PRIMARY KEY,
   license_plate VARCHAR(20) UNIQUE NOT NULL,
   vehicle_type VARCHAR(50) NOT NULL,
   capacity_kg DECIMAL(10,2),
   fuel_type VARCHAR(20),
   acquisition_date DATE,
   status VARCHAR(20) DEFAULT 'active'
);

-- Tabla: drivers
CREATE TABLE drivers (
   driver_id SERIAL PRIMARY KEY,
   employee_code VARCHAR(20) UNIQUE NOT NULL,
   first_name VARCHAR(100) NOT NULL,
   last_name VARCHAR(100) NOT NULL,
   license_number VARCHAR(50) UNIQUE NOT NULL,
   license_expiry DATE,
   phone VARCHAR(20),
   hire_date DATE,
   status VARCHAR(20) DEFAULT 'active'
);

-- Tabla: routes
CREATE TABLE routes (
   route_id SERIAL PRIMARY KEY,
   route_code VARCHAR(20) UNIQUE NOT NULL,
   origin_city VARCHAR(100) NOT NULL,
   destination_city VARCHAR(100) NOT NULL,
   distance_km DECIMAL(10,2),
   estimated_duration_hours DECIMAL(5,2),
   toll_cost DECIMAL(10,2) DEFAULT 0
);

-- ============================================
-- 2. TABLAS TRANSACCIONALES
-- ============================================

-- Tabla: trips
CREATE TABLE trips (
   trip_id SERIAL PRIMARY KEY,
   vehicle_id INTEGER REFERENCES vehicles(vehicle_id),
   driver_id INTEGER REFERENCES drivers(driver_id),
   route_id INTEGER REFERENCES routes(route_id),
   departure_datetime TIMESTAMP NOT NULL,
   arrival_datetime TIMESTAMP,
   fuel_consumed_liters DECIMAL(10,2),
   total_weight_kg DECIMAL(10,2),
   status VARCHAR(20) DEFAULT 'in_progress'
);

-- Tabla: deliveries
CREATE TABLE deliveries (
   delivery_id SERIAL PRIMARY KEY,
   trip_id INTEGER REFERENCES trips(trip_id),
   tracking_number VARCHAR(50) UNIQUE NOT NULL,
   customer_name VARCHAR(200) NOT NULL,
   delivery_address TEXT NOT NULL,
   package_weight_kg DECIMAL(10,2),
   scheduled_datetime TIMESTAMP,
   delivered_datetime TIMESTAMP,
   delivery_status VARCHAR(20) DEFAULT 'pending',
   recipient_signature BOOLEAN DEFAULT FALSE
);

-- Tabla: maintenance
CREATE TABLE maintenance (
   maintenance_id SERIAL PRIMARY KEY,
   vehicle_id INTEGER REFERENCES vehicles(vehicle_id),
   maintenance_date DATE NOT NULL,
   maintenance_type VARCHAR(50) NOT NULL,
   description TEXT,
   cost DECIMAL(10,2),
   next_maintenance_date DATE,
   performed_by VARCHAR(200)
);

-- ============================================
-- 3. CREACIÓN DE ÍNDICES
-- ============================================

-- Índices para optimización de consultas
CREATE INDEX idx_trips_departure ON trips(departure_datetime);
CREATE INDEX idx_deliveries_status ON deliveries(delivery_status);
CREATE INDEX idx_vehicles_status ON vehicles(status);

-- ============================================
-- 4. DOCUMENTACIÓN DEL MODELO
-- ============================================

COMMENT ON TABLE vehicles IS 'Registro de vehículos de la flota de FleetLogix';
COMMENT ON TABLE drivers IS 'Información de conductores empleados';
COMMENT ON TABLE routes IS 'Rutas predefinidas entre ciudades';
COMMENT ON TABLE trips IS 'Registro de viajes realizados';
COMMENT ON TABLE deliveries IS 'Entregas individuales asociadas a cada viaje';
COMMENT ON TABLE maintenance IS 'Historial de mantenimiento de vehículos';

-- ============================================
-- 5. VALIDACIÓN DEL ESQUEMA
-- ============================================

-- Verificar tablas creadas
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;