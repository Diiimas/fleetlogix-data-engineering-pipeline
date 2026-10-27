import unittest
from datetime import date

import pandas as pd

from src.etl_pipeline import FleetLogixETL


class TransformDataTests(unittest.TestCase):

    def setUp(self):
        self.etl = FleetLogixETL()

    def test_transform_data_calculates_expected_metrics(self):
        data = pd.DataFrame(
            {
                "trip_id": [1, 1],
                "scheduled_datetime": [
                    "2026-10-20 08:00:00",
                    "2026-10-20 08:00:00",
                ],
                "delivered_datetime": [
                    "2026-10-20 08:20:00",
                    "2026-10-20 08:45:00",
                ],
                "departure_datetime": [
                    "2026-10-20 07:00:00",
                    "2026-10-20 07:00:00",
                ],
                "arrival_datetime": [
                    "2026-10-20 09:00:00",
                    "2026-10-20 09:00:00",
                ],
                "distance_km": [100.0, 100.0],
                "fuel_consumed_liters": [20.0, 20.0],
                "toll_cost": [2000.0, 2000.0],
                "package_weight_kg": [10.0, 20.0],
            }
        )

        result = self.etl.transform_data(data)

        self.assertEqual(len(result), 2)
        self.assertEqual(result["delivery_time_minutes"].tolist(), [20.0, 45.0])
        self.assertEqual(result["delay_minutes"].tolist(), [20.0, 45.0])
        self.assertEqual(result["is_on_time"].tolist(), [True, False])

        self.assertEqual(result["trip_duration_hours"].tolist(), [2.0, 2.0])
        self.assertEqual(result["deliveries_in_trip"].tolist(), [2, 2])
        self.assertEqual(result["deliveries_per_hour"].tolist(), [1.0, 1.0])

        self.assertEqual(
            result["fuel_efficiency_km_per_liter"].tolist(),
            [5.0, 5.0],
        )
        self.assertEqual(result["cost_per_delivery"].tolist(), [51000.0, 51000.0])
        self.assertEqual(
            result["revenue_per_delivery"].tolist(),
            [25000.0, 30000.0],
        )

        self.assertEqual(
            result["valid_from"].tolist(),
            [date(2026, 10, 20), date(2026, 10, 20)],
        )
        self.assertTrue(result["valid_to"].eq(date(9999, 12, 31)).all())
        self.assertTrue(result["is_current"].all())

        self.assertEqual(self.etl.metrics["records_transformed"], 2)
        self.assertEqual(self.etl.metrics["errors"], 0)

    def test_transform_data_removes_invalid_records(self):
        data = pd.DataFrame(
            {
                "trip_id": [1, 2, 3],
                "scheduled_datetime": [
                    "2026-10-20 08:00:00",
                    "2026-10-20 09:00:00",
                    "2026-10-20 10:00:00",
                ],
                "delivered_datetime": [
                    "2026-10-20 08:20:00",  # Registro válido
                    "2026-10-20 08:50:00",  # Tiempo negativo
                    "2026-10-20 10:20:00",  # Peso inválido
                ],
                "departure_datetime": [
                    "2026-10-20 07:00:00",
                    "2026-10-20 08:00:00",
                    "2026-10-20 09:00:00",
                ],
                "arrival_datetime": [
                    "2026-10-20 09:00:00",
                    "2026-10-20 10:00:00",
                    "2026-10-20 11:00:00",
                ],
                "distance_km": [100.0, 100.0, 100.0],
                "fuel_consumed_liters": [20.0, 20.0, 20.0],
                "toll_cost": [2000.0, 2000.0, 2000.0],
                "package_weight_kg": [10.0, 10.0, 0.0],
            }
        )

        result = self.etl.transform_data(data)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["trip_id"], 1)
        self.assertEqual(self.etl.metrics["records_transformed"], 1)
        self.assertEqual(self.etl.metrics["errors"], 0)

    def test_transform_data_removes_zero_division_records(self):
        data = pd.DataFrame(
            {
                "trip_id": [1, 2, 3],
                "scheduled_datetime": [
                    "2026-10-20 08:00:00",
                    "2026-10-20 09:00:00",
                    "2026-10-20 10:00:00",
                ],
                "delivered_datetime": [
                    "2026-10-20 08:20:00",
                    "2026-10-20 09:20:00",
                    "2026-10-20 10:20:00",
                ],
                "departure_datetime": [
                    "2026-10-20 07:00:00",
                    "2026-10-20 09:00:00",  # Duración cero
                    "2026-10-20 09:00:00",
                ],
                "arrival_datetime": [
                    "2026-10-20 09:00:00",
                    "2026-10-20 09:00:00",  # Duración cero
                    "2026-10-20 11:00:00",
                ],
                "distance_km": [100.0, 100.0, 100.0],
                "fuel_consumed_liters": [
                    20.0,
                    20.0,
                    0.0,  # División por cero
                ],
                "toll_cost": [2000.0, 2000.0, 2000.0],
                "package_weight_kg": [10.0, 10.0, 10.0],
            }
        )

        result = self.etl.transform_data(data)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["trip_id"], 1)
        self.assertFalse(
            result["deliveries_per_hour"].isin([float("inf"), float("-inf")]).any()
        )
        self.assertFalse(
            result["fuel_efficiency_km_per_liter"].isin(
                [float("inf"), float("-inf")]
            ).any()
        )
        self.assertEqual(self.etl.metrics["records_transformed"], 1)

if __name__ == "__main__":
    unittest.main()