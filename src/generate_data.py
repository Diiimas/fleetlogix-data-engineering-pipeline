"""
FleetLogix - Generación de Datos Sintéticos

Script para poblar la base de datos relacional con 505.650 registros,
respetando relaciones entre tablas y reglas básicas del negocio logístico.

Correcciones aplicadas sobre el código base:
- Se completó el INSERT faltante en vehicles
- Se corrigió la generación incompleta de routes
- Se corrigió el error de conteo en deliveries (> por >=)
- Se corrigió incompatibilidad entre np.float64 y psycopg2
- Se corrigió la generación incompleta de maintenance
- Se agregó reinicio controlado de tablas con TRUNCATE
"""

import psycopg2
from psycopg2.extras import execute_batch
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import logging
from tqdm import tqdm
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# CONFIGURACIÓN GENERAL
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_generation.log'),
        logging.StreamHandler()
    ]
)

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "database": os.getenv("POSTGRES_DB", "fleetlogix"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
}

# Se mantiene es_CO porque el código base de cursada trabaja con ciudades colombianas
fake = Faker('es_CO')
Faker.seed(42)
random.seed(42)
np.random.seed(42)


class DataGenerator:
    def __init__(self, db_config):
        """
        Inicializa el generador de datos sintéticos.
        """
        self.db_config = db_config
        self.connection = None
        self.cursor = None

        self.cities = ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena']

        self.counters = {
            'vehicles': 0,
            'drivers': 0,
            'routes': 0,
            'trips': 0,
            'deliveries': 0,
            'maintenance': 0
        }

    def connect(self):
        """
        Establece conexión con PostgreSQL.
        """
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.cursor = self.connection.cursor()
            logging.info("Conexión exitosa a PostgreSQL.")
            return True
        except Exception as e:
            logging.error(f"Error al conectar con PostgreSQL: {e}")
            return False

    def close(self):
        """
        Cierra cursor y conexión.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logging.info("Conexión cerrada.")

    def reset_tables(self):
        """
        Reinicia las tablas del proyecto antes de una nueva carga.
        IMPORTANTE: este método elimina todos los datos existentes.
        """
        logging.info("Reiniciando tablas con TRUNCATE...")

        self.cursor.execute("""
            TRUNCATE TABLE
                deliveries,
                maintenance,
                trips,
                routes,
                drivers,
                vehicles
            RESTART IDENTITY CASCADE;
        """)
        self.connection.commit()

        logging.info("Tablas reiniciadas correctamente.")

    def generate_vehicles(self, count=200):
        """
        Genera registros de vehículos.
        """
        logging.info(f"Generando {count} vehículos...")

        vehicle_types = [
            ('Camión Grande', 5000, 'diesel', 0.3),
            ('Camión Mediano', 3000, 'diesel', 0.3),
            ('Van', 1500, 'gasolina', 0.3),
            ('Motocicleta', 50, 'gasolina', 0.1)
        ]

        vehicles = []
        used_plates = set()

        while len(vehicles) < count:
            v_type, capacity, fuel, prob = random.choices(
                vehicle_types,
                weights=[vt[3] for vt in vehicle_types]
            )[0]

            license_plate = (
                f"{fake.random_uppercase_letter()}"
                f"{fake.random_uppercase_letter()}"
                f"{fake.random_uppercase_letter()}"
                f"{random.randint(100, 999)}"
            )

            if license_plate in used_plates:
                continue

            used_plates.add(license_plate)

            acquisition_date = fake.date_between(start_date='-5y', end_date='-1m')
            status = random.choice(['active'] * 9 + ['maintenance'])

            vehicles.append((
                license_plate,
                v_type,
                capacity,
                fuel,
                acquisition_date,
                status
            ))

        # CORRECCIÓN: INSERT faltante en el código original
        query = """
            INSERT INTO vehicles (
                license_plate,
                vehicle_type,
                capacity_kg,
                fuel_type,
                acquisition_date,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        execute_batch(self.cursor, query, vehicles, page_size=100)
        self.connection.commit()

        self.counters['vehicles'] = count
        logging.info(f"{count} vehículos insertados correctamente.")

    def generate_drivers(self, count=400):
        """
        Genera registros de conductores.
        """
        logging.info(f"Generando {count} conductores...")

        drivers = []
        used_license_numbers = set()
        license_types = ['C1', 'C2', 'C3', 'A2']

        for i in range(count):
            employee_code = f"EMP{str(i + 1).zfill(4)}"
            first_name = fake.first_name()
            last_name = fake.last_name()

            license_number = f"{random.randint(1000000000, 9999999999)}"
            while license_number in used_license_numbers:
                license_number = f"{random.randint(1000000000, 9999999999)}"
            used_license_numbers.add(license_number)

            license_type = random.choice(license_types)
            # Se conserva por consistencia con el código base, aunque no existe columna en la tabla.

            license_expiry = fake.date_between(start_date='-1m', end_date='+3y')
            phone = f"3{random.randint(100000000, 999999999)}"
            hire_date = fake.date_between(start_date='-5y', end_date='-1w')
            status = random.choice(['active'] * 19 + ['inactive'])

            drivers.append((
                employee_code,
                first_name,
                last_name,
                license_number,
                license_expiry,
                phone,
                hire_date,
                status
            ))

        query = """
            INSERT INTO drivers (
                employee_code,
                first_name,
                last_name,
                license_number,
                license_expiry,
                phone,
                hire_date,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        execute_batch(self.cursor, query, drivers, page_size=100)
        self.connection.commit()

        self.counters['drivers'] = count
        logging.info(f"{count} conductores insertados correctamente.")

    def _get_distance(self, origin, destination):
        """
        Devuelve la distancia aproximada entre dos ciudades.

        Se utiliza frozenset para que el resultado sea independiente
        del sentido de la ruta.
        """
        distances = {
            frozenset(("Bogotá", "Medellín")): 440,
            frozenset(("Bogotá", "Cali")): 460,
            frozenset(("Bogotá", "Barranquilla")): 1000,
            frozenset(("Bogotá", "Cartagena")): 1050,
            frozenset(("Medellín", "Cali")): 420,
            frozenset(("Medellín", "Barranquilla")): 640,
            frozenset(("Medellín", "Cartagena")): 640,
            frozenset(("Cali", "Barranquilla")): 1100,
            frozenset(("Cali", "Cartagena")): 1100,
            frozenset(("Barranquilla", "Cartagena")): 120,
        }

        key = frozenset((origin, destination))
        return distances.get(key, 500)

        key = tuple(sorted([origin, destination]))
        return distances.get(key, 500)

    def generate_routes(self, count=50):
        """
        Genera rutas entre ciudades.
        """
        logging.info(f"Generando {count} rutas...")

        routes = []
        route_counter = 1

        for origin in self.cities:
            for destination in self.cities:
                if origin != destination:
                    num_routes = 3 if origin == 'Bogotá' or destination == 'Bogotá' else 2

                    for _ in range(num_routes):
                        route_code = f"R{str(route_counter).zfill(3)}"

                        base_distance = self._get_distance(origin, destination)
                        distance = base_distance + random.uniform(-50, 50)

                        avg_speed = random.uniform(60, 80)
                        duration = distance / avg_speed

                        toll_cost = int(distance / 100) * 15000

                        routes.append((
                            route_code,
                            origin,
                            destination,
                            round(distance, 2),
                            round(duration, 2),
                            toll_cost
                        ))

                        route_counter += 1

        # CORRECCIÓN: la lógica original no garantizaba alcanzar exactamente 50 rutas
        while len(routes) < count:
            origin = random.choice(self.cities)
            destination = random.choice(self.cities)

            if origin != destination:
                route_code = f"R{str(route_counter).zfill(3)}"

                base_distance = self._get_distance(origin, destination)
                distance = base_distance + random.uniform(-50, 50)

                avg_speed = random.uniform(60, 80)
                duration = distance / avg_speed

                toll_cost = int(distance / 100) * 15000

                routes.append((
                    route_code,
                    origin,
                    destination,
                    round(distance, 2),
                    round(duration, 2),
                    toll_cost
                ))

                route_counter += 1

        routes = routes[:count]

        query = """
            INSERT INTO routes (
                route_code,
                origin_city,
                destination_city,
                distance_km,
                estimated_duration_hours,
                toll_cost
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        execute_batch(self.cursor, query, routes, page_size=50)
        self.connection.commit()

        self.counters['routes'] = count
        logging.info(f"{count} rutas insertadas correctamente.")

    def _get_hourly_distribution(self):
        """
        Distribución de probabilidad por hora.
        """
        probs = np.ones(24) * 0.02
        probs[6:20] = 0.06
        probs[8:12] = 0.08
        probs[14:18] = 0.07
        return probs / probs.sum()

    def generate_trips(self, count=100000):
        """
        Genera viajes utilizando vehículos, conductores y rutas válidas.
        """
        logging.info(f"Generando {count} viajes...")

        self.cursor.execute("SELECT vehicle_id, capacity_kg FROM vehicles WHERE status = 'active'")
        vehicles = self.cursor.fetchall()

        self.cursor.execute("SELECT driver_id FROM drivers WHERE status = 'active'")
        drivers = [d[0] for d in self.cursor.fetchall()]

        self.cursor.execute("SELECT route_id, distance_km, estimated_duration_hours FROM routes")
        routes = self.cursor.fetchall()

        start_date = datetime.now() - timedelta(days=730)

        trips = []
        current_date = start_date

        for _ in tqdm(range(count), desc="Generando trips"):
            vehicle_id, capacity = random.choice(vehicles)
            capacity = float(capacity)

            driver_id = random.choice(drivers)
            route_id, distance, est_duration = random.choice(routes)

            distance = float(distance)
            est_duration = float(est_duration)

            hour = np.random.choice(range(24), p=self._get_hourly_distribution())

            departure = current_date.replace(
                hour=hour,
                minute=random.randint(0, 59),
                second=0,
                microsecond=0
            )

            actual_duration = est_duration * random.uniform(0.8, 1.3)
            arrival = departure + timedelta(hours=actual_duration)

            # MEJORA: consumo ajustado por tipo de vehículo según capacidad
            if capacity > 4000:
                consumption_rate = random.uniform(0.25, 0.35)
            elif capacity > 2000:
                consumption_rate = random.uniform(0.18, 0.25)
            elif capacity > 500:
                consumption_rate = random.uniform(0.10, 0.18)
            else:
                consumption_rate = random.uniform(0.03, 0.07)

            fuel_consumed = distance * consumption_rate
            total_weight = capacity * random.uniform(0.4, 0.9)

            status = 'completed' if arrival < datetime.now() else 'in_progress'

            trips.append((
                vehicle_id,
                driver_id,
                route_id,
                departure,
                arrival if status == 'completed' else None,
                round(float(fuel_consumed), 2),
                round(float(total_weight), 2),
                status
            ))

            current_date += timedelta(minutes=int(1440 * 2 * 365 / count))

        query = """
            INSERT INTO trips (
                vehicle_id,
                driver_id,
                route_id,
                departure_datetime,
                arrival_datetime,
                fuel_consumed_liters,
                total_weight_kg,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        for i in range(0, len(trips), batch_size):
            batch = trips[i:i + batch_size]
            execute_batch(
                self.cursor,
                query,
                batch,
                page_size=100,
            )

            inserted = min(i + len(batch), len(trips))

            if inserted % 10000 == 0 or inserted == len(trips):
                logging.info(
                    "%s/%s trips preparados para confirmar",
                    inserted,
                    len(trips),
                )

        self.connection.commit()

        self.counters["trips"] = len(trips)
        logging.info(
            "%s viajes insertados correctamente.",
            len(trips),
        )

    def _distribute_weight(self, total_weight, num_packages):
        """
        Distribuye el 95 % del peso total entre los paquetes.

        Cada paquete debe pesar al menos 0,5 kg. Se rechazan entradas
        no positivas o combinaciones que no permitan respetar ese mínimo.
        """
        if num_packages <= 0:
            raise ValueError("num_packages debe ser mayor que cero")

        if total_weight <= 0:
            raise ValueError("total_weight debe ser mayor que cero")

        minimum_package_weight = 0.5
        target_weight = total_weight * 0.95
        minimum_required = minimum_package_weight * num_packages

        if target_weight < minimum_required:
            raise ValueError(
                "El peso disponible no permite asignar "
                "el mínimo de 0,5 kg por paquete"
            )

        remaining_weight = target_weight - minimum_required

        if remaining_weight == 0:
            return np.full(num_packages, minimum_package_weight)

        proportions = np.random.exponential(
            scale=1.0,
            size=num_packages,
        )
        proportions = proportions / proportions.sum()

        return (
            np.full(num_packages, minimum_package_weight)
            + proportions * remaining_weight
        )

    def generate_deliveries(self, count=400000):
        """
        Genera entregas asociadas a los viajes.
        """
        logging.info(f"Generando {count} entregas...")

        # CORRECCIÓN: query faltante en el código original
        self.cursor.execute("""
            SELECT
                t.trip_id,
                t.departure_datetime,
                t.arrival_datetime,
                t.total_weight_kg,
                r.destination_city
            FROM trips t
            JOIN routes r ON t.route_id = r.route_id
        """)
        trips_data = self.cursor.fetchall()

        deliveries = []
        delivery_counter = 0

        for trip_id, departure, arrival, total_weight, city in tqdm(trips_data, desc="Generando deliveries"):
            num_deliveries = np.random.choice([2, 3, 4, 5, 6], p=[0.1, 0.2, 0.4, 0.2, 0.1])

            weights = self._distribute_weight(float(total_weight), num_deliveries)

            if arrival:
                duration = (arrival - departure).total_seconds() / 3600
                time_per_delivery = duration / num_deliveries
            else:
                time_per_delivery = 0.5

            for i in range(num_deliveries):
                tracking_number = f"FL{datetime.now().year}{str(delivery_counter + 1).zfill(8)}"
                customer_name = fake.name()
                delivery_address = f"{fake.street_address()}, {city}"
                scheduled = departure + timedelta(hours=time_per_delivery * (i + 0.5))

                if arrival:
                    if random.random() < 0.9:
                        delivered = scheduled + timedelta(minutes=random.randint(-30, 30))
                    else:
                        delivered = scheduled + timedelta(minutes=random.randint(60, 180))

                    delivery_status = 'delivered'
                    signature = random.random() < 0.95
                else:
                    delivered = None
                    delivery_status = 'pending'
                    signature = False

                deliveries.append((
                    trip_id,
                    tracking_number,
                    customer_name,
                    delivery_address,
                    round(float(weights[i]), 2),  # CORRECCIÓN: conversión explícita desde np.float64
                    scheduled,
                    delivered,
                    delivery_status,
                    signature
                ))

                delivery_counter += 1

                # CORRECCIÓN: el código original usaba ">" y podía exceder el total requerido
                if delivery_counter >= count:
                    break

            if delivery_counter >= count:
                break

        if len(deliveries) != count:
            raise RuntimeError(
                "No se pudo generar la cantidad solicitada de entregas: "
                f"solicitadas={count}, generadas={len(deliveries)}"
            )

        query = """
            INSERT INTO deliveries (
                trip_id,
                tracking_number,
                customer_name,
                delivery_address,
                package_weight_kg,
                scheduled_datetime,
                delivered_datetime,
                delivery_status,
                recipient_signature
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        batch_size = 1000

        for i in range(0, len(deliveries), batch_size):
            batch = deliveries[i:i + batch_size]
            execute_batch(
                self.cursor,
                query,
                batch,
                page_size=100,
            )

            inserted = min(i + len(batch), len(deliveries))

            if inserted % 50000 == 0 or inserted == len(deliveries):
                logging.info(
                    "%s/%s deliveries preparadas para confirmar",
                    inserted,
                    len(deliveries),
                )

        self.connection.commit()

        self.counters['deliveries'] = len(deliveries)
        logging.info(f"{len(deliveries)} entregas insertadas correctamente.")

    def generate_maintenance(self, count=5000):
        """
        Genera registros de mantenimiento basados en el uso de los vehículos.
        """
        logging.info(f"Generando {count} registros de mantenimiento...")

        # CORRECCIÓN: query faltante en el código original
        self.cursor.execute("""
            SELECT
                v.vehicle_id,
                v.vehicle_type,
                COUNT(t.trip_id) AS trip_count,
                MIN(t.departure_datetime),
                MAX(t.departure_datetime)
            FROM vehicles v
            LEFT JOIN trips t ON v.vehicle_id = t.vehicle_id
            GROUP BY v.vehicle_id, v.vehicle_type
        """)
        vehicle_stats = self.cursor.fetchall()

        maintenance_types = [
            ('Cambio de aceite', 150000, 30),
            ('Revisión de frenos', 250000, 60),
            ('Cambio de llantas', 450000, 90),
            ('Mantenimiento general', 350000, 45),
            ('Revisión de motor', 500000, 60),
            ('Alineación y balanceo', 180000, 30)
        ]

        maintenance_records = []

        for vehicle_id, vehicle_type, trip_count, first_trip, last_trip in vehicle_stats:
            num_maintenance = max(1, trip_count // 20)

            if first_trip and last_trip:
                operation_days = max(1, (last_trip - first_trip).days)

                for i in range(num_maintenance):
                    if len(maintenance_records) >= count:
                        break

                    days_offset = int(operation_days * (i + 1) / (num_maintenance + 1))
                    maintenance_date = (first_trip + timedelta(days=days_offset)).date()

                    maint_type, base_cost, days_next = random.choice(maintenance_types)
                    cost = base_cost * random.uniform(0.8, 1.2)
                    description = f"{maint_type} programado"
                    next_maintenance = maintenance_date + timedelta(days=days_next)
                    performed_by = f"{fake.first_name()} {fake.last_name()}"

                    maintenance_records.append((
                        vehicle_id,
                        maintenance_date,
                        maint_type,
                        description,
                        round(float(cost), 2),
                        next_maintenance,
                        performed_by
                    ))

                if len(maintenance_records) >= count:
                    break

        # CORRECCIÓN: la lógica original podía quedarse corta respecto del total requerido
        while len(maintenance_records) < count:
            vehicle_id, vehicle_type, trip_count, first_trip, last_trip = random.choice(vehicle_stats)

            if first_trip and last_trip:
                start_date = first_trip.date()
                end_date = last_trip.date()

                if start_date == end_date:
                    maintenance_date = start_date
                else:
                    random_days = random.randint(0, (end_date - start_date).days)
                    maintenance_date = start_date + timedelta(days=random_days)
            else:
                maintenance_date = fake.date_between(start_date='-2y', end_date='today')

            maint_type, base_cost, days_next = random.choice(maintenance_types)
            cost = base_cost * random.uniform(0.8, 1.2)
            description = f"{maint_type} adicional para completar volumen objetivo"
            next_maintenance = maintenance_date + timedelta(days=days_next)
            performed_by = f"{fake.first_name()} {fake.last_name()}"

            maintenance_records.append((
                vehicle_id,
                maintenance_date,
                maint_type,
                description,
                round(float(cost), 2),
                next_maintenance,
                performed_by
            ))

        query = """
            INSERT INTO maintenance (
                vehicle_id,
                maintenance_date,
                maintenance_type,
                description,
                cost,
                next_maintenance_date,
                performed_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        execute_batch(self.cursor, query, maintenance_records[:count], page_size=100)
        self.connection.commit()

        self.counters['maintenance'] = len(maintenance_records[:count])
        logging.info(f"{self.counters['maintenance']} mantenimientos insertados correctamente.")

    def validate_data_quality(self):
        """
        Ejecuta controles básicos de calidad de datos.
        """
        logging.info("Validando calidad de datos...")

        validations = {
            "Trips sin vehículo válido": """
                SELECT COUNT(*) FROM trips t
                LEFT JOIN vehicles v ON t.vehicle_id = v.vehicle_id
                WHERE v.vehicle_id IS NULL
            """,
            "Deliveries sin trip válido": """
                SELECT COUNT(*) FROM deliveries d
                LEFT JOIN trips t ON d.trip_id = t.trip_id
                WHERE t.trip_id IS NULL
            """,
            "Arrival menor que Departure": """
                SELECT COUNT(*) FROM trips
                WHERE arrival_datetime IS NOT NULL
                AND arrival_datetime < departure_datetime
            """,
            "Peso excede capacidad": """
                SELECT COUNT(*) FROM trips t
                JOIN vehicles v ON t.vehicle_id = v.vehicle_id
                WHERE t.total_weight_kg > v.capacity_kg
            """
        }

        all_valid = True

        for desc, query in validations.items():
            self.cursor.execute(query)
            result = self.cursor.fetchone()[0]
            logging.info(f"{desc}: {result}")
            if result > 0:
                all_valid = False

        return all_valid

    def generate_summary_report(self):
        """
        Genera un resumen en JSON con los conteos finales.
        """
        logging.info("Generando resumen final...")

        tables = ['vehicles', 'drivers', 'routes', 'trips', 'deliveries', 'maintenance']
        total_records = 0

        table_counts = {}

        for table in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            table_counts[table] = count
            total_records += count

        summary = {
            'generation_date': datetime.now().isoformat(),
            'total_records': total_records,
            'table_counts': table_counts,
            'validations_passed': self.validate_data_quality()
        }

        with open('generation_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logging.info(f"Total de registros generados: {total_records}")
        logging.info("Resumen guardado en generation_summary.json")


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    print("FLEETLOGIX - Generación de Datos Masivos")
    print("=" * 60)
    print("Objetivo: generar 505.650 registros manteniendo integridad")
    print("=" * 60)

    generator = DataGenerator(DB_CONFIG)

    try:
        if not generator.connect():
            return

        generator.reset_tables()
        generator.generate_vehicles(200)
        generator.generate_drivers(400)
        generator.generate_routes(50)
        generator.generate_trips(100000)
        generator.generate_deliveries(400000)
        generator.generate_maintenance(5000)
        generator.generate_summary_report()

    except Exception as e:
        logging.error(f"Error durante la generación: {e}")
        if generator.connection:
            generator.connection.rollback()

    finally:
        generator.close()


if __name__ == "__main__":
    main()