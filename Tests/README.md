# Synthetic FlightStats test data

These fixtures contain entirely synthetic flight data. They are intended
for parser, calculation, GUI and performance testing without using private
pilot logbooks.

## Fixtures

- `synthetic_normal_1000.csv` — deterministic 1,000-flight baseline.
- `synthetic_edge_1000.csv` — mixed aircraft, spelling variants, and
  deliberate LIS/NDR route coverage.
- `synthetic_stress_10000.csv` — 10,000-flight stress dataset.

Each CSV has a matching JSON manifest containing expected aggregate values.

## Regenerate

From the project root:

```bash
python Tests/generate_test_logbook_csv.py --flights 1000 --seed 42   --output Tests/fixtures/synthetic_edge_1000.csv
```

Changing the seed creates a different but reproducible dataset.
