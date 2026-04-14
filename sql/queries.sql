-- ============================================================
-- Manufacturing KPI Dashboard — Analytical Queries
-- Database: SQLite (manufacturing.db)
-- Usage: Run these against the loaded database for analysis
-- ============================================================


-- ============================================================
-- 1. OVERALL OEE SCORECARD
-- ============================================================
-- Returns plant-wide OEE and its three components
SELECT
    ROUND(SUM(run_time_min) / SUM(planned_time_min) * 100, 2)
        AS availability_pct,

    ROUND(CAST(SUM(units_produced) AS REAL) / (SUM(run_time_min) * 0.5) * 100, 2)
        AS performance_pct,

    ROUND(CAST(SUM(units_produced) - SUM(defects) AS REAL) / NULLIF(SUM(units_produced), 0) * 100, 2)
        AS quality_pct,

    ROUND(
        (SUM(run_time_min) / SUM(planned_time_min)) *
        (CAST(SUM(units_produced) AS REAL) / (SUM(run_time_min) * 0.5)) *
        (CAST(SUM(units_produced) - SUM(defects) AS REAL) / NULLIF(SUM(units_produced), 0)) * 100
    , 2) AS oee_pct

FROM fact_production;


-- ============================================================
-- 2. TOP 5 DOWNTIME CONTRIBUTORS (by machine)
-- ============================================================
SELECT
    fp.machine_id,
    dm.machine_type,
    dm.plant_section,
    ROUND(SUM(fp.downtime_min), 1) AS total_downtime_min,
    ROUND(SUM(fp.downtime_min) / SUM(fp.planned_time_min) * 100, 2) AS downtime_pct,
    COUNT(CASE WHEN fp.failure_type IS NOT NULL THEN 1 END) AS failure_count
FROM fact_production fp
JOIN dim_machine dm ON fp.machine_id = dm.machine_id
GROUP BY fp.machine_id
ORDER BY total_downtime_min DESC
LIMIT 5;


-- ============================================================
-- 3. DEFECT RATE TREND (weekly)
-- ============================================================
SELECT
    dd.year,
    dd.week_number,
    MIN(fp.shift_date) AS week_start,
    SUM(fp.defects) AS total_defects,
    SUM(fp.units_produced) AS total_produced,
    ROUND(CAST(SUM(fp.defects) AS REAL) / NULLIF(SUM(fp.units_produced), 0) * 100, 3)
        AS defect_rate_pct
FROM fact_production fp
JOIN dim_date dd ON fp.shift_date = dd.date_key
GROUP BY dd.year, dd.week_number
ORDER BY dd.year, dd.week_number;


-- ============================================================
-- 4. SHIFT COMPARISON (Day vs Night)
-- ============================================================
SELECT
    fp.shift,
    COUNT(*) AS total_shifts,
    ROUND(AVG(fp.downtime_min), 1) AS avg_downtime_min,
    ROUND(AVG(fp.units_produced), 1) AS avg_units,
    ROUND(AVG(fp.defects), 2) AS avg_defects,

    -- OEE per shift type
    ROUND(
        (SUM(fp.run_time_min) / SUM(fp.planned_time_min)) *
        (CAST(SUM(fp.units_produced) AS REAL) / (SUM(fp.run_time_min) * 0.5)) *
        (CAST(SUM(fp.units_produced) - SUM(fp.defects) AS REAL) / NULLIF(SUM(fp.units_produced), 0)) * 100
    , 2) AS oee_pct

FROM fact_production fp
GROUP BY fp.shift;


-- ============================================================
-- 5. FAILURE TYPE PARETO ANALYSIS
-- ============================================================
-- Shows failure types ranked by frequency with cumulative %
WITH failure_counts AS (
    SELECT
        failure_type,
        COUNT(*) AS cnt
    FROM fact_production
    WHERE failure_type IS NOT NULL
    GROUP BY failure_type
),
ranked AS (
    SELECT
        failure_type,
        cnt,
        SUM(cnt) OVER (ORDER BY cnt DESC) AS running_total,
        SUM(cnt) OVER () AS grand_total
    FROM failure_counts
)
SELECT
    failure_type,
    cnt AS occurrence_count,
    ROUND(CAST(cnt AS REAL) / grand_total * 100, 1) AS pct_of_total,
    ROUND(CAST(running_total AS REAL) / grand_total * 100, 1) AS cumulative_pct
FROM ranked
ORDER BY cnt DESC;


-- ============================================================
-- 6. OEE BY MACHINE BY MONTH (uses the view)
-- ============================================================
SELECT
    machine_id,
    month_name,
    ROUND(availability * 100, 1) AS availability_pct,
    ROUND(performance * 100, 1) AS performance_pct,
    ROUND(quality * 100, 1) AS quality_pct,
    ROUND(oee * 100, 1) AS oee_pct,
    total_downtime_min,
    total_units,
    total_defects
FROM vw_oee_by_machine_month
ORDER BY machine_id, month;


-- ============================================================
-- 7. MACHINE × SHIFT × FAILURE TYPE MATRIX
-- (Power BI drill-down source)
-- ============================================================
SELECT
    fp.machine_id,
    dm.plant_section,
    fp.shift,
    COALESCE(fp.failure_type, 'No Failure') AS failure_type,
    COUNT(*) AS record_count,
    SUM(fp.downtime_min) AS total_downtime,
    SUM(fp.defects) AS total_defects
FROM fact_production fp
JOIN dim_machine dm ON fp.machine_id = dm.machine_id
GROUP BY fp.machine_id, fp.shift, fp.failure_type
ORDER BY fp.machine_id, fp.shift;


-- ============================================================
-- 8. MONTHLY OEE TREND WITH MONTH-OVER-MONTH CHANGE
-- ============================================================
WITH monthly_oee AS (
    SELECT
        dd.year,
        dd.month,
        dd.month_name,
        ROUND(
            (SUM(fp.run_time_min) / SUM(fp.planned_time_min)) *
            (CAST(SUM(fp.units_produced) AS REAL) / (SUM(fp.run_time_min) * 0.5)) *
            (CAST(SUM(fp.units_produced) - SUM(fp.defects) AS REAL) / NULLIF(SUM(fp.units_produced), 0)) * 100
        , 2) AS oee_pct
    FROM fact_production fp
    JOIN dim_date dd ON fp.shift_date = dd.date_key
    GROUP BY dd.year, dd.month
)
SELECT
    year,
    month,
    month_name,
    oee_pct,
    LAG(oee_pct) OVER (ORDER BY year, month) AS prev_month_oee,
    ROUND(
        (oee_pct - LAG(oee_pct) OVER (ORDER BY year, month)) /
        NULLIF(LAG(oee_pct) OVER (ORDER BY year, month), 0) * 100
    , 2) AS mom_change_pct
FROM monthly_oee
ORDER BY year, month;


-- ============================================================
-- 9. PLANT SECTION PERFORMANCE SUMMARY
-- ============================================================
SELECT
    dm.plant_section,
    COUNT(DISTINCT fp.machine_id) AS machines,
    SUM(fp.units_produced) AS total_units,
    SUM(fp.defects) AS total_defects,
    ROUND(CAST(SUM(fp.defects) AS REAL) / NULLIF(SUM(fp.units_produced), 0) * 100, 2)
        AS defect_rate_pct,
    ROUND(SUM(fp.downtime_min) / SUM(fp.planned_time_min) * 100, 2)
        AS downtime_pct,
    ROUND(
        (SUM(fp.run_time_min) / SUM(fp.planned_time_min)) *
        (CAST(SUM(fp.units_produced) AS REAL) / (SUM(fp.run_time_min) * 0.5)) *
        (CAST(SUM(fp.units_produced) - SUM(fp.defects) AS REAL) / NULLIF(SUM(fp.units_produced), 0)) * 100
    , 2) AS oee_pct
FROM fact_production fp
JOIN dim_machine dm ON fp.machine_id = dm.machine_id
GROUP BY dm.plant_section
ORDER BY oee_pct DESC;
