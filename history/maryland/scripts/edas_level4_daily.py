"""Run the Level 4 report one day at a time -> data/edas_level4_daily.csv (hospital-day rows)."""
import sys, os, csv, re, time, datetime as dt, html
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import edas_level4 as L

START = dt.date.fromisoformat(sys.argv[1] if len(sys.argv) > 1 else "2025-08-01")
END = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date.today() - dt.timedelta(days=1)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edas_level4_daily.csv")
REG = re.compile(r'TextBox126="([^"]+)"|TextBox4="([^"]+)" TextBox14="([^"]+)" TextBox5="([^"]+)"')

def one(d):
    for i in range(4):
        try:
            x = L.export(d, d).decode("utf-8-sig"); break
        except Exception as e:
            print("retry", d, e, file=sys.stderr); time.sleep(5)
    else:
        return d, None
    rows, region = [], ""
    for m in REG.finditer(x):
        if m.group(1): region = html.unescape(m.group(1))
        else: rows.append({"date": d.isoformat(), "region": region, "hospital_name": html.unescape(m.group(2)),
                           "level4_hours": m.group(3), "level4_pct": m.group(4).replace(" %", "")})
    return d, rows

days = [START + dt.timedelta(n) for n in range((END - START).days + 1)]
done = set()
if os.path.exists(OUT):
    done = {r["date"] for r in csv.DictReader(open(OUT))}
todo = [d for d in days if d.isoformat() not in done]
new = not os.path.exists(OUT)
with open(OUT, "a", newline="") as f, ThreadPoolExecutor(4) as ex:
    w = csv.DictWriter(f, fieldnames=["date", "region", "hospital_name", "level4_hours", "level4_pct"])
    if new: w.writeheader()
    for d, rows in ex.map(one, todo):
        if rows is None: print("FAILED", d, file=sys.stderr); continue
        w.writerows(rows); f.flush(); print(d, len(rows), file=sys.stderr)
