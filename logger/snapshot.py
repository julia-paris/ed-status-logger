"""Save one snapshot of the Maryland EDAS and New York ED status dashboards.

Each source is written as raw JSON to
    snapshots/<source>/<YYYY>/<MM>/<DD>/<YYYYMMDDTHHMMSSZ>.json
wrapped as {"fetched_at_utc": ..., "url": ..., "data": <response>}.

Exit code is non-zero only if every source failed, so one site being down
does not stop the other from being saved.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (compatible; ed-status-logger; research archive)"

SOURCES = {
    # Statewide status: per-hospital alerts, ED census score, units at/en route, wait times.
    "maryland": "https://edas.miemss.org/edas-services/api/cachedhospitalstatus",
    # Current ED status for every NY hospital.
    "newyork": "https://nydiverts.juvare.com/nydiverts.juvare.com.json",
}


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as e:  # network errors, bad JSON
            last = e
            time.sleep(5 * (i + 1))
    raise last


def main():
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    ok = 0
    for name, url in SOURCES.items():
        try:
            data = fetch(url)
        except Exception as e:
            print(f"[{name}] FAILED: {e}", file=sys.stderr)
            continue
        d = os.path.join(ROOT, "snapshots", name, now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"))
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{stamp}.json")
        with open(path, "w") as f:
            # indent=1 keeps one field per line so git can delta-compress consecutive snapshots well
            json.dump({"fetched_at_utc": now.isoformat(), "url": url, "data": data}, f, indent=1, ensure_ascii=False)
        print(f"[{name}] saved {os.path.relpath(path, ROOT)}")
        ok += 1
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
