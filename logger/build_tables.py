"""Flatten saved snapshots into analysis-ready CSVs in tables/.

    python3 logger/build_tables.py

Writes:
  tables/maryland_hospital_status.csv  one row per hospital per snapshot
  tables/maryland_units.csv            one row per EMS unit at / en route to a hospital per snapshot
  tables/newyork_ed_status.csv         one row per hospital per snapshot
"""
import csv
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tables")

MD_HOSP = ["fetched_at_utc", "hospital_code", "hospital_name", "ed_census_level", "reroute", "code_black", "code_black_reason",
           "trauma_bypass", "capacity", "red", "yellow", "notes", "units_at_facility", "units_enroute",
           "min_stay_min", "max_stay_min", "lat", "lon"]
MD_UNIT = ["fetched_at_utc", "hospital_code", "jurisdiction", "agency", "unit", "incident_number", "is_enroute",
           "length_of_stay_min", "time_enroute_min"]
NY = ["fetched_at_utc", "source_updated_utc", "id", "hospital_name", "county", "ed_status", "reason", "comments", "color"]


def snaps(source):
    for p in sorted(glob.glob(os.path.join(ROOT, "snapshots", source, "*", "*", "*", "*.json"))):
        with open(p) as f:
            yield json.load(f)


def maryland():
    with open(os.path.join(OUT, "maryland_hospital_status.csv"), "w", newline="") as fh, \
         open(os.path.join(OUT, "maryland_units.csv"), "w", newline="") as fu:
        wh = csv.DictWriter(fh, MD_HOSP); wh.writeheader()
        wu = csv.DictWriter(fu, MD_UNIT); wu.writeheader()
        for s in snaps("maryland"):
            t = s["fetched_at_utc"]
            for h in s["data"].get("results", []):
                a = h.get("alerts") or {}
                name = (h.get("destinationName") or "").rsplit(" - ", 1)[0]
                wh.writerow({"fetched_at_utc": t, "hospital_code": h.get("destinationCode"), "hospital_name": name,
                             "ed_census_level": a.get("edCensusIndicatorScore"), "reroute": a.get("reroute"),
                             "code_black": a.get("codeBlack"), "code_black_reason": a.get("codeBlackReason"),
                             "trauma_bypass": a.get("traumaBypass"), "capacity": a.get("capacity"),
                             "red": a.get("red"), "yellow": a.get("yellow"), "notes": a.get("notes"),
                             "units_at_facility": h.get("numOfUnits"), "units_enroute": h.get("numOfUnitsEnroute"),
                             "min_stay_min": h.get("minStay"), "max_stay_min": h.get("maxStay"),
                             "lat": h.get("lat"), "lon": h.get("lon")})
                for u in h.get("units") or []:
                    wu.writerow({"fetched_at_utc": t, "hospital_code": h.get("destinationCode"),
                                 "jurisdiction": u.get("jurisdiction"), "agency": u.get("agencyName"),
                                 "unit": u.get("unitCallSign"), "incident_number": u.get("incidentNumber"),
                                 "is_enroute": u.get("isEnroute"), "length_of_stay_min": u.get("lengthOfStay"),
                                 "time_enroute_min": u.get("timeEnroute")})


def newyork():
    with open(os.path.join(OUT, "newyork_ed_status.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, NY); w.writeheader()
        for s in snaps("newyork"):
            d = s["data"]
            for h in d.get("statuses", []):
                w.writerow({"fetched_at_utc": s["fetched_at_utc"], "source_updated_utc": d.get("updateDateTime"),
                            "id": h.get("id"), "hospital_name": h.get("resourceName"), "county": h.get("county"),
                            "ed_status": h.get("edStatus"), "reason": h.get("edStatusReason"), "comments": h.get("comments"),
                            "color": h.get("colorCode")})


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    maryland()
    newyork()
    print("wrote", ", ".join(sorted(os.listdir(OUT))))
