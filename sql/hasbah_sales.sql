-- hasbah_sales.sql — monthly HFS (vans/bikes) sales per customer, DATA_SOURCE=mssql
--
-- OUTPUT CONTRACT (one row per customer per month; data.py pivots it wide):
--   customer_id, customer_id_PK, customer_name, category, rep_category,
--   sales_rep, REGION_NAME, LAT, LONG, month_start (date, 1st of month), sales
--
-- Parameter "start" — first day of the earliest month (bound by data.py).
-- wh.FACT_VAN_SALES has no SUBD data; data.py adds SUBD rows from the Excel export.
-- Customers = those with at least one sale in the window. Their attributes
-- (name, rep, coordinates) come from their latest sale with valid coordinates.
--
-- TO VERIFY against the Excel (Jan–Apr 2026) before going live:
--   * VALUE_SOLD vs EXT_VAT_VALUE_SOLD — which one matches the Excel totals
--   * whether ENTRY_TYPE includes returns/credit notes that must be excluded

WITH src AS (
    SELECT CUSTOMER_KEY, SRC_CUSTOMER_CODE, CUSTOMER_NAME, SALES_REP, REP_CATEGORY,
           REGION_NAME, LATITUDE, LONGITUDE, ENTRY_DATE, ENTRY_TS, VALUE_SOLD
    FROM wh.FACT_VAN_SALES
    WHERE DW_IS_DELETED = 0
      AND CUSTOMER_KEY IS NOT NULL
      AND ENTRY_DATE >= '2026-01-01'  -- Jan 1, 2026 is the first month in the Excel export
      AND ENTRY_DATE <  DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)  -- full months only
),
latest AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY CUSTOMER_KEY
               ORDER BY CASE WHEN LATITUDE IS NULL OR LATITUDE = 0 THEN 1 ELSE 0 END,
                        ENTRY_TS DESC
           ) AS rn
    FROM src
),
monthly AS (
    SELECT CUSTOMER_KEY,
           DATEFROMPARTS(YEAR(ENTRY_DATE), MONTH(ENTRY_DATE), 1) AS month_start,
           SUM(VALUE_SOLD)                                       AS sales
    FROM src
    GROUP BY CUSTOMER_KEY, DATEFROMPARTS(YEAR(ENTRY_DATE), MONTH(ENTRY_DATE), 1)
)
SELECT
    l.SRC_CUSTOMER_CODE      AS customer_id,
    l.CUSTOMER_KEY           AS customer_id_PK,
    l.CUSTOMER_NAME          AS customer_name,
    'HFS'                    AS category,
    LTRIM(RTRIM(l.REP_CATEGORY)) AS rep_category,
    l.SALES_REP              AS sales_rep,
    UPPER(l.REGION_NAME)     AS REGION_NAME,
    CAST(l.LATITUDE  AS float) AS LAT,
    CAST(l.LONGITUDE AS float) AS LONG,
    m.month_start,
    m.sales
FROM latest  AS l
JOIN monthly AS m ON m.CUSTOMER_KEY = l.CUSTOMER_KEY
WHERE l.rn = 1;
