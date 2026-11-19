"""Pull EDAS 'Chronological Alert Log by Hospital' for every hospital via the public Bold Reports service."""
import json, sys, uuid, time, csv, io, os, datetime as dt
import urllib.request, urllib.parse

BASE = "https://edas.miemss.org/open-data/api/reportService"
REPORT = "edas-chronological-report.rdl"
ALERTS = (["Capacity", "CodeBlack", "Reroute", "TraumaBypass"], ["Capacity", "Code Black", "Reroute", "Trauma Bypass"])
FMT = os.environ.get("FMT","XML")
UA = {"User-Agent": "Mozilla/5.0 (research data pull)"}

def post_json(body):
    req = urllib.request.Request(BASE + "/PostReportAction", data=json.dumps(body).encode(),
                                 headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read().decode()

def post_form(fields):
    req = urllib.request.Request(BASE + "/PostFormReportAction", data=urllib.parse.urlencode(fields).encode(),
                                 headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()

def date_param(name, d):
    return {"allowBlank": False, "name": name, "values": [f"{d.month}/{d.day}/{d.year}"], "labels": [f"{d.month}/{d.day}/{d.year}"],
            "nullable": False, "dateTimeInfo": {"Year": d.year, "Month": d.month, "Day": d.day, "Hour": 0, "Minute": 0, "Second": 0}, "operator": ""}

def params(code, label, start, end):
    return [{"allowBlank": False, "name": "HospitalCode", "values": [code], "labels": [label], "nullable": False, "dateTimeInfo": {}, "operator": ""},
            {"allowBlank": False, "name": "AlertTypes", "values": ALERTS[0], "labels": ALERTS[1], "nullable": False, "dateTimeInfo": {}, "operator": ""},
            date_param("StartDate", start), date_param("EndDate", end)]

def load(tok, p):
    return json.loads(post_json({"reportAction": "ReportLoad", "parameters": p, "isReloadReport": False, "controlId": "reportviewer1",
        "reportPath": REPORT, "enableVirtualEvaluation": False, "reportServerUrl": "", "processingMode": "remote", "locale": "en-US",
        "enableSearchText": True, "reportViewerToken": tok, "reportViewerClientId": tok}))

def export_csv(code, label, start, end):
    tok = str(uuid.uuid4())
    p = params(code, label, start, end)
    load(tok, p)
    post_json({"reportAction": "GetParameters", "parameters": p, "dataSources": None, "reportViewerToken": tok, "reportViewerClientId": tok})
    post_json({"reportAction": "GetPageModel", "refresh": True, "dataRefresh": False, "pageindex": 1, "pageInit": False, "isPrint": False,
               "dataSources": None, "parameters": p, "reportViewerToken": tok, "reportViewerClientId": tok})
    r = json.loads(post_json({"reportAction": "Export", "controlID": tok, "resourcetype": FMT, "serviceAuthorizationToken": "",
                              "isPrint": False, "reportName": "", "pageindex": 1, "reportViewerToken": tok, "reportViewerClientId": tok}))
    while r.get("inProgress") == "inProgress":
        time.sleep(1)
        r = json.loads(post_json({"reportAction": "Export", "downloadreportid": r.get("downloadreportid"), "reportViewerToken": tok, "reportViewerClientId": tok}))
    data = post_form({"reportAction": "Export", "controlID": tok, "serviceAuthorizationToken": "", "isPrint": "false",
                      "downloadreportid": r.get("downloadreportid", ""), "sessionToken": "null", "serverUrl": ""})
    return data, r

def hospitals():
    tok = str(uuid.uuid4())
    p = params("221", "Anne Arundel Medical Center", dt.date(2025, 1, 1), dt.date.today())
    load(tok, p)
    r = json.loads(post_json({"reportAction": "GetParameters", "parameters": p, "dataSources": None, "reportViewerToken": tok, "reportViewerClientId": tok}))
    hp = next(x for x in r["parameters"] if x["Name"] == "HospitalCode")
    return list(zip(hp["AvailableValues"], hp["AvailableLabels"]))

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "list":
        print(json.dumps(hospitals()))
    elif mode == "one":
        data, r = export_csv(sys.argv[2], sys.argv[3], dt.date(2018, 1, 1), dt.date.today())
        print(json.dumps({k: v for k, v in r.items() if k != "reportPageModel"})[:600]); print(data[:1500].decode(errors="replace"))

def alert_types():
    tok = str(uuid.uuid4())
    p = params("221", "Anne Arundel Medical Center", dt.date(2025, 1, 1), dt.date.today())
    load(tok, p)
    r = json.loads(post_json({"reportAction": "GetParameters", "parameters": p, "dataSources": None, "reportViewerToken": tok, "reportViewerClientId": tok}))
    a = next(x for x in r["parameters"] if x["Name"] == "AlertTypes")
    return a["AvailableValues"], a["AvailableLabels"]

def run_all(outdir, start, end):
    import xml.etree.ElementTree as ET
    global ALERTS
    ALERTS = alert_types()
    print("alert types:", ALERTS[0], file=sys.stderr)
    rows = []
    for code, label in hospitals():
        for attempt in range(3):
            try:
                data, _ = export_csv(code, label, start, end); break
            except Exception as e:
                print("retry", code, e, file=sys.stderr); time.sleep(3)
        else:
            print("FAILED", code, label, file=sys.stderr); continue
        open(os.path.join(outdir, f"{code}.xml"), "wb").write(data)
        root = ET.fromstring(data.decode("utf-8-sig"))
        n = 0
        for t in root.iter("Tablix4"):
            if "TextBox31" in t.attrib:
                a = t.attrib
                def p(s): return dt.datetime.strptime(s, "%m/%d/%Y %I:%M:%S %p").isoformat(sep=" ") if s else ""
                rows.append({"hospital_code": code, "hospital_name": a.get("TextBox38", label), "alert_type": a.get("TextBox2", ""),
                             "start": p(a.get("TextBox39", "")), "end": p(a.get("TextBox43", "")), "duration_hours": a.get("TextBox41", "")})
                n += 1
        print(f"{code}\t{label}\t{n}", file=sys.stderr)
        time.sleep(0.5)
    return rows

if __name__ == "__main__" and sys.argv[1] == "all":
    rows = run_all(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw_alert_xml"), dt.date(2018, 1, 1), dt.date.today())
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edas_alert_log.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("rows:", len(rows), file=sys.stderr)
