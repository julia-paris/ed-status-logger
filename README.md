# ED status logger

Archives four emergency-department status feeds every 15 minutes, because none of them publishes a full history:

| Source | Dashboard | Feed saved |
|---|---|---|
| Maryland EDAS (MIEMSS) | https://edas.miemss.org/dashboard | `edas-services/api/cachedhospitalstatus` |
| New York ED Status (Juvare) | https://nydiverts.juvare.com/ | `nydiverts.juvare.com.json` |
| Georgia Coordinating Center (ImageTrend) | https://georgiarcc.org/ | `georgiarcc.imagetrendresourcebridge.com/ws/ResourceBridgeAPI/api/Agencies` |
| San Diego County EMS (ImageTrend LEMSIS Resource Bridge) | none public (staff login at https://cosd.imagetrendresourcebridge.com/) | `cosd.imagetrendresourcebridge.com/ws/ResourceBridgeAPI/api/Agencies` |

A GitHub Actions workflow ([`.github/workflows/snapshot.yml`](.github/workflows/snapshot.yml)) runs [`logger/snapshot.py`](logger/snapshot.py) every 15 minutes (on the quarter hour) and commits the raw JSON, gzipped, to `snapshots/<source>/YYYY/MM/DD/<UTC timestamp>.json.gz` (the first few snapshots from 2026-11-19 are plain `.json`).

## What each snapshot contains

**Maryland** — for every hospital: ED Census Index level (1–4), active alerts (Reroute, Code Black + reason, Trauma Bypass, Capacity) with how long they have been active, free-text notes (e.g. "STEMI Unavailable"), number of EMS units at the facility and en route, min/max ambulance length of stay, and one record per EMS unit (agency, call sign, incident number, minutes at hospital / en route).

**New York** — for every hospital: ED status (open, diversion, not reporting, …), diversion reason, comments, county, and the feed's own last-updated time.

**Georgia** — for 136 hospitals: diversion status (Open, ED Divert, Total Divert, …) with reason, comments and when it last changed; latest NEDOCS crowding score; staffed/available beds by type (ED, med-surg, ICU, …); accepting/not-accepting status for specialty services (STEMI, stroke, trauma, burn, psych, L&D, NICU, …); trauma/stroke/STEMI designation levels. Only the diversion and NEDOCS fields are updated frequently; some hospitals' beds and specialties go months without updates. The Georgia Coordinating Center call center closed in April 2025, but hospitals still post statuses to this board.

**San Diego** — same feed layout as Georgia, for 73 facilities: 23 hospitals with diversion status (HOSPITAL OPEN or a diversion status, with reason, comments, when it last changed and by whom), beds and specialty status, plus EMS agencies and a few out-of-county hospitals. Unlike Georgia's, this feed isn't shown on any public page: it answers without a login, but the county's front end is staff-only, and records include staff names. Logging started 2026-11-23.

## Working with the data

```bash
git clone https://github.com/julia-paris/ed-status-logger
cd ed-status-logger
python3 logger/build_tables.py   # -> tables/*.csv
```

`build_tables.py` flattens all snapshots into `tables/maryland_hospital_status.csv`, `tables/maryland_units.csv`, `tables/newyork_ed_status.csv`, `tables/georgia_status.csv`, `tables/georgia_beds.csv`, `tables/georgia_specialties.csv` and the same three `tables/sandiego_*.csv` (git-ignored; regenerate any time). Bed and specialty tables carry `hospital_name` as well as `dest_code`, because some Georgia facilities have a blank or shared code.

## San Francisco, CA (event log)

`history/san_francisco/` — San Francisco EMS Agency's open datasets on DataSF, built from ReddiNet:

- `sf_hospital_diversions.csv` ([t4sf-777q](https://data.sf.gov/d/t4sf-777q)) — every hospital diversion since Jan 2024: hospital, category (ED, or Trauma Override at ZSFG), start, end, duration in minutes. Diversions expire after 2 hours unless re-declared, so long episodes appear as consecutive 2-hour rows; many rows are only a few minutes long.
- `sf_hospital_suspensions.csv` ([6x9s-ipug](https://data.sf.gov/d/6x9s-ipug)) — every citywide diversion suspension (triggered when 4+ hospitals are on diversion; blocks new diversions for 4 hours): start, end, duration.

Times are San Francisco local time as published. DataSF updates these monthly (roughly 6 weeks behind). A weekly workflow ([`.github/workflows/san-francisco.yml`](.github/workflows/san-francisco.yml), started Mondays 09:15 UTC by the snapshot loop) re-downloads both and commits only when they change. Script: `history/san_francisco/scripts/sf_diversions.py`.

## Historical backfill: Maryland

The EDAS reports site (https://edas.miemss.org/reports) exposes history from August 2025 onward. Pulled once into `history/maryland/`:

- `edas_alert_log.csv` — every Reroute, Trauma Bypass, Code Black and Capacity alert with start/end/duration, all hospitals (Chronological Alert Log by Hospital report). Raw per-hospital XML exports in `raw_alert_xml/`.
- `edas_level4_daily.csv` — hours each hospital spent at ED Census Index Level 4 (≥131% of capacity) per day, Aug 4 2025 – Nov 18 2026 (53 hospitals), from the ED Census Index Level 4 report run one day at a time. Hospitals with no Level 4 time on a day may be missing rather than listed with 0. The report's percent column does not always divide back to 24 hours; prefer `level4_hours`.

Scripts: `history/maryland/scripts/` (`edas_pull.py all`, `edas_level4_daily.py [start] [end]`, re-runnable and resumable).

New York, Georgia and San Diego have no public history; the snapshots here are the only record.

## Orange County, CA (event log)

`history/orange_county/oc_diversion_events.csv` — every diversion recorded in ReddiNet for Orange County's 26 Emergency Receiving Centers, Dec 31 2016 onward: facility, category (ED, Cardiac, Neuro, Trauma, CT, INT, Helipad), start and end time (Pacific local time, no timezone stored), duration in minutes, authorizing staff, operator, and comments. Downloaded from the data model behind the county's public Power BI "Diversion Dashboard" (https://www.ochealthinfo.com/providers-partners/emergency-medical-services/ems-system-reports/health-care-facilities) by `history/orange_county/scripts/oc_diversion_events.py`. Monthly hospital totals match the county's PDF diversion reports.

A weekly workflow ([`.github/workflows/orange-county.yml`](.github/workflows/orange-county.yml), started Mondays 09:15 UTC by the snapshot loop) re-downloads the table and commits it if anything changed; git history keeps each earlier version.

Caveats: event counts rise sharply from 2022–2023, partly because Cardiac and Neuro diversions are logged alongside ED diversions ("Caused by ED Diversion"); a few events have implausibly long durations (up to ~58 days); events identical in every field would be collapsed into one row.

## Los Angeles, CA (monthly by hospital)

`history/los_angeles/la_diversion_monthly.csv` — the share of each month's hours every 9-1-1 receiving hospital (about 68–73) spent on diversion for ED saturation, January 2012 onward: year, month, region, hospital code and name, percent, and the source report. Parsed from the EMS Agency's yearly "Diversion Reports – By Hospital & Regions" PDFs (https://lahs.lacounty.gov/emergency-medical-services-agency/home/data-management-division/reports/); each report's by-hospital table covers its final year, and the current year's report is updated during the year. County averages match the figures printed in the reports. No start or end times. Hospital names change between reports, so link years on `hospital_code`. Script: `history/los_angeles/scripts/la_diversion.py` (needs `pdftotext`).

## Sacramento, CA (offload times)

`history/sacramento/` — Sacramento County EMS Agency's ambulance patient offload time (APOT) layers from its open data portal (https://data.saccounty.gov/): monthly 90th-percentile and mean APOT with patient counts, by hospital and county-wide; weekly patient counts by APOT range per hospital; weekly 90th-percentile APOT per hospital. The county keeps only the current year's months and the last two weeks, so `history/sacramento/scripts/sac_apot.py` merges each pull into these files to build history from 2026 onward (the weekly 90th-percentile layer was last updated for week 39 of 2026). Sacramento publishes no diversion data.

LA and Sacramento are pulled by [`.github/workflows/california.yml`](.github/workflows/california.yml), started Mondays 09:15 UTC by the snapshot loop: Sacramento every week, Los Angeles on the first Monday of each month. Files are committed only when they change.

## Caveats

- GitHub's cron scheduler never fired for this repo in its first hours, so the snapshot workflow doesn't depend on it: each run loops for ~5h40m taking a snapshot every quarter hour, then starts the next run itself, which waits for the next quarter hour so no slot is captured twice. A cron entry every 3 hours only restarts the chain if it breaks. A snapshot can occasionally land a few minutes late or, when the chain is restarted by hand or by cron, twice in one quarter hour (as at the 2026-11-20 04:30 UTC hand-off, before this fix); use `fetched_at_utc` in each file rather than assuming exact spacing.
- If snapshots stop, check the Actions tab and start the `snapshot` workflow by hand (`gh workflow run snapshot.yml`).
- If one site is down, the others are still saved; the run only fails if all are down.
- Growth: roughly 6 MB/day (~2 GB/year), mostly Georgia; San Diego adds a little under half as much again.
