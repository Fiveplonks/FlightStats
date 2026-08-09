#!/usr/bin/env python3
"""Generate deterministic synthetic FlightStats logbooks for testing."""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path


AIRPORTS = [
    ("EHAM", "AMS"), ("LPPT", "LIS"), ("GMMW", "NDR"),
    ("EGLL", "LHR"), ("EGCC", "MAN"), ("LEMD", "MAD"),
    ("LFPG", "CDG"), ("EDDF", "FRA"), ("EDDM", "MUC"),
    ("LOWW", "VIE"), ("LSZH", "ZRH"), ("LIRF", "FCO"),
    ("LEBL", "BCN"), ("LPPR", "OPO"), ("LPMA", "FNC"),
    ("LTFM", "IST"),
]

AIRCRAFT = [
    ("B737-800", ["800", "737-800", "B737-800"]),
    ("B737-8200", ["8200", "737-8200", "B737-8200", "B38M", "737 MAX 8"]),
    ("B737-700", ["737-700", "B737-700"]),
    ("B737-900", ["B737-900"]),
    ("A319", ["A319"]),
    ("A320", ["A320"]),
    ("A330-200", ["A330-200"]),
    ("A330-900", ["A330-900"]),
    ("E190", ["E190"]),
    ("E195", ["E195"]),
    ("CRJ900", ["CRJ900"]),
    ("DH8D", ["DH8D"]),
    ("ATR72", ["ATR72"]),
    ("PA28", ["PA28"]),
    ("PA34", ["PA34"]),
    ("PA44", ["PA44"]),
    ("EA300L", ["EA300L"]),
]

FORCED_ROUTES = [
    ("LIS", "NDR"),
    ("NDR", "LIS"),
    ("AMS", "LIS"),
    ("LIS", "AMS"),
    ("NDR", "AMS"),
    ("AMS", "NDR"),
]


def generate_rows(count: int, seed: int):
    rng = random.Random(seed)
    rows = []

    for n in range(count):
        flight_date = date(2020, 1, 1) + timedelta(days=n // 2)

        if n < len(FORCED_ROUTES):
            departure, arrival = FORCED_ROUTES[n]
        else:
            _, departure = rng.choice(AIRPORTS)
            _, arrival = rng.choice(AIRPORTS)
            while arrival == departure:
                _, arrival = rng.choice(AIRPORTS)

        canonical, variants = AIRCRAFT[n % len(AIRCRAFT)]
        aircraft = variants[n % len(variants)]

        # Deliberately operate the same routes with different aircraft.
        if n % 37 == 0:
            departure, arrival = "LIS", "NDR"
        elif n % 37 == 1:
            departure, arrival = "NDR", "LIS"

        hour = rng.randrange(0, 24)
        minute = rng.choice(range(0, 60, 5))

        if canonical in {"PA28", "PA34", "PA44", "EA300L"}:
            block = rng.randrange(25, 100)
        elif canonical in {"A330-200", "A330-900"}:
            block = rng.randrange(180, 620)
        elif canonical in {"DH8D", "ATR72", "E190", "E195", "CRJ900"}:
            block = rng.randrange(45, 210)
        else:
            block = rng.randrange(55, 300)

        arrival_total = hour * 60 + minute + block

        rows.append({
            "date": flight_date.isoformat(),
            "departure": departure,
            "departure_time": f"{hour:02d}:{minute:02d}",
            "flight_number": f"FS{1000 + n % 9000:04d}",
            "arrival": arrival,
            "arrival_time": (
                f"{(arrival_total // 60) % 24:02d}:"
                f"{arrival_total % 60:02d}"
            ),
            "aircraft": aircraft,
            "registration": f"NTS{n % 10 + 1:02d}",
            "_canonical_aircraft": canonical,
            "_block_minutes": block,
        })

    return rows


def write_dataset(output: Path, rows, seed: int):
    fields = [
        "date", "departure", "departure_time", "flight_number",
        "arrival", "arrival_time", "aircraft", "registration",
    ]

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})

    aircraft_counts = {}
    for row in rows:
        key = row["_canonical_aircraft"]
        aircraft_counts[key] = aircraft_counts.get(key, 0) + 1

    manifest = {
        "seed": seed,
        "flights": len(rows),
        "total_block_minutes": sum(
            row["_block_minutes"] for row in rows
        ),
        "aircraft_type_counts": aircraft_counts,
        "forced_airport_tests": {
            "LIS": "LPPT",
            "NDR": "GMMW",
            "AMS": "EHAM",
        },
        "notes": [
            "Synthetic data only; contains no personal logbook data.",
            "Aircraft variants intentionally differ in spelling.",
            "LIS/NDR routes deliberately repeat with different aircraft.",
        ],
    }

    output.with_suffix(".json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--flights", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output = args.output or Path(
        f"synthetic_{args.flights}_{args.seed}.csv"
    )

    rows = generate_rows(args.flights, args.seed)
    write_dataset(output, rows, args.seed)

    print(f"Created {output}")
    print(f"Created {output.with_suffix('.json')}")
    print(f"Flights: {len(rows)}")


if __name__ == "__main__":
    main()
