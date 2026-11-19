"""Download San Francisco EMS Agency's hospital diversion and diversion-suspension datasets (DataSF).

    python3 history/san_francisco/scripts/sf_diversions.py

Writes, next to this script's parent folder:
  sf_hospital_diversions.csv   one row per diversion event (data.sf.gov t4sf-777q)
  sf_hospital_suspensions.csv  one row per citywide diversion suspension (data.sf.gov 6x9s-ipug)

Both are published monthly from ReddiNet data; times are San Francisco local time as published.
The data_loaded_at / data_as_of columns are dropped so the files only change when the data does.
"""
import csv
import io
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
DATASETS = {
    "sf_hospital_diversions.csv": ("t4sf-777q", "started, hospital_abbrev, diversion_category"),
    "sf_hospital_suspensions.csv": ("6x9s-ipug", "time_added"),
}
DROP = {"data_loaded_at", "data_as_of"}


def fetch(dataset, order):
    url = (f"https://data.sf.gov/resource/{dataset}.csv?$limit=1000000"
           f"&$order={urllib.parse.quote(order)}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ed-status-logger)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8")


def main():
    for name, (dataset, order) in DATASETS.items():
        rows = list(csv.DictReader(io.StringIO(fetch(dataset, order))))
        cols = [c for c in rows[0] if c not in DROP] if rows else []
        with open(os.path.join(OUT, name), "w", newline="") as f:
            w = csv.DictWriter(f, cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"{name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
