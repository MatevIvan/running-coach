import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fetch_historical_weather.py"
SPEC = importlib.util.spec_from_file_location("fetch_historical_weather", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class HistoricalWeatherTests(unittest.TestCase):
    def test_gpx_location_is_quantized_and_withheld_from_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "run.gpx"
            path.write_text(
                """<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="47.1234" lon="-122.9876"><time>2026-08-31T16:00:00Z</time></trkpt>
    <trkpt lat="47.1334" lon="-122.9776"><time>2026-08-31T16:30:00Z</time></trkpt>
  </trkseg></trk>
</gpx>
""",
                encoding="utf-8",
            )
            records = MODULE.load_gpx_records(path, "UTC")
            start, end, latitude, longitude, metadata = MODULE.activity_window_and_location(
                records, "GPX track points"
            )

        self.assertEqual(start.isoformat(), "2026-08-31T16:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-08-31T16:30:00+00:00")
        self.assertAlmostEqual(latitude % 0.05, 0.0, places=8)
        self.assertAlmostEqual(longitude % 0.05, 0.0, places=8)
        self.assertTrue(metadata["coordinates_withheld"])

    def test_summary_contains_weather_but_no_coordinates(self):
        start = dt.datetime(2026, 8, 31, 16, 10, tzinfo=dt.timezone.utc)
        end = dt.datetime(2026, 8, 31, 17, 5, tzinfo=dt.timezone.utc)
        payload = {
            "latitude": 47.1,
            "longitude": -122.9,
            "hourly_units": {
                "temperature_2m": "°F",
                "apparent_temperature": "°F",
                "relative_humidity_2m": "%",
                "dew_point_2m": "°F",
                "precipitation": "inch",
                "wind_speed_10m": "mp/h",
                "wind_gusts_10m": "mp/h",
            },
            "hourly": {
                "time": ["2026-08-31T16:00", "2026-08-31T17:00", "2026-08-31T18:00"],
                "temperature_2m": [60, 62, 64],
                "apparent_temperature": [59, 61, 63],
                "relative_humidity_2m": [70, 65, 60],
                "dew_point_2m": [50, 49, 48],
                "precipitation": [0.0, 0.01, 0.0],
                "weather_code": [1, 2, 2],
                "wind_speed_10m": [5, 7, 9],
                "wind_direction_10m": [180, 190, 200],
                "wind_gusts_10m": [8, 10, 12],
            },
        }
        result = MODULE.summarize_weather(
            payload,
            start,
            end,
            {
                "source": "FIT GPS records",
                "gps_points_used": 100,
                "method": "private test",
                "coordinates_withheld": True,
            },
        )
        serialized = json.dumps(result)

        self.assertNotIn("latitude", serialized)
        self.assertNotIn("longitude", serialized)
        self.assertEqual(result["hourly_samples"], 2)
        self.assertEqual(result["conditions"]["temperature"]["mean"], 61.0)
        self.assertEqual(
            result["conditions"]["precipitation_total_for_sampled_hours"], 0.01
        )
        self.assertEqual(
            result["conditions"]["weather_code_labels"],
            ["mainly clear", "partly cloudy"],
        )


if __name__ == "__main__":
    unittest.main()
