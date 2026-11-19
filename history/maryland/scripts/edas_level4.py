"""Pull EDAS 'ED Census Index Level 4 Report' (all regions/hospitals) as XML via the public Bold Reports service."""
import sys, json, uuid, time, datetime as dt
sys.path.insert(0, __import__("os").path.dirname(__file__))
import edas_pull as E

REPORT = "edas-ed-census-index-level4-report.rdl"

def blank(name):
    return {"allowBlank": True, "name": name, "values": [], "labels": [], "nullable": False, "dateTimeInfo": {}, "operator": ""}

def export(start, end, fmt="XML"):
    tok = str(uuid.uuid4())
    p = [blank("Region"), blank("HospitalCode"), E.date_param("StartDate", start), E.date_param("EndDate", end)]
    base = {"reportViewerToken": tok, "reportViewerClientId": tok}
    E.post_json({"reportAction": "ReportLoad", "parameters": p, "isReloadReport": False, "controlId": "reportviewer1", "reportPath": REPORT,
                 "enableVirtualEvaluation": False, "reportServerUrl": "", "processingMode": "remote", "locale": "en-US", "enableSearchText": True, **base})
    E.post_json({"reportAction": "GetParameters", "parameters": p, "dataSources": None, **base})
    E.post_json({"reportAction": "GetPageModel", "refresh": True, "dataRefresh": False, "pageindex": 1, "pageInit": False, "isPrint": False,
                 "dataSources": None, "parameters": p, **base})
    r = json.loads(E.post_json({"reportAction": "Export", "controlID": tok, "resourcetype": fmt, "serviceAuthorizationToken": "", "isPrint": False,
                                "reportName": "", "pageindex": 1, **base}))
    while r.get("inProgress") == "inProgress":
        time.sleep(1)
        r = json.loads(E.post_json({"reportAction": "Export", "downloadreportid": r.get("downloadreportid"), **base}))
    return E.post_form({"reportAction": "Export", "controlID": tok, "serviceAuthorizationToken": "", "isPrint": "false",
                        "downloadreportid": r.get("downloadreportid", ""), "sessionToken": "null", "serverUrl": ""})

if __name__ == "__main__":
    s = dt.date.fromisoformat(sys.argv[1]); e = dt.date.fromisoformat(sys.argv[2])
    sys.stdout.buffer.write(export(s, e))
