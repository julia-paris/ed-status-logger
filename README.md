# ED status logger

Archives three public emergency-department status dashboards every 15 minutes, because none of them publishes a full history:

| Source | Dashboard | Feed saved |
|---|---|---|
| Maryland EDAS (MIEMSS) | https://edas.miemss.org/dashboard | `edas-services/api/cachedhospitalstatus` |
| New York ED Status (Juvare) | https://nydiverts.juvare.com/ | `nydiverts.juvare.com.json` |
| Georgia Coordinating Center (ImageTrend) | https://georgiarcc.org/ | `georgiarcc.imagetrendresourcebridge.com/ws/ResourceBridgeAPI/api/Agencies` |

A GitHub Actions workflow ([`.github/workflows/snapshot.yml`](.github/workflows/snapshot.yml)) runs [`logger/snapshot.py`](logger/snapshot.py) on a `*/15 * * * *` schedule and commits the raw JSON, gzipped, to `snapshots/<source>/YYYY/MM/DD/<UTC timestamp>.json.gz` (the first few snapshots from 2026-11-19 are plain `.json`).

## What each snapshot contains

**Maryland** — for every hospital: ED Census Index level (1–4), active alerts (Reroute, Code Black + reason, Trauma Bypass, Capacity) with how long they have been active, free-text notes (e.g. "STEMI Unavailable"), number of EMS units at the facility and en route, min/max ambulance length of stay, and one record per EMS unit (agency, call sign, incident number, minutes at hospital / en route).

**New York** — for every hospital: ED status (open, diversion, not reporting, …), diversion reason, comments, county, and the feed's own last-updated time.

**Georgia** — for 136 hospitals: diversion status (Open, ED Divert, Total Divert, …) with reason, comments and when it last changed; latest NEDOCS crowding score; staffed/available beds by type (ED, med-surg, ICU, …); accepting/not-accepting status for specialty services (STEMI, stroke, trauma, burn, psych, L&D, NICU, …); trauma/stroke/STEMI designation levels. Only the diversion and NEDOCS fields are updated frequently; some hospitals' beds and specialties go months without updates. The Georgia Coordinating Center call center closed in April 2025, but hospitals still post statuses to this board.

## Working with the data

```bash
git clone https://github.com/julia-paris/ed-status-logger
cd ed-status-logger
python3 logger/build_tables.py   # -> tables/*.csv
```

`build_tables.py` flattens all snapshots into `tables/maryland_hospital_status.csv`, `tables/maryland_units.csv`, `tables/newyork_ed_status.csv`, `tables/georgia_status.csv`, `tables/georgia_beds.csv` and `tables/georgia_specialties.csv` (git-ignored; regenerate any time).

## San Francisco, CA (event log)

`history/san_francisco/` — San Francisco EMS Agency's open datasets on DataSF, built from ReddiNet:

- `sf_hospital_diversions.csv` ([t4sf-777q](https://data.sf.gov/d/t4sf-777q)) — every hospital diversion since Jan 2024: hospital, category (ED, or Trauma Override at ZSFG), start, end, duration in minutes. Diversions expire after 2 hours unless re-declared, so long episodes appear as consecutive 2-hour rows; many rows are only a few minutes long.
- `sf_hospital_suspensions.csv` ([6x9s-ipug](https://data.sf.gov/d/6x9s-ipug)) — every citywide diversion suspension (triggered when 4+ hospitals are on diversion; blocks new diversions for 4 hours): start, end, duration.

Times are San Francisco local time as published. DataSF updates these monthly (roughly 6 weeks behind). A weekly workflow ([`.github/workflows/san-francisco.yml`](.github/workflows/san-francisco.yml), Mondays) re-downloads both and commits only when they change. Script: `history/san_francisco/scripts/sf_diversions.py`.

## Historical backfill: Maryland

The EDAS reports site (https://edas.miemss.org/reports) exposes history from August 2025 onward. Pulled once into `history/maryland/`:

- `edas_alert_log.csv` — every Reroute, Trauma Bypass, Code Black and Capacity alert with start/end/duration, all hospitals (Chronological Alert Log by Hospital report). Raw per-hospital XML exports in `raw_alert_xml/`.
- `edas_level4_daily.csv` — hours each hospital spent at ED Census Index Level 4 (≥131% of capacity) per day, Aug 4 2025 – Nov 18 2026 (53 hospitals), from the ED Census Index Level 4 report run one day at a time. Hospitals with no Level 4 time on a day may be missing rather than listed with 0. The report's percent column does not always divide back to 24 hours; prefer `level4_hours`.

Scripts: `history/maryland/scripts/` (`edas_pull.py all`, `edas_level4_daily.py [start] [end]`, re-runnable and resumable).

New York and Georgia have no public history; the snapshots here are the only record.

## Orange County, CA (event log)

`history/orange_county/oc_diversion_events.csv` — every diversion recorded in ReddiNet for Orange County's 26 Emergency Receiving Centers, Dec 31 2016 onward: facility, category (ED, Cardiac, Neuro, Trauma, CT, INT, Helipad), start and end time (Pacific local time, no timezone stored), duration in minutes, authorizing staff, operator, and comments. Downloaded from the data model behind the county's public Power BI "Diversion Dashboard" (https://www.ochealthinfo.com/providers-partners/emergency-medical-services/ems-system-reports/health-care-facilities) by `history/orange_county/scripts/oc_diversion_events.py`. Monthly hospital totals match the county's PDF diversion reports.

A weekly workflow ([`.github/workflows/orange-county.yml`](.github/workflows/orange-county.yml), Mondays) re-downloads the table and commits it if anything changed; git history keeps each earlier version.

Caveats: event counts rise sharply from 2022–2023, partly because Cardiac and Neuro diversions are logged alongside ED diversions ("Caused by ED Diversion"); a few events have implausibly long durations (up to ~58 days); events identical in every field would be collapsed into one row.

## Caveats

- Scheduled runs can be delayed several minutes, or occasionally skipped, at GitHub's busy times. Use `fetched_at_utc` in each file, not the file's position.
- GitHub disables schedules in repos with no activity for 60 days; the workflow's own commits normally count as activity, but check the Actions tab if snapshots stop.
- If one site is down, the others are still saved; the run only fails if all are down.
- Growth: roughly 6 MB/day (~2 GB/year), mostly Georgia.
