-- =====================================================
-- FLEETLOGIX - ÍNDICES DE OPTIMIZACIÓN
-- Basados en las 12 queries analizadas
-- Objetivo: Mejorar performance en 20%+
-- =====================================================

-- Análisis de performance ANTES de crear índices
-- Ejecutar cada query con EXPLAIN ANALYZE y guardar tiempos

-- =====================================================
-- OPCIONAL: LIMPIEZA PREVIA SI SE QUIERE REEJECUTAR
-- =====================================================
-- Descomentar solo si ya habías creado estos índices antes
-- DROP INDEX IF EXISTS idx_trips_composite_joins;
-- DROP INDEX IF EXISTS idx_deliveries_scheduled_trip;
-- DROP INDEX IF EXISTS idx_maintenance_vehicle_cost;
-- DROP INDEX IF EXISTS idx_drivers_active_driver;
-- DROP INDEX IF EXISTS idx_deliveries_trip_id;

-- =====================================================
-- ÍNDICE 1: Optimización para JOINs frecuentes en trips
-- =====================================================
-- Justificación original: Las queries 4-12 hacen JOIN intensivo entre trips y otras tablas
-- Queries beneficiadas: 4, 5, 6, 7, 9, 10, 11
--
-- CORRECCIÓN:
-- Se mantiene la idea del índice compuesto sobre trips,
-- pero se evita duplicar el foco temporal ya cubierto por idx_trips_departure.
-- El objetivo principal acá es acelerar joins sobre viajes completados.
CREATE INDEX idx_trips_composite_joins
ON trips(vehicle_id, driver_id, route_id)
WHERE status = 'completed';

-- =====================================================
-- ÍNDICE 2: Optimización para análisis temporal de deliveries
-- =====================================================
-- Justificación original: Queries 8, 12 filtran y agrupan por scheduled_datetime
-- Queries beneficiadas: 4, 8, 12
--
-- CORRECCIÓN:
-- Se elimina la condición parcial por delivery_status = 'delivered'
-- porque la Query 4 no filtra por ese campo.
-- Además se agrega trip_id para mejorar el join con trips en consultas temporales.
CREATE INDEX idx_deliveries_scheduled_trip
ON deliveries(scheduled_datetime, trip_id);

-- =====================================================
-- ÍNDICE 3: Optimización para mantenimiento por vehículo
-- =====================================================
-- Justificación: Query 9 necesita acceso rápido a mantenimientos por vehículo
-- Queries beneficiadas: 9
CREATE INDEX idx_maintenance_vehicle_cost
ON maintenance(vehicle_id, cost);

-- =====================================================
-- ÍNDICE 4: Optimización para análisis de conductores activos
-- =====================================================
-- Justificación original: Queries 5, 6, 10 filtran por conductores activos
-- Queries beneficiadas: 5, 6, 10
--
-- CORRECCIÓN:
-- Se reemplaza license_expiry porque no participa en las queries analizadas.
-- El filtro real observado es status = 'active'.
CREATE INDEX idx_drivers_active_driver
ON drivers(driver_id)
WHERE status = 'active';

-- =====================================================
-- ÍNDICE 5: Optimización para JOINs pesados sobre deliveries
-- =====================================================
-- Justificación:
-- A partir de los EXPLAIN ANALYZE se observó que deliveries es una de las tablas
-- con mayor costo en queries como 6, 9, 10 y 12.
--
-- CORRECCIÓN RESPECTO DE LA PLANTILLA ORIGINAL:
-- Se reemplaza el índice sobre routes, ya que esa tabla es muy pequeña (50 filas)
-- y route_id ya posee índice por ser clave primaria.
-- En cambio, deliveries sí apareció como cuello de botella real.
CREATE INDEX idx_deliveries_trip_id
ON deliveries(trip_id);

-- =====================================================
-- COMANDOS PARA VERIFICAR ÍNDICES CREADOS
-- =====================================================
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;

-- =====================================================
-- ACTUALIZACIÓN DE ESTADÍSTICAS
-- =====================================================
ANALYZE vehicles;
ANALYZE drivers;
ANALYZE routes;
ANALYZE trips;
ANALYZE deliveries;
ANALYZE maintenance;