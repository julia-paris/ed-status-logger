"""Accumulate Sacramento County EMS Agency's ambulance patient offload time (APOT) data.

    python3 history/sacramento/scripts/sac_apot.py

The county's open data layers (data.saccounty.gov, ArcGIS) only hold the current year's months and the
last two weeks, overwriting older weeks. Each run merges what is published now into these files, so
history builds up over time (later pulls replace earlier values for the same key, picking up late records):

  sac_apot_monthly_hospital.csv   year, month, hospital: 90th percentile and average APOT, patient count
  sac_apot_monthly_system.csv     year, month: same, county-wide
  sac_apot_weekly_ranges.csv      week, hospital, APOT range (e.g. "> 20 to <= 60" minutes): patient count
  sac_apot_weekly_p90.csv         week, hospital: 90th percentile APOT, transfers with a completed ePCR

Monthly layers give no year; it is taken as the year of the pull (or the year before, for a month later
than the current one). No diversion data is published for Sacramento.
"""
import csv
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
BASE = "https://services1.arcgis.com/5NARefyPVtAeuJPU/arcgis/rest/services/{}/FeatureServer/0/query?"
UA = "Mozilla/5.0 (compatible; ed-status-logger; research archive)"


def layer(name):
    q = urllib.parse.urlencode({"where": "1=1", "outFields": "*", "f": "json", "resultRecordCount": 5000})
    req = urllib.request.Request(BASE.format(name) + q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if "error" in d:
        raise RuntimeError(f"{name}: {d['error']}")
    return [f["attributes"] for f in d["features"]]


def merge(fname, cols, key, new):
    path = os.path.join(OUT, fname)
    rows = {}
    if os.path.exists(path):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                rows[tuple(r[k] for k in key)] = r
    for r in new:
        r = {c: "" if r.get(c) is None else str(r[c]) for c in cols}
        if all(r[k] for k in key):
            rows[tuple(r[k] for k in key)] = r
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows[k] for k in sorted(rows))
    print(f"{fname}: {len(rows)} rows")


def month_year(label, today):
    m = int(label.split(" - ")[0])
    return (today.year if m <= today.month else today.year - 1), m


def main():
    today = dt.date.today()
    mh = []
    for a in layer("Monthly_Hospital_EMS_APOT_Data"):
        y, m = month_year(a["Month_Number_Name"], today)
        mh.append({"year": y, "month": f"{m:02d}", "hospital": a["Destination_Hospital"],
                   "apot_p90": a["APOT_90th_Percentile_HH_MM_SS"], "apot_mean": a["APOT_Average_in_HH_MM_SS"],
                   "patients": a["Patient_Count"]})
    merge("sac_apot_monthly_hospital.csv", ["year", "month", "hospital", "apot_p90", "apot_mean", "patients"],
          ["year", "month", "hospital"], mh)

    ms = []
    for a in layer("Monthly_System_EMS_APOT_Data"):
        y, m = month_year(a["Month_Number___Name"], today)
        ms.append({"year": y, "month": f"{m:02d}", "apot_p90": a["APOT_90th_Percentile_HH_MM_SS"],
                   "apot_mean": a["APOT_Average_in_HH_MM_SS"], "patients": a["Patient_Count"]})
    merge("sac_apot_monthly_system.csv", ["year", "month", "apot_p90", "apot_mean", "patients"], ["year", "month"], ms)

    wr = []
    for name in ("EMS_Weekly_APOT_Range_Hospital_Data_of_Previous_Week", "EMS_Weekly_APOT_Range_Hospital_Data"):
        for a in layer(name):  # newer week last, so it wins on overlap
            start = dt.datetime.strptime(a["Incident_Week___Year"].split("-")[0].strip(), "%B %d, %Y").date()
            wr.append({"week_start": start.isoformat(), "week_label": a["Incident_Week___Year"],
                       "hospital": a["Disposition_Destination_Name_De"], "range_order": a["APOT_Range_Order"],
                       "apot_range_min": a["APOT_Range"], "patients": a["Patient_Count"]})
    merge("sac_apot_weekly_ranges.csv", ["week_start", "week_label", "hospital", "range_order", "apot_range_min", "patients"],
          ["week_start", "hospital", "range_order"], wr)

    wp = [{"week": a["Week_Number_Year"], "hospital": a["Destination_Hospital"],
           "apot_p90": a["APOT_90th_Percentile_in_Minutes_per_Hospital"],
           "transfers_with_epcr": a["Count_of_Patient_Transfer_of_Care_with_Completed_ePCR"]}
          for a in layer("EMS_Dashboard")]
    merge("sac_apot_weekly_p90.csv", ["week", "hospital", "apot_p90", "transfers_with_epcr"], ["week", "hospital"], wp)


if __name__ == "__main__":
    main()
