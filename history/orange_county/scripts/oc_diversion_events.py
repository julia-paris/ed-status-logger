"""Download every diversion event behind Orange County (CA) EMS's public Power BI diversion dashboard.

Source page: https://www.ochealthinfo.com/providers-partners/emergency-medical-services/ems-system-reports/health-care-facilities
Dashboard "Diversion Dashboard: System" (data source: ReddiNet). Its data model contains one row per
diversion event; this script queries that table through the same public endpoint the dashboard uses.

    python3 history/orange_county/scripts/oc_diversion_events.py

Writes history/orange_county/oc_diversion_events.csv.

Timestamps: Power BI stores these as naive datetimes; they appear to be Pacific local time
(e.g. events at 23:57 on New Year's Eve), so they are written without a timezone as *_local.
Note: the query groups on all columns, so two events identical in every field would collapse into one.
"""
import csv
import datetime as dt
import gzip
import json
import os
import urllib.request

BASE = "https://wabi-us-gov-iowa-api.analysis.usgovcloudapi.net/public/reports/"
KEY = "2caa138a-eb83-4f9a-be03-638b7703246a"  # public resource key from the embed URL
COLS = ["Facility Name", "Diversion Category", "Started", "Ended", "Duration in Minutes",
        "Authority 1", "Authority 2", "Operator", "Comments"]
OUT_NAMES = ["facility", "category", "started_local", "ended_local", "duration_min",
             "authority1", "authority2", "operator", "comments"]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "oc_diversion_events.csv")
HDR = {"X-PowerBI-ResourceKey": KEY, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), headers=HDR)
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read()
        return json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)


def query(model, restart=None, count=30000):
    win = {"Count": count}
    if restart:
        win["RestartTokens"] = restart
    src = {"SourceRef": {"Source": "a"}}
    return {"version": "1.0.0", "cancelQueries": [], "modelId": model["id"], "queries": [{
        "QueryId": "", "ApplicationContext": {"DatasetId": model["dbName"], "Sources": [{"ReportId": "", "VisualId": ""}]},
        "Query": {"Commands": [{"SemanticQueryDataShapeCommand": {
            "Query": {"Version": 2, "From": [{"Name": "a", "Entity": "All Facilities", "Type": 0}],
                      "Select": [{"Column": {"Expression": src, "Property": c}, "Name": "a." + c} for c in COLS],
                      "OrderBy": [{"Direction": 1, "Expression": {"Column": {"Expression": src, "Property": "Started"}}}]},
            "Binding": {"Primary": {"Groupings": [{"Projections": list(range(len(COLS)))}]},
                        "DataReduction": {"DataVolume": 3, "Primary": {"Window": win}}, "Version": 1}}}]}}]}


def decode(ds):
    """Expand Power BI's DSR row compression (R = repeat-previous bitmask, Ø = null bitmask, value dictionaries)."""
    dicts, rows, prev, schema = ds.get("ValueDicts", {}), [], None, None
    for row in ds["PH"][0]["DM0"]:
        schema = row.get("S", schema)
        c, rep, nul, ci, vals = row.get("C", []), row.get("R", 0), row.get("Ø", 0), 0, []
        for i, col in enumerate(schema):
            if rep & (1 << i):
                v = prev[i]
            elif nul & (1 << i):
                v = None
            else:
                v = c[ci]; ci += 1
                if col.get("DN") and isinstance(v, int):
                    v = dicts[col["DN"]][v]
            vals.append(v)
        rows.append(vals)
        prev = vals
    return rows


def ts(ms):
    return None if ms is None else dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def main():
    model = call(KEY + "/modelsAndExploration?preferReadOnlySession=true")["models"][0]
    rows, rt = [], None
    while True:
        ds = call("querydata?synchronous=true", query(model, rt))["results"][0]["result"]["data"]["dsr"]["DS"][0]
        rows += decode(ds)
        rt = ds.get("RT")
        print(f"{len(rows)} rows", flush=True)
        if not rt:
            break
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(OUT_NAMES)
        for v in rows:
            w.writerow([v[0], v[1], ts(v[2]), ts(v[3]), v[4], v[5], v[6], v[7], v[8]])
    print("wrote", os.path.relpath(OUT), len(rows))


if __name__ == "__main__":
    main()
