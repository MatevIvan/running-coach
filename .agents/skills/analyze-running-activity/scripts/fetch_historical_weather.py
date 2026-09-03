#!/usr/bin/env python3
"""Fetch historical weather for a run without exposing route coordinates.

The script derives a representative point from FIT, GPX, or GarminDB records,
quantizes it before the network request, and omits coordinates from all output.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import math
import sqlite3
import statistics
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


API_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
SOURCE_URL = "https://open-meteo.com/en/docs/historical-weather-api"
LOCATION_GRID_DEGREES = 0.05
HOURLY_FIELDS = (
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
)
WEATHER_CODE_LABELS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snowfall",
    73: "moderate snowfall",
    75: "heavy snowfall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


class WeatherLookupError(RuntimeError):
    """A safe-to-display lookup or source error."""


def parse_timestamp(value: str | None, default_timezone: str) -> dt.datetime | None:
    if not value:
        return None
    parsed = dt.datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        try:
            timezone = ZoneInfo(default_timezone)
        except ZoneInfoNotFoundError as error:
            raise WeatherLookupError(
                f"Time zone {default_timezone!r} is unavailable. Install the Python "
                "tzdata package when the operating system does not provide IANA time zones."
            ) from error
        parsed = parsed.replace(tzinfo=timezone)
    return parsed.astimezone(dt.timezone.utc)


def normalize_coordinate(value: Any, *, latitude: bool) -> float | None:
    if value is None:
        return None
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    limit = 90.0 if latitude else 180.0
    if abs(coordinate) > limit:
        coordinate *= 180.0 / 2**31
    return coordinate if -limit <= coordinate <= limit else None


def load_fit_records(path: Path) -> list[dict[str, Any]]:
    parser_path = (
        Path(__file__).resolve().parents[2]
        / "parse-fit-run"
        / "scripts"
        / "parse_fit_run.py"
    )
    spec = importlib.util.spec_from_file_location("running_fit_parser", parser_path)
    if spec is None or spec.loader is None:
        raise WeatherLookupError("FIT parser could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.normalized_records(module.parse_fit(path))


def load_gpx_records(path: Path, default_timezone: str) -> list[dict[str, Any]]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        raise WeatherLookupError("GPX activity could not be parsed.") from error

    records: list[dict[str, Any]] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "trkpt":
            continue
        timestamp = None
        for child in element:
            if child.tag.rsplit("}", 1)[-1] == "time":
                timestamp = parse_timestamp(child.text, default_timezone)
                break
        records.append(
            {
                "timestamp_utc": timestamp,
                "position_lat": normalize_coordinate(element.get("lat"), latitude=True),
                "position_long": normalize_coordinate(element.get("lon"), latitude=False),
            }
        )
    return records


def find_fit_file(root: Path, activity_id: str) -> Path | None:
    fit_dir = root / "docs" / "garmindb" / "data" / "FitFiles" / "Activities"
    direct = fit_dir / f"{activity_id}_ACTIVITY.fit"
    if direct.is_file():
        return direct
    matches = sorted(fit_dir.glob(f"{activity_id}*.fit")) if fit_dir.is_dir() else []
    return matches[0] if matches else None


def load_garmindb_records(
    root: Path, activity_id: str, default_timezone: str
) -> list[dict[str, Any]]:
    database = root / "docs" / "garmindb" / "data" / "DBs" / "garmin_activities.db"
    if not database.is_file():
        raise WeatherLookupError("GarminDB activities database is unavailable.")
    try:
        connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(activity_records)")
        }
        required = {"activity_id", "timestamp", "position_lat", "position_long"}
        if not required.issubset(columns):
            raise WeatherLookupError("GarminDB activity records do not include GPS fields.")
        rows = connection.execute(
            """
            SELECT timestamp, position_lat, position_long
            FROM activity_records
            WHERE activity_id = ?
            ORDER BY record
            """,
            (activity_id,),
        ).fetchall()
    except sqlite3.Error as error:
        raise WeatherLookupError("GarminDB activity records could not be read.") from error
    finally:
        if "connection" in locals():
            connection.close()

    return [
        {
            "timestamp_utc": parse_timestamp(row["timestamp"], default_timezone),
            "position_lat": normalize_coordinate(row["position_lat"], latitude=True),
            "position_long": normalize_coordinate(row["position_long"], latitude=False),
        }
        for row in rows
    ]


def resolve_records(
    root: Path,
    activity_file: Path | None,
    activity_id: str | None,
    default_timezone: str,
) -> tuple[list[dict[str, Any]], str]:
    if activity_file is not None:
        path = activity_file if activity_file.is_absolute() else root / activity_file
        path = path.resolve()
        if not path.is_file():
            raise WeatherLookupError("Activity file was not found.")
        if path.suffix.lower() == ".fit":
            return load_fit_records(path), "FIT GPS records"
        if path.suffix.lower() == ".gpx":
            return load_gpx_records(path, default_timezone), "GPX track points"
        raise WeatherLookupError("Activity file must be FIT or GPX.")

    if activity_id is None:
        raise WeatherLookupError("An activity file or Garmin activity ID is required.")
    fit_path = find_fit_file(root, activity_id)
    if fit_path:
        return load_fit_records(fit_path), "FIT GPS records"
    return load_garmindb_records(root, activity_id, default_timezone), "GarminDB GPS records"


def activity_window_and_location(
    records: list[dict[str, Any]], source: str
) -> tuple[dt.datetime, dt.datetime, float, float, dict[str, Any]]:
    timestamps = [
        value.astimezone(dt.timezone.utc)
        for record in records
        if isinstance((value := record.get("timestamp_utc")), dt.datetime)
        and value.tzinfo is not None
    ]
    positions = []
    for record in records:
        latitude = normalize_coordinate(record.get("position_lat"), latitude=True)
        longitude = normalize_coordinate(record.get("position_long"), latitude=False)
        if latitude is None or longitude is None or (latitude == 0 and longitude == 0):
            continue
        positions.append((latitude, longitude))
    if not timestamps:
        raise WeatherLookupError("The activity has no usable timestamps for weather matching.")
    if not positions:
        raise WeatherLookupError("The activity has no usable GPS points for weather matching.")

    latitude = round(statistics.median(point[0] for point in positions) / LOCATION_GRID_DEGREES) * LOCATION_GRID_DEGREES
    longitude = round(statistics.median(point[1] for point in positions) / LOCATION_GRID_DEGREES) * LOCATION_GRID_DEGREES
    location_metadata = {
        "source": source,
        "gps_points_used": len(positions),
        "method": "median route point quantized to a 0.05-degree grid before lookup",
        "coordinates_withheld": True,
    }
    return min(timestamps), max(timestamps), latitude, longitude, location_metadata


def fetch_hourly_weather(
    start: dt.datetime,
    end: dt.datetime,
    latitude: float,
    longitude: float,
    units: str,
) -> dict[str, Any]:
    parameters = {
        "latitude": f"{latitude:.2f}",
        "longitude": f"{longitude:.2f}",
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "hourly": ",".join(HOURLY_FIELDS),
        "timezone": "GMT",
        "temperature_unit": "fahrenheit" if units == "imperial" else "celsius",
        "wind_speed_unit": "mph" if units == "imperial" else "kmh",
        "precipitation_unit": "inch" if units == "imperial" else "mm",
    }
    request = urllib.request.Request(
        f"{API_ENDPOINT}?{urllib.parse.urlencode(parameters)}",
        headers={"User-Agent": "privacy-first-running-coach/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise WeatherLookupError(f"Historical weather service returned HTTP {error.code}.") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise WeatherLookupError("Historical weather service could not be reached.") from error
    if payload.get("error"):
        raise WeatherLookupError("Historical weather service rejected the request.")
    return payload


def numeric_summary(values: list[Any]) -> dict[str, float] | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return {
        "min": round(min(numeric), 1),
        "mean": round(statistics.mean(numeric), 1),
        "max": round(max(numeric), 1),
    }


def circular_mean(values: list[Any]) -> int | None:
    degrees = [float(value) for value in values if value is not None]
    if not degrees:
        return None
    sine = statistics.mean(math.sin(math.radians(value)) for value in degrees)
    cosine = statistics.mean(math.cos(math.radians(value)) for value in degrees)
    return int(round(math.degrees(math.atan2(sine, cosine)) % 360))


def summarize_weather(
    payload: dict[str, Any],
    start: dt.datetime,
    end: dt.datetime,
    location_metadata: dict[str, Any],
) -> dict[str, Any]:
    hourly = payload.get("hourly") or {}
    units = payload.get("hourly_units") or {}
    raw_times = hourly.get("time") or []
    times = [parse_timestamp(value, "UTC") for value in raw_times]
    lower = start.replace(minute=0, second=0, microsecond=0)
    upper = end.replace(minute=0, second=0, microsecond=0)
    indexes = [
        index for index, value in enumerate(times) if value is not None and lower <= value <= upper
    ]
    if not indexes and times:
        midpoint = start + (end - start) / 2
        valid_indexes = [index for index, value in enumerate(times) if value is not None]
        if valid_indexes:
            indexes = [min(valid_indexes, key=lambda index: abs(times[index] - midpoint))]
    if not indexes:
        raise WeatherLookupError("Historical weather response did not cover the activity window.")

    def selected(field: str) -> list[Any]:
        values = hourly.get(field) or []
        return [values[index] for index in indexes if index < len(values)]

    precipitation_values = [float(value) for value in selected("precipitation") if value is not None]
    weather_codes = sorted({int(value) for value in selected("weather_code") if value is not None})
    return {
        "source": "Open-Meteo Historical Weather API",
        "source_url": SOURCE_URL,
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "activity_window_utc": {"start": start.isoformat(), "end": end.isoformat()},
        "location": location_metadata,
        "hourly_samples": len(indexes),
        "conditions": {
            "temperature": numeric_summary(selected("temperature_2m")),
            "apparent_temperature": numeric_summary(selected("apparent_temperature")),
            "relative_humidity": numeric_summary(selected("relative_humidity_2m")),
            "dew_point": numeric_summary(selected("dew_point_2m")),
            "wind_speed": numeric_summary(selected("wind_speed_10m")),
            "wind_gusts": numeric_summary(selected("wind_gusts_10m")),
            "mean_wind_direction_degrees": circular_mean(selected("wind_direction_10m")),
            "precipitation_total_for_sampled_hours": round(sum(precipitation_values), 3),
            "weather_codes": weather_codes,
            "weather_code_labels": [
                WEATHER_CODE_LABELS.get(code, f"unknown code {code}") for code in weather_codes
            ],
        },
        "units": {
            "temperature": units.get("temperature_2m"),
            "apparent_temperature": units.get("apparent_temperature"),
            "relative_humidity": units.get("relative_humidity_2m"),
            "dew_point": units.get("dew_point_2m"),
            "wind_speed": units.get("wind_speed_10m"),
            "wind_gusts": units.get("wind_gusts_10m"),
            "precipitation": units.get("precipitation"),
        },
        "limitations": [
            "Gridded historical estimate, not an on-route weather-station measurement.",
            "Hourly samples can miss short-lived or highly localized conditions.",
            "One representative route location does not capture weather changes along a long route.",
        ],
    }


def print_text(result: dict[str, Any]) -> None:
    conditions = result["conditions"]
    units = result["units"]
    print(f"Source: {result['source']}")
    print(f"Location: {result['location']['method']} (coordinates withheld)")
    print(f"Activity window: {result['activity_window_utc']}")
    print(f"Temperature: {conditions['temperature']} {units['temperature'] or ''}")
    print(f"Apparent temperature: {conditions['apparent_temperature']} {units['apparent_temperature'] or ''}")
    print(f"Relative humidity: {conditions['relative_humidity']} {units['relative_humidity'] or ''}")
    print(f"Dew point: {conditions['dew_point']} {units['dew_point'] or ''}")
    print(f"Wind: {conditions['wind_speed']} {units['wind_speed'] or ''}; gusts {conditions['wind_gusts']}")
    print(f"Precipitation across sampled hours: {conditions['precipitation_total_for_sampled_hours']} {units['precipitation'] or ''}")
    print(f"Weather codes: {conditions['weather_codes']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve historical weather for a FIT, GPX, or GarminDB running activity."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--activity-file", type=Path)
    source.add_argument("--activity-id")
    parser.add_argument("--timezone", default="America/Los_Angeles")
    parser.add_argument("--units", choices=("imperial", "metric"), default="imperial")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.project_root.expanduser().resolve()
    try:
        records, source_name = resolve_records(
            root, args.activity_file, args.activity_id, args.timezone
        )
        start, end, latitude, longitude, location_metadata = activity_window_and_location(
            records, source_name
        )
        payload = fetch_hourly_weather(start, end, latitude, longitude, args.units)
        result = summarize_weather(payload, start, end, location_metadata)
    except (OSError, ValueError, WeatherLookupError) as error:
        parser.exit(2, f"ERROR: {error}\n")

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_text(result)


if __name__ == "__main__":
    main()
