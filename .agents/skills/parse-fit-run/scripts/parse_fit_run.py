#!/usr/bin/env python3
"""Parse running FIT files into coaching-friendly metrics.

This is a small dependency-free decoder for the FIT message subset used in
run reviews. It is not a complete FIT SDK replacement.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import struct
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


FIT_EPOCH = datetime(1989, 12, 31, tzinfo=timezone.utc)
METERS_PER_MILE = 1609.344

GLOBAL_RECORD = 20
GLOBAL_LAP = 19
GLOBAL_SESSION = 18
GLOBAL_ACTIVITY = 34

BASE_TYPES = {
    0x00: ("enum", 1, "B", 0xFF),
    0x01: ("sint8", 1, "b", 0x7F),
    0x02: ("uint8", 1, "B", 0xFF),
    0x83: ("sint16", 2, "h", 0x7FFF),
    0x84: ("uint16", 2, "H", 0xFFFF),
    0x85: ("sint32", 4, "i", 0x7FFFFFFF),
    0x86: ("uint32", 4, "I", 0xFFFFFFFF),
    0x07: ("string", 1, None, None),
    0x88: ("float32", 4, "f", None),
    0x89: ("float64", 8, "d", None),
    0x0A: ("uint8z", 1, "B", 0),
    0x8B: ("uint16z", 2, "H", 0),
    0x8C: ("uint32z", 4, "I", 0),
    0x0D: ("byte", 1, None, None),
    0x8E: ("sint64", 8, "q", 0x7FFFFFFFFFFFFFFF),
    0x8F: ("uint64", 8, "Q", 0xFFFFFFFFFFFFFFFF),
    0x90: ("uint64z", 8, "Q", 0),
}


def decode_value(raw: bytes, base_type: int, endian: str):
    key = base_type if base_type in BASE_TYPES else base_type & 0x1F
    if key not in BASE_TYPES:
        return raw.hex()
    name, size, fmt, invalid = BASE_TYPES[key]
    if name == "string":
        return raw.split(b"\x00", 1)[0].decode("utf-8", "replace")
    if name == "byte":
        return raw.hex()

    values = []
    for i in range(len(raw) // size):
        chunk = raw[i * size : (i + 1) * size]
        value = struct.unpack(endian + fmt, chunk)[0]
        values.append(None if invalid is not None and value == invalid else value)
    if not values:
        return None
    return values[0] if len(values) == 1 else values


def fit_datetime(value):
    if value is None:
        return None
    return FIT_EPOCH + timedelta(seconds=value)


def semicircles_to_degrees(value):
    if value is None:
        return None
    return value * (180.0 / 2**31)


def meters_to_miles(meters):
    if meters is None:
        return None
    return meters / METERS_PER_MILE


def format_duration(seconds):
    if seconds is None:
        return "NA"
    seconds = int(round(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_pace(seconds_per_mile):
    if seconds_per_mile is None or not math.isfinite(seconds_per_mile):
        return "NA"
    seconds = int(round(seconds_per_mile))
    return f"{seconds // 60}:{seconds % 60:02d}/mi"


def mean_or_none(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


def round_or_none(value, digits=1):
    if value is None:
        return None
    return round(value, digits)


def parse_fit(path: Path):
    data = path.read_bytes()
    if len(data) < 14 or data[8:12] != b".FIT":
        raise ValueError(f"{path} does not look like a FIT file")

    header_size = data[0]
    data_size = struct.unpack("<I", data[4:8])[0]
    pos = header_size
    end = header_size + data_size
    local_defs = {}
    messages = []
    last_timestamp = None

    while pos < end:
        header = data[pos]
        pos += 1

        if header & 0x80:
            local_id = (header >> 5) & 0x03
            time_offset = header & 0x1F
            global_msg, endian, fields, dev_fields = local_defs[local_id]
            values = {}
            for field_num, size, base_type in fields:
                values[field_num] = decode_value(data[pos : pos + size], base_type, endian)
                pos += size
            for _field_num, size, _dev_idx in dev_fields:
                pos += size
            if last_timestamp is not None:
                new_timestamp = (last_timestamp & ~0x1F) + time_offset
                if new_timestamp <= last_timestamp - 16:
                    new_timestamp += 32
                values[253] = new_timestamp
                last_timestamp = new_timestamp
            messages.append((global_msg, values))
            continue

        is_definition = bool(header & 0x40)
        has_developer_fields = bool(header & 0x20)
        local_id = header & 0x0F

        if is_definition:
            architecture = data[pos + 1]
            pos += 2
            endian = ">" if architecture else "<"
            global_msg = struct.unpack(endian + "H", data[pos : pos + 2])[0]
            pos += 2
            field_count = data[pos]
            pos += 1
            fields = []
            for _ in range(field_count):
                fields.append((data[pos], data[pos + 1], data[pos + 2]))
                pos += 3
            dev_fields = []
            if has_developer_fields:
                dev_count = data[pos]
                pos += 1
                for _ in range(dev_count):
                    dev_fields.append((data[pos], data[pos + 1], data[pos + 2]))
                    pos += 3
            local_defs[local_id] = (global_msg, endian, fields, dev_fields)
            continue

        global_msg, endian, fields, dev_fields = local_defs[local_id]
        values = {}
        for field_num, size, base_type in fields:
            values[field_num] = decode_value(data[pos : pos + size], base_type, endian)
            pos += size
        for _field_num, size, _dev_idx in dev_fields:
            pos += size
        if values.get(253) is not None:
            last_timestamp = values[253]
        messages.append((global_msg, values))

    return messages


def normalized_records(messages):
    records = []
    for global_msg, fields in messages:
        if global_msg != GLOBAL_RECORD:
            continue
        timestamp = fit_datetime(fields.get(253))
        distance_m = fields.get(5)
        speed_mps = fields.get(29, fields.get(6))
        altitude_m = fields.get(30, fields.get(2))
        records.append(
            {
                "timestamp_utc": timestamp,
                "distance_m": distance_m / 100.0 if distance_m is not None else None,
                "heart_rate": fields.get(3),
                "cadence_single": fields.get(4),
                "speed_mps": speed_mps / 1000.0 if speed_mps is not None else None,
                "altitude_m": altitude_m / 5.0 - 500.0 if altitude_m is not None else None,
                "position_lat": semicircles_to_degrees(fields.get(0)),
                "position_long": semicircles_to_degrees(fields.get(1)),
                "power": fields.get(7),
            }
        )
    return [record for record in records if record["timestamp_utc"] is not None]


def summarize_session(messages, tz):
    sessions = [fields for global_msg, fields in messages if global_msg == GLOBAL_SESSION]
    summaries = []
    for fields in sessions:
        start = fit_datetime(fields.get(2))
        timer_s = fields.get(8) / 1000.0 if fields.get(8) is not None else None
        elapsed_s = fields.get(7) / 1000.0 if fields.get(7) is not None else None
        distance_m = fields.get(9) / 100.0 if fields.get(9) is not None else None
        distance_mi = meters_to_miles(distance_m)
        summaries.append(
            {
                "start_utc": start.isoformat() if start else None,
                "start_local": start.astimezone(tz).isoformat() if start else None,
                "distance_mi": round_or_none(distance_mi, 3),
                "timer_time": format_duration(timer_s),
                "elapsed_time": format_duration(elapsed_s),
                "pace": format_pace(timer_s / distance_mi if timer_s and distance_mi else None),
                "max_heart_rate": fields.get(16),
                "avg_cadence_field": fields.get(17),
                "max_cadence_field": fields.get(18),
                "calories": fields.get(11),
                "sport": fields.get(5),
                "subsport": fields.get(6),
            }
        )
    return summaries


def summarize_zones(records, zone_cutoffs):
    names = ["Z1", "Z2", "Z3", "Z4", "Z5"]
    ranges = [
        (names[0], -math.inf, zone_cutoffs[0]),
        (names[1], zone_cutoffs[0], zone_cutoffs[1]),
        (names[2], zone_cutoffs[1], zone_cutoffs[2]),
        (names[3], zone_cutoffs[2], zone_cutoffs[3]),
        (names[4], zone_cutoffs[3], math.inf),
    ]
    seconds = {name: 0.0 for name in names}
    total = 0.0
    for current, following in zip(records, records[1:]):
        hr = current["heart_rate"]
        if hr is None:
            continue
        interval = (following["timestamp_utc"] - current["timestamp_utc"]).total_seconds()
        if interval <= 0 or interval > 10:
            continue
        total += interval
        for name, low, high in ranges:
            if low <= hr < high:
                seconds[name] += interval
                break
    return {
        "cutoffs": zone_cutoffs,
        "seconds": {name: round(value, 1) for name, value in seconds.items()},
        "minutes": {name: round(value / 60.0, 1) for name, value in seconds.items()},
        "percent": {name: round((value / total * 100.0), 1) if total else 0 for name, value in seconds.items()},
        "total_seconds": round(total, 1),
    }


def segment_summary(records, start_m, end_m):
    points = [
        record
        for record in records
        if record["distance_m"] is not None and start_m <= record["distance_m"] <= end_m
    ]
    if len(points) < 2:
        return None
    duration_s = (points[-1]["timestamp_utc"] - points[0]["timestamp_utc"]).total_seconds()
    distance_mi = (points[-1]["distance_m"] - points[0]["distance_m"]) / METERS_PER_MILE
    hrs = [point["heart_rate"] for point in points if point["heart_rate"] is not None]
    cads = [point["cadence_single"] for point in points if point["cadence_single"] not in (None, 0)]
    return {
        "distance_mi": round(distance_mi, 2),
        "time": format_duration(duration_s),
        "pace": format_pace(duration_s / distance_mi if distance_mi else None),
        "avg_heart_rate": round_or_none(mean_or_none(hrs), 1),
        "avg_cadence_single": round_or_none(mean_or_none(cads), 1),
        "avg_spm": round_or_none(mean_or_none(cads) * 2 if cads else None, 1),
    }


def build_splits(records, total_distance_m):
    targets = [METERS_PER_MILE * i for i in range(1, int(total_distance_m / METERS_PER_MILE) + 1)]
    if total_distance_m / METERS_PER_MILE - int(total_distance_m / METERS_PER_MILE) > 0.03:
        targets.append(total_distance_m)

    splits = []
    split_start_time = records[0]["timestamp_utc"]
    last_target_m = 0.0
    cursor = 0
    for target_m in targets:
        cross_time = None
        for i in range(cursor, len(records)):
            distance_m = records[i]["distance_m"]
            if distance_m is None or distance_m < target_m:
                continue
            current = records[i]
            before = records[i - 1] if i > 0 else current
            d0 = before["distance_m"]
            d1 = current["distance_m"]
            fraction = 0 if d1 == d0 else (target_m - d0) / (d1 - d0)
            cross_time = before["timestamp_utc"] + (current["timestamp_utc"] - before["timestamp_utc"]) * fraction
            cursor = max(i - 1, 0)
            break
        if cross_time is None:
            continue

        split_seconds = (cross_time - split_start_time).total_seconds()
        split_miles = (target_m - last_target_m) / METERS_PER_MILE
        points = [
            record
            for record in records
            if record["distance_m"] is not None and last_target_m <= record["distance_m"] <= target_m
        ]
        hrs = [point["heart_rate"] for point in points if point["heart_rate"] is not None]
        cads = [point["cadence_single"] for point in points if point["cadence_single"] not in (None, 0)]
        splits.append(
            {
                "ending_mile": round(target_m / METERS_PER_MILE, 2),
                "distance_mi": round(split_miles, 2),
                "time": format_duration(split_seconds),
                "pace": format_pace(split_seconds / split_miles if split_miles else None),
                "avg_heart_rate": round_or_none(mean_or_none(hrs), 1),
                "avg_cadence_single": round_or_none(mean_or_none(cads), 1),
                "avg_spm": round_or_none(mean_or_none(cads) * 2 if cads else None, 1),
            }
        )
        split_start_time = cross_time
        last_target_m = target_m
    return splits


def summarize_records(records, tz, zone_cutoffs):
    if not records:
        return {}

    start = records[0]["timestamp_utc"]
    end = records[-1]["timestamp_utc"]
    distances = [record["distance_m"] for record in records if record["distance_m"] is not None]
    total_distance_m = max(distances) if distances else None
    total_miles = meters_to_miles(total_distance_m)
    duration_s = (end - start).total_seconds()
    hrs = [record["heart_rate"] for record in records if record["heart_rate"] is not None]
    cads = [record["cadence_single"] for record in records if record["cadence_single"] not in (None, 0)]
    powers = [record["power"] for record in records if record["power"] is not None]
    alts = [record["altitude_m"] for record in records if record["altitude_m"] is not None]

    halves = {}
    if total_distance_m:
        halves["first_half"] = segment_summary(records, 0, total_distance_m / 2.0)
        halves["second_half"] = segment_summary(records, total_distance_m / 2.0, total_distance_m)

    return {
        "start_utc": start.isoformat(),
        "start_local": start.astimezone(tz).isoformat(),
        "end_local": end.astimezone(tz).isoformat(),
        "distance_mi": round_or_none(total_miles, 3),
        "duration": format_duration(duration_s),
        "pace": format_pace(duration_s / total_miles if total_miles else None),
        "avg_heart_rate": round_or_none(mean_or_none(hrs), 1),
        "max_heart_rate": max(hrs) if hrs else None,
        "min_heart_rate": min(hrs) if hrs else None,
        "avg_cadence_single": round_or_none(mean_or_none(cads), 1),
        "avg_spm": round_or_none(mean_or_none(cads) * 2 if cads else None, 1),
        "max_cadence_single": max(cads) if cads else None,
        "avg_power": round_or_none(mean_or_none(powers), 1),
        "max_power": max(powers) if powers else None,
        "altitude_range_m": round_or_none(max(alts) - min(alts), 1) if alts else None,
        "zones": summarize_zones(records, zone_cutoffs),
        "halves": halves,
        "splits": build_splits(records, total_distance_m) if total_distance_m else [],
    }


def print_summary(result):
    record = result.get("record_summary", {})
    print(f"File: {result['file']}")
    print(f"Messages: {result['message_counts']}")
    print(
        "Record summary: "
        f"{record.get('start_local')} | {record.get('distance_mi')} mi | "
        f"{record.get('duration')} | {record.get('pace')} | "
        f"avg HR {record.get('avg_heart_rate')} | max HR {record.get('max_heart_rate')} | "
        f"avg cadence {record.get('avg_cadence_single')} single / {record.get('avg_spm')} spm"
    )
    zones = record.get("zones", {})
    if zones:
        print(f"HR zone percent: {zones.get('percent')}")
    halves = record.get("halves", {})
    if halves:
        print(f"First half: {halves.get('first_half')}")
        print(f"Second half: {halves.get('second_half')}")
    if record.get("splits"):
        print("Splits:")
        for split in record["splits"]:
            print(f"  {split}")


def main():
    parser = argparse.ArgumentParser(description="Parse a running FIT file for coaching metrics.")
    parser.add_argument("fit_file", type=Path)
    parser.add_argument("--timezone", default="America/Los_Angeles")
    parser.add_argument(
        "--zones",
        default="138,154,169,184",
        help="Comma-separated HR cutoffs for Z1/Z2/Z3/Z4/Z5. Default matches the running project.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()

    zone_cutoffs = [int(value) for value in args.zones.split(",")]
    if len(zone_cutoffs) != 4:
        raise SystemExit("--zones must contain exactly four comma-separated cutoffs")

    try:
        tz = ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError:
        parser.error(
            f"time zone {args.timezone!r} is unavailable; install the Python tzdata "
            "package when the operating system does not provide IANA time zones"
        )
    messages = parse_fit(args.fit_file)
    records = normalized_records(messages)
    message_counts = Counter(global_msg for global_msg, _fields in messages)
    result = {
        "file": str(args.fit_file),
        "message_counts": dict(sorted(message_counts.items())),
        "session_summary": summarize_session(messages, tz),
        "record_summary": summarize_records(records, tz, zone_cutoffs),
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_summary(result)


if __name__ == "__main__":
    main()
