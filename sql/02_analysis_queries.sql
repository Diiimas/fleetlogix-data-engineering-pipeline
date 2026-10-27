-- Query 1: Vehículos activos con su última fecha de mantenimiento
-- Problema de negocio: identificar el estado de mantenimiento reciente de la flota activa

EXPLAIN ANALYZE
SELECT
    v.vehicle_id,
    v.license_plate,
    v.vehicle_type,
    v.status,
    MAX(m.maintenance_date) AS last_maintenance_date
FROM vehicles v
LEFT JOIN maintenance m
    ON v.vehicle_id = m.vehicle_id
WHERE v.status = 'active'
GROUP BY
    v.vehicle_id,
    v.license_plate,
    v.vehicle_type,
    v.status
ORDER BY last_maintenance_date DESC NULLS LAST;


-- Query 2: Cantidad de viajes completados por tipo de vehículo
-- Problema de negocio: conocer qué tipo de vehículo concentra mayor carga operativa

EXPLAIN ANALYZE
SELECT
    v.vehicle_type,
    COUNT(t.trip_id) AS completed_trips
FROM vehicles v
JOIN trips t
    ON v.vehicle_id = t.vehicle_id
WHERE t.status = 'completed'
GROUP BY v.vehicle_type
ORDER BY completed_trips DESC;


-- Query 3: Promedio de peso transportado por ruta
-- Problema de negocio: analizar qué rutas suelen transportar mayor carga promedio

EXPLAIN ANALYZE
SELECT
    r.route_id,
    r.origin_city,
    r.destination_city,
    ROUND(AVG(t.total_weight_kg), 2) AS avg_weight_kg
FROM routes r
JOIN trips t
    ON r.route_id = t.route_id
WHERE t.status = 'completed'
GROUP BY
    r.route_id,
    r.origin_city,
    r.destination_city
ORDER BY avg_weight_kg DESC;


-- Query 4: Total de entregas por ciudad destino en los últimos 2 meses
-- Problema de negocio: identificar demanda por ciudad para planificación de recursos

EXPLAIN ANALYZE
SELECT
    r.destination_city,
    COUNT(d.delivery_id) AS total_deliveries
FROM deliveries d
JOIN trips t
    ON d.trip_id = t.trip_id
JOIN routes r
    ON t.route_id = r.route_id
WHERE d.scheduled_datetime >= CURRENT_DATE - INTERVAL '2 months'
GROUP BY r.destination_city
ORDER BY total_deliveries DESC;


-- Query 5: Conductores activos con cantidad de viajes completados
-- Problema de negocio: evaluar carga de trabajo por conductor

EXPLAIN ANALYZE
SELECT
    d.driver_id,
    d.first_name,
    d.last_name,
    COUNT(t.trip_id) AS completed_trips
FROM drivers d
LEFT JOIN trips t
    ON d.driver_id = t.driver_id
    AND t.status = 'completed'
WHERE d.status = 'active'
GROUP BY
    d.driver_id,
    d.first_name,
    d.last_name
ORDER BY completed_trips DESC;


-- Query 6: Promedio de entregas por conductor en los últimos 6 meses
-- Problema de negocio: medir productividad individual de conductores

EXPLAIN ANALYZE
WITH deliveries_per_trip AS (
    SELECT
        t.driver_id,
        t.trip_id,
        COUNT(d.delivery_id) AS deliveries_in_trip
    FROM trips t
    JOIN deliveries d
        ON t.trip_id = d.trip_id
    WHERE t.departure_datetime >= CURRENT_DATE - INTERVAL '6 months'
    GROUP BY t.driver_id, t.trip_id
)
SELECT
    d.driver_id,
    d.first_name,
    d.last_name,
    ROUND(AVG(dpt.deliveries_in_trip), 2) AS avg_deliveries_per_trip
FROM drivers d
LEFT JOIN deliveries_per_trip dpt
    ON d.driver_id = dpt.driver_id
WHERE d.status = 'active'
GROUP BY
    d.driver_id,
    d.first_name,
    d.last_name
ORDER BY avg_deliveries_per_trip DESC NULLS LAST;


-- Query 7: Rutas con mayor consumo de combustible por kilómetro
-- Problema de negocio: identificar rutas ineficientes para optimización

EXPLAIN ANALYZE
SELECT
    r.route_id,
    r.origin_city,
    r.destination_city,
    ROUND(AVG(t.fuel_consumed_liters / NULLIF(r.distance_km, 0)), 4) AS avg_fuel_per_km
FROM routes r
JOIN trips t
    ON r.route_id = t.route_id
WHERE t.status = 'completed'
GROUP BY
    r.route_id,
    r.origin_city,
    r.destination_city
ORDER BY avg_fuel_per_km DESC;


-- Query 8: Análisis de entregas retrasadas por día de la semana
-- Problema de negocio: identificar patrones de retraso para mejorar planificación

EXPLAIN ANALYZE
SELECT
    TRIM(TO_CHAR(d.scheduled_datetime, 'Day')) AS day_of_week,
    COUNT(*) AS delayed_deliveries
FROM deliveries d
WHERE d.delivered_datetime IS NOT NULL
  AND d.delivered_datetime > d.scheduled_datetime
GROUP BY TRIM(TO_CHAR(d.scheduled_datetime, 'Day'))
ORDER BY delayed_deliveries DESC;


-- Query 9: Costo de mantenimiento por kilómetro recorrido
-- Problema de negocio: evaluar costo-beneficio de cada tipo de vehículo

EXPLAIN ANALYZE
WITH vehicle_km AS (
    SELECT
        t.vehicle_id,
        SUM(r.distance_km) AS total_km
    FROM trips t
    JOIN routes r
        ON t.route_id = r.route_id
    WHERE t.status = 'completed'
    GROUP BY t.vehicle_id
),
vehicle_maintenance AS (
    SELECT
        m.vehicle_id,
        SUM(m.cost) AS total_maintenance_cost
    FROM maintenance m
    GROUP BY m.vehicle_id
)
SELECT
    v.vehicle_id,
    v.vehicle_type,
    ROUND(COALESCE(vm.total_maintenance_cost, 0), 2) AS total_maintenance_cost,
    ROUND(COALESCE(vk.total_km, 0), 2) AS total_km,
    ROUND(
        COALESCE(vm.total_maintenance_cost, 0) / NULLIF(vk.total_km, 0),
        4
    ) AS maintenance_cost_per_km
FROM vehicles v
LEFT JOIN vehicle_km vk
    ON v.vehicle_id = vk.vehicle_id
LEFT JOIN vehicle_maintenance vm
    ON v.vehicle_id = vm.vehicle_id
ORDER BY maintenance_cost_per_km DESC NULLS LAST;


-- Query 10: Ranking de conductores por eficiencia usando Window Functions
-- Problema de negocio: identificar top performers para otorgar incentivos

EXPLAIN ANALYZE
WITH driver_efficiency AS (
    SELECT
        d.driver_id,
        d.first_name,
        d.last_name,
        COUNT(DISTINCT t.trip_id) AS completed_trips,
        COUNT(dv.delivery_id) AS total_deliveries,
        ROUND(
            COUNT(dv.delivery_id)::numeric / NULLIF(COUNT(DISTINCT t.trip_id), 0),
            2
        ) AS deliveries_per_trip
    FROM drivers d
    LEFT JOIN trips t
        ON d.driver_id = t.driver_id
       AND t.status = 'completed'
    LEFT JOIN deliveries dv
        ON t.trip_id = dv.trip_id
    WHERE d.status = 'active'
    GROUP BY
        d.driver_id,
        d.first_name,
        d.last_name
)
SELECT
    driver_id,
    first_name,
    last_name,
    completed_trips,
    total_deliveries,
    deliveries_per_trip,
    RANK() OVER (ORDER BY deliveries_per_trip DESC NULLS LAST) AS efficiency_rank
FROM driver_efficiency
ORDER BY efficiency_rank;


-- Query 11: Análisis de tendencia de viajes con LAG y LEAD
-- Problema de negocio: proyectar necesidades futuras basadas en tendencias

EXPLAIN ANALYZE
WITH monthly_trips AS (
    SELECT
        DATE_TRUNC('month', departure_datetime) AS trip_month,
        COUNT(*) AS total_trips
    FROM trips
    GROUP BY DATE_TRUNC('month', departure_datetime)
)
SELECT
    trip_month,
    total_trips,
    LAG(total_trips) OVER (ORDER BY trip_month) AS previous_month_trips,
    LEAD(total_trips) OVER (ORDER BY trip_month) AS next_month_trips,
    total_trips - LAG(total_trips) OVER (ORDER BY trip_month) AS variation_vs_previous_month
FROM monthly_trips
ORDER BY trip_month;


-- Query 12: Pivot de entregas por hora y día de la semana
-- Problema de negocio: optimizar horarios de operación y personal

EXPLAIN ANALYZE
SELECT
    EXTRACT(HOUR FROM scheduled_datetime) AS hora_entrega,
    COUNT(*) FILTER (WHERE EXTRACT(DOW FROM scheduled_datetime) = 0) AS domingo,
    COUNT(*) FILTER (WHERE EXTRACT(DOW FROM scheduled_datetime) = 1) AS lunes,
    COUNT(*) FILTER (WHERE EXTRACT(DOW FROM scheduled_datetime) = 2) AS martes,
    COUNT(*) FILTER (WHERE EXTRACT(DOW FROM scheduled_datetime) = 3) AS miercoles,
    COUNT(*) FILTER (WHERE EXTRACT(DOW FROM scheduled_datetime) = 4) AS jueves,
    COUNT(*) FILTER (WHERE EXTRACT(DOW FROM scheduled_datetime) = 5) AS viernes,
    COUNT(*) FILTER (WHERE EXTRACT(DOW FROM scheduled_datetime) = 6) AS sabado
FROM deliveries
GROUP BY EXTRACT(HOUR FROM scheduled_datetime)
ORDER BY hora_entrega;