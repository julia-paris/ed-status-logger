"""Flatten saved snapshots into analysis-ready CSVs in tables/.

    python3 logger/build_tables.py

Writes:
  tables/maryland_hospital_status.csv  one row per hospital per snapshot
  tables/maryland_units.csv            one row per EMS unit at / en route to a hospital per snapshot
  tables/newyork_ed_status.csv         one row per hospital per snapshot
  tables/georgia_status.csv            one row per hospital per snapshot (diversion, NEDOCS, ED beds)
  tables/georgia_beds.csv              one row per hospital per bed type per snapshot
  tables/georgia_specialties.csv       one row per hospital per specialty service per snapshot
"""
import csv
import glob
import gzip
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
    base = os.path.join(ROOT, "snapshots", source, "*", "*", "*")
    paths = glob.glob(os.path.join(base, "*.json")) + glob.glob(os.path.join(base, "*.json.gz"))
    for p in sorted(paths, key=os.path.basename):
        with (gzip.open(p, "rt", encoding="utf-8") if p.endswith(".gz") else open(p)) as f:
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


GA = ["fetched_at_utc", "dest_code", "hospital_name", "county", "region", "trauma_level", "stroke_level", "stemi_level",
      "eoc_status", "diversion_status", "diversion_reason", "diversion_comments", "diversion_updated_utc", "diversion_updated_by",
      "nedocs_score", "nedocs_description", "nedocs_time_local", "ed_beds_total", "ed_beds_available", "lat", "lon"]
GA_BEDS = ["fetched_at_utc", "dest_code", "bed_type", "total_beds", "available_staffed", "updated_on"]
GA_SPEC = ["fetched_at_utc", "dest_code", "specialty", "availability_status", "comment", "changed_on", "availability_begins",
           "availability_ends"]


def georgia():
    with open(os.path.join(OUT, "georgia_status.csv"), "w", newline="") as fs, \
         open(os.path.join(OUT, "georgia_beds.csv"), "w", newline="") as fb, \
         open(os.path.join(OUT, "georgia_specialties.csv"), "w", newline="") as fp:
        ws = csv.DictWriter(fs, GA); ws.writeheader()
        wb = csv.DictWriter(fb, GA_BEDS); wb.writeheader()
        wp = csv.DictWriter(fp, GA_SPEC); wp.writeheader()
        for s in snaps("georgia"):
            t = s["fetched_at_utc"]
            for h in s["data"].get("results", []):
                dv, nd = h.get("diversion") or {}, h.get("nedoc") or {}
                ed = next((b for b in h.get("beds") or [] if b.get("name", "").startswith("Emergency Department")), {})
                code = h.get("destCode")
                ws.writerow({"fetched_at_utc": t, "dest_code": code, "hospital_name": h.get("agencyName"),
                             "county": h.get("county"), "region": h.get("region"), "trauma_level": h.get("traumaLevel"),
                             "stroke_level": h.get("pA_StrokeLevel"), "stemi_level": h.get("pA_STEMILevel"),
                             "eoc_status": h.get("eocStatus"), "diversion_status": dv.get("status"),
                             "diversion_reason": dv.get("status_reason"), "diversion_comments": dv.get("status_comments"),
                             "diversion_updated_utc": dv.get("updated_on_utc"), "diversion_updated_by": dv.get("updated_by"),
                             "nedocs_score": nd.get("nedocs_score"), "nedocs_description": nd.get("description"),
                             "nedocs_time_local": nd.get("created_on_clientTime"), "ed_beds_total": ed.get("total_beds"),
                             "ed_beds_available": ed.get("available_staffed"), "lat": h.get("latitude"), "lon": h.get("longitude")})
                for b in h.get("beds") or []:
                    wb.writerow({"fetched_at_utc": t, "dest_code": code, "bed_type": b.get("name"), "total_beds": b.get("total_beds"),
                                 "available_staffed": b.get("available_staffed"), "updated_on": b.get("updated_on")})
                for sp in h.get("specialties") or []:
                    wp.writerow({"fetched_at_utc": t, "dest_code": code, "specialty": sp.get("name"),
                                 "availability_status": sp.get("availability_status"), "comment": sp.get("comment"),
                                 "changed_on": sp.get("changed_on"), "availability_begins": sp.get("availability_begins"),
                                 "availability_ends": sp.get("availability_ends")})


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    maryland()
    newyork()
    georgia()
    print("wrote", ", ".join(sorted(os.listdir(OUT))))
