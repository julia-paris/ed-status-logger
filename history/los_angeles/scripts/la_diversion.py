"""Build Los Angeles County's monthly hospital diversion table from the EMS Agency's yearly PDF reports.

    python3 history/los_angeles/scripts/la_diversion.py

Needs `pdftotext` (poppler-utils). Downloads every "Diversion Reports - By Hospital & Regions" PDF
listed on the EMS Agency reports page, reads each report's by-hospital table for its final year
("MONTHLY PERCENT OF DIVERSION <year>: by hospital"), and writes

  history/los_angeles/la_diversion_monthly.csv
    year, month, region, hospital_code, hospital_name, pct_hours_on_diversion, source_pdf

pct_hours_on_diversion is the share of the month's hours the hospital was on diversion to 9-1-1
traffic for ED saturation, as printed in the report (whole percents, with decimals in some years).
The current year's report prints 0% for months not yet reached; months after the last month with any
non-zero value county-wide are dropped. Hospital names change between reports; use hospital_code.
The PDFs themselves are not kept (about 3 MB each); source_pdf is the report each row came from.
"""
import csv
import collections
import os
import re
import subprocess
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "la_diversion_monthly.csv")
PAGE = "https://lahs.lacounty.gov/emergency-medical-services-agency/home/data-management-division/reports/"
UA = "Mozilla/5.0 (compatible; ed-status-logger; research archive)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def report_urls():
    html = get(PAGE).decode("utf-8", "replace")
    urls = re.findall(r'href="(https?://file\.lacounty\.gov/[^"]*Yearly[^"]*\.pdf)"', html)
    return sorted({u.replace("http://", "https://") for u in urls})


def parse(text, src, rows, names):
    for page in text.split("\f"):
        m = re.search(r"MONTHLY PERCENT OF DIVERSION:?\s*(\d{4})", page)
        if not m:
            continue
        year = int(m.group(1))
        reg = re.search(r"\n\s*([A-Z][A-Z \-/&]+REGION)", page)
        reg = reg.group(1).strip() if reg else ""
        # legend: "CODE  Hospital name   CODE  Hospital name ..."
        for code, name in re.findall(r"\b([A-Z]{3})\s{2,}(\S.*?)(?=\s{3,}[A-Z]{3}\s{2,}|\s*$)", page, flags=re.M):
            if not re.match(r"[\d.]", name) and "HOSPITAL NAME" not in name:
                names[code] = name.strip()
        for line in page.splitlines():
            r = re.match(r"^\s*([A-Z]{3})\s+((?:[\d.]+%\s*){1,12})$", line)
            if r:
                for i, v in enumerate(re.findall(r"([\d.]+)%", r.group(2))):
                    # later reports overwrite earlier ones for the same hospital-month
                    rows[(year, i + 1, r.group(1))] = (reg, float(v), src)


def main():
    rows, names = {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        for url in report_urls():
            pdf = os.path.join(tmp, "r.pdf")
            with open(pdf, "wb") as f:
                f.write(get(url))
            text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
            parse(text, os.path.basename(url), rows, names)
            print("parsed", os.path.basename(url))
    # drop placeholder months at the end of the current year (printed as 0% for every hospital)
    total = collections.Counter()
    for (y, mo, _), (_, v, _) in rows.items():
        total[(y, mo)] += v
    last = max(k for k, v in total.items() if v > 0)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "month", "region", "hospital_code", "hospital_name", "pct_hours_on_diversion", "source_pdf"])
        n = 0
        for (y, mo, code), (reg, v, src) in sorted(rows.items()):
            if (y, mo) <= last:
                w.writerow([y, mo, reg, code, names.get(code, ""), f"{v:g}", src])
                n += 1
    print(f"wrote {n} hospital-months through {last[0]}-{last[1]:02d}")


if __name__ == "__main__":
    main()
