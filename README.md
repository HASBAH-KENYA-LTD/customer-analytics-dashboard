# Customer Analytics · Kenya

Plotly Dash dashboards that place HASBAH (HFS / SUBD) and Coke customers onto
Kenyan admin geography (wards, constituencies, sublocations, sales territories).

| Entry point      | What it serves                                  |
|------------------|-------------------------------------------------|
| `dashboard.py`   | Multi-page dashboard (main, sales, overlap, …)  |
| `shptest_app.py` | Standalone borough/distributor map (port 8051)  |

## Data sources

| Data                    | Source                                                        |
|-------------------------|---------------------------------------------------------------|
| HASBAH HFS (vans/bikes) | SQL Server `wh.FACT_VAN_SALES` (`DATA_SOURCE=mssql`) or the Excel export (`DATA_SOURCE=excel`) |
| HASBAH SUBD (distributors) | Always `HASBAH_CUSTOMERS_SUBD_VANS.xlsx` — SUBD sales are not in SQL Server |
| Coke customers          | `COKE_CUSTOMERS.xlsx`                                         |
| Geography               | Shapefiles in `Kenya_Wards/`, `ken_adm_iebc_20191031_shp/`, `Boroughs/` |

`data.py` loads everything once, runs the spatial joins, and pickles the result
to `.cache_data_<source>.pkl`. The cache is rebuilt when a source file changes or,
for `mssql`, when it is older than `CACHE_TTL_HOURS`. If SQL Server is unreachable
during a rebuild, the app logs the error and starts from the stale cache.

The months shown (`config.MONTHS`) come from the data: the last `MONTHS_BACK`
full calendar months (mssql) or the last `MONTHS_BACK` month columns (Excel).

### SQL Server query

`sql/hasbah_sales.sql` must return one row per customer per month:

```
customer_id, customer_id_PK, customer_name, category ('HFS'|'SUBD'),
rep_category, sales_rep, REGION_NAME, LAT, LONG, month_start (date), sales
```

The `start` parameter is bound to the first day of the earliest month. Only
HFS rows come from SQL Server; SUBD rows are appended from the Excel export.
Months the Excel doesn't cover are blank for SUBD (`data.NO_DATA_MONTHS`), so
trend charts show a gap rather than a false zero. Refresh the SUBD Excel or
raise `MONTHS_BACK` to keep SUBD months in the window.

## Setup

```bash
# SQL Server ODBC driver (Ubuntu / WSL) — https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
sudo apt install msodbcsql17 unixodbc-dev

python -m venv ../geo_env && ../geo_env/bin/pip install -r requirements.txt
cp .env.example .env        # fill in the MSSQL_* values
../geo_env/bin/python db.py # connectivity check: prints server, database, version
```

Use `DATA_SOURCE=excel` in `.env` to work offline from the Excel export.

## Run

```bash
../geo_env/bin/python dashboard.py
gunicorn shptest_app:server -w 1 -b 127.0.0.1:8051 --timeout 120   # production
```

## Daily refresh (production)

Dash holds the data in memory, so fresh sales are picked up by restarting the
service. `deploy/` has a systemd timer that does this at 05:00:

```bash
sudo cp deploy/dashboard-refresh.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now dashboard-refresh.timer
systemctl list-timers dashboard-refresh.timer
```

The first request after a refresh restart waits for the rebuild (~1 min).
