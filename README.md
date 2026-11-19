# ED status logger

Archives two public emergency-department status dashboards every 15 minutes, because neither site keeps (or publishes) a full history:

| Source | Dashboard | Feed saved |
|---|---|---|
| Maryland EDAS (MIEMSS) | https://edas.miemss.org/dashboard | `edas-services/api/cachedhospitalstatus` |
| New York ED Status (Juvare) | https://nydiverts.juvare.com/ | `nydiverts.juvare.com.json` |

A GitHub Actions workflow ([`.github/workflows/snapshot.yml`](.github/workflows/snapshot.yml)) runs [`logger/snapshot.py`](logger/snapshot.py) on a `*/15 * * * *` schedule and commits the raw JSON to `snapshots/<source>/YYYY/MM/DD/<UTC timestamp>.json`.

## What each snapshot contains

**Maryland** — for every hospital: ED Census Index level (1–4), active alerts (Reroute, Code Black + reason, Trauma Bypass, Capacity) with how long they have been active, free-text notes (e.g. "STEMI Unavailable"), number of EMS units at the facility and en route, min/max ambulance length of stay, and one record per EMS unit (agency, call sign, incident number, minutes at hospital / en route).

**New York** — for every hospital: ED status (open, diversion, not reporting, …), diversion reason, comments, county, and the feed's own last-updated time.

## Working with the data

```bash
git clone https://github.com/julia-paris/ed-status-logger
cd ed-status-logger
python3 logger/build_tables.py   # -> tables/*.csv
```

`build_tables.py` flattens all snapshots into `tables/maryland_hospital_status.csv`, `tables/maryland_units.csv` and `tables/newyork_ed_status.csv` (git-ignored; regenerate any time).

## Historical backfill (Maryland only)

The EDAS reports site (https://edas.miemss.org/reports) exposes history from August 2025 onward. Pulled once into `history/maryland/`:

- `edas_alert_log.csv` — every Reroute, Trauma Bypass, Code Black and Capacity alert with start/end/duration, all hospitals (Chronological Alert Log by Hospital report). Raw per-hospital XML exports in `raw_alert_xml/`.
- `edas_level4_daily.csv` — hours each hospital spent at ED Census Index Level 4 (≥131% of capacity) per day, from the ED Census Index Level 4 report run one day at a time.

Scripts: `history/maryland/scripts/` (`edas_pull.py all`, `edas_level4_daily.py [start] [end]`, re-runnable and resumable).

New York has no public history; the snapshots here are the only record.

## Caveats

- Scheduled runs can be delayed several minutes, or occasionally skipped, at GitHub's busy times. Use `fetched_at_utc` in each file, not the file's position.
- GitHub disables schedules in repos with no activity for 60 days; the workflow's own commits normally count as activity, but check the Actions tab if snapshots stop.
- If one site is down, the other is still saved; the run only fails if both are down.
