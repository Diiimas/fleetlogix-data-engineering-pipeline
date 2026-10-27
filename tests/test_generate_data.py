import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import psycopg2

from src.generate_data import DataGenerator


class DataGeneratorConnectionTests(unittest.TestCase):

    def setUp(self):
        self.config = {
            "host": "localhost",
            "database": "fleetlogix_test",
            "user": "test_user",
            "password": "test_password",
            "port": 5432,
        }

    @patch("src.generate_data.psycopg2.connect")
    def test_connect_and_close_database(self, mock_connect):
        mock_connection = MagicMock()
        mock_cursor = MagicMock()

        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        generator = DataGenerator(self.config)

        connected = generator.connect()

        self.assertTrue(connected)
        mock_connect.assert_called_once_with(**self.config)
        self.assertIs(generator.connection, mock_connection)
        self.assertIs(generator.cursor, mock_cursor)

        generator.close()

        mock_cursor.close.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch(
        "src.generate_data.psycopg2.connect",
        side_effect=psycopg2.OperationalError("database unavailable"),
    )
    def test_connect_returns_false_when_database_is_unavailable(
        self,
        mock_connect,
    ):
        generator = DataGenerator(self.config)

        connected = generator.connect()

        self.assertFalse(connected)
        self.assertIsNone(generator.connection)
        self.assertIsNone(generator.cursor)
        mock_connect.assert_called_once_with(**self.config)

class DataGeneratorHelperTests(unittest.TestCase):

    def setUp(self):
        self.generator = DataGenerator({})

    def test_get_distance_is_symmetric_and_returns_expected_values(self):
        expected_distances = {
            ("Bogotá", "Medellín"): 440,
            ("Bogotá", "Cali"): 460,
            ("Bogotá", "Barranquilla"): 1000,
            ("Bogotá", "Cartagena"): 1050,
            ("Medellín", "Cali"): 420,
            ("Medellín", "Barranquilla"): 640,
            ("Medellín", "Cartagena"): 640,
            ("Cali", "Barranquilla"): 1100,
            ("Cali", "Cartagena"): 1100,
            ("Barranquilla", "Cartagena"): 120,
        }

        for (origin, destination), expected in expected_distances.items():
            with self.subTest(origin=origin, destination=destination):
                self.assertEqual(
                    self.generator._get_distance(origin, destination),
                    expected,
                )
                self.assertEqual(
                    self.generator._get_distance(destination, origin),
                    expected,
                )

    def test_get_distance_uses_default_for_unknown_route(self):
        self.assertEqual(
            self.generator._get_distance("Ciudad A", "Ciudad B"),
            500,
        )

    def test_hourly_distribution_is_a_valid_probability_distribution(self):
        probabilities = self.generator._get_hourly_distribution()

        self.assertEqual(len(probabilities), 24)
        self.assertAlmostEqual(float(probabilities.sum()), 1.0)
        self.assertTrue((probabilities > 0).all())

        # Las horas de mayor actividad deben tener más peso que la madrugada.
        self.assertGreater(probabilities[9], probabilities[2])

    def test_distribute_weight_preserves_target_and_minimum_weight(self):
        total_weight = 1000.0
        num_packages = 10

        weights = self.generator._distribute_weight(
            total_weight,
            num_packages,
        )

        self.assertEqual(len(weights), num_packages)
        self.assertTrue((weights >= 0.5).all())
        self.assertAlmostEqual(
            float(weights.sum()),
            total_weight * 0.95,
            places=6,
        )

    def test_distribute_weight_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.generator._distribute_weight(1000.0, 0)

        with self.assertRaises(ValueError):
            self.generator._distribute_weight(0.0, 10)

        with self.assertRaises(ValueError):
            self.generator._distribute_weight(-100.0, 10)

        with self.assertRaises(ValueError):
            self.generator._distribute_weight(2.0, 10)

class DataGeneratorDeliveryTests(unittest.TestCase):

    def test_generate_deliveries_fails_when_trips_are_insufficient(self):
        generator = DataGenerator({})

        departure = datetime(2026, 1, 1, 8, 0)
        arrival = departure + timedelta(hours=2)

        generator.cursor = MagicMock()
        generator.connection = MagicMock()
        generator.cursor.fetchall.return_value = [
            (1, departure, arrival, 100.0, "Bogotá"),
        ]

        with (
            patch(
                "src.generate_data.np.random.choice",
                return_value=2,
            ),
            patch.object(
                generator,
                "_distribute_weight",
                return_value=[45.0, 50.0],
            ),
            patch("src.generate_data.execute_batch"),
        ):
            with self.assertRaises(RuntimeError):
                generator.generate_deliveries(count=3)

        generator.connection.commit.assert_not_called()

    def test_generate_deliveries_commits_once_after_all_batches(self):
        generator = DataGenerator({})

        departure = datetime(2026, 1, 1, 8, 0)
        arrival = departure + timedelta(hours=2)

        # 501 viajes permiten generar 1002 entregas; el método se detendrá en 1001.
        trips = [
            (trip_id, departure, arrival, 100.0, "Bogotá")
            for trip_id in range(1, 502)
        ]

        generator.cursor = MagicMock()
        generator.connection = MagicMock()
        generator.cursor.fetchall.return_value = trips

        with (
            patch(
                "src.generate_data.np.random.choice",
                return_value=2,
            ),
            patch.object(
                generator,
                "_distribute_weight",
                return_value=[45.0, 50.0],
            ),
            patch(
                "src.generate_data.execute_batch",
            ) as mock_execute_batch,
            patch(
                "src.generate_data.tqdm",
                side_effect=lambda iterable, **kwargs: iterable,
            ),
            patch(
                "src.generate_data.fake.name",
                return_value="Cliente de prueba",
            ),
            patch(
                "src.generate_data.fake.street_address",
                return_value="Calle de prueba 123",
            ),
        ):
            generator.generate_deliveries(count=1001)

        self.assertEqual(mock_execute_batch.call_count, 2)
        generator.connection.commit.assert_called_once()
        self.assertEqual(generator.counters["deliveries"], 1001)

if __name__ == "__main__":
    unittest.main()