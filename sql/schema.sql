-- ============================================================
-- Manufacturing KPI Dashboard — Star Schema
-- Database: SQLite (manufacturing.db)
-- Author: Om Sudhamsh
-- Description: Star schema for OEE tracking and analysis
-- ============================================================

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

-- Machine dimension: one row per physical machine
CREATE TABLE IF NOT EXISTS dim_machine (
    machine_id      TEXT PRIMARY KEY,       -- e.g., 'M001'
    machine_type    TEXT NOT NULL,           -- 'L' (Low), 'M' (Medium), 'H' (High) quality variant
    line            TEXT NOT NULL,           -- Production line: 'Line A', 'Line B', 'Line C'
    plant_section   TEXT NOT NULL            -- 'Section 1', 'Section 2', 'Section 3'
);

-- Date dimension: one row per calendar date
CREATE TABLE IF NOT EXISTS dim_date (
    date_key        DATE PRIMARY KEY,       -- e.g., '2023-01-15'
    day_of_week     TEXT NOT NULL,           -- 'Monday', 'Tuesday', etc.
    day_of_month    INTEGER NOT NULL,
    month           INTEGER NOT NULL,        -- 1–12
    month_name      TEXT NOT NULL,           -- 'January', 'February', etc.
    quarter         TEXT NOT NULL,           -- 'Q1', 'Q2', 'Q3', 'Q4'
    year            INTEGER NOT NULL,
    week_number     INTEGER NOT NULL,
    is_weekend      INTEGER NOT NULL DEFAULT 0  -- 0 = weekday, 1 = weekend
);

-- ============================================================
-- FACT TABLE
-- ============================================================

-- Production fact: one row per machine-shift combination
CREATE TABLE IF NOT EXISTS fact_production (
    production_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id          TEXT NOT NULL,
    shift_date          DATE NOT NULL,
    shift               TEXT NOT NULL,           -- 'Day' or 'Night'
    planned_time_min    REAL NOT NULL,           -- 480 min = 8-hour shift
    run_time_min        REAL NOT NULL,           -- actual running time
    downtime_min        REAL NOT NULL,           -- unplanned downtime
    units_produced      INTEGER NOT NULL,
    defects             INTEGER NOT NULL DEFAULT 0,
    failure_type        TEXT,                    -- 'TWF','HDF','PWF','OSF','RNF', or NULL
    air_temp_k          REAL,                    -- sensor: air temperature (Kelvin)
    process_temp_k      REAL,                    -- sensor: process temperature (Kelvin)
    rotational_speed    INTEGER,                 -- sensor: RPM
    torque_nm           REAL,                    -- sensor: torque (Nm)
    tool_wear_min       INTEGER,                 -- sensor: tool wear (minutes)

    FOREIGN KEY (machine_id) REFERENCES dim_machine(machine_id),
    FOREIGN KEY (shift_date) REFERENCES dim_date(date_key)
);

-- ============================================================
-- INDEXES for query performance
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_fact_machine     ON fact_production(machine_id);
CREATE INDEX IF NOT EXISTS idx_fact_date        ON fact_production(shift_date);
CREATE INDEX IF NOT EXISTS idx_fact_shift       ON fact_production(shift);
CREATE INDEX IF NOT EXISTS idx_fact_failure     ON fact_production(failure_type);

-- ============================================================
-- VIEWS for common KPI calculations
-- ============================================================

-- OEE by machine by month
CREATE VIEW IF NOT EXISTS vw_oee_by_machine_month AS
SELECT
    fp.machine_id,
    dm.machine_type,
    dm.plant_section,
    dd.year,
    dd.month,
    dd.month_name,

    -- Availability = Run Time / Planned Time
    ROUND(SUM(fp.run_time_min) / SUM(fp.planned_time_min), 4) AS availability,

    -- Performance = Units Produced / (Run Time × Ideal Rate)
    -- Ideal rate: 0.5 units/min (30 units/hour)
    ROUND(
        CAST(SUM(fp.units_produced) AS REAL) /
        (SUM(fp.run_time_min) * 0.5),
        4
    ) AS performance,

    -- Quality = (Units Produced - Defects) / Units Produced
    ROUND(
        CAST(SUM(fp.units_produced) - SUM(fp.defects) AS REAL) /
        NULLIF(SUM(fp.units_produced), 0),
        4
    ) AS quality,

    -- OEE = Availability × Performance × Quality
    ROUND(
        (SUM(fp.run_time_min) / SUM(fp.planned_time_min)) *
        (CAST(SUM(fp.units_produced) AS REAL) / (SUM(fp.run_time_min) * 0.5)) *
        (CAST(SUM(fp.units_produced) - SUM(fp.defects) AS REAL) / NULLIF(SUM(fp.units_produced), 0)),
        4
    ) AS oee,

    SUM(fp.downtime_min)    AS total_downtime_min,
    SUM(fp.units_produced)  AS total_units,
    SUM(fp.defects)         AS total_defects,
    COUNT(*)                AS shift_count

FROM fact_production fp
JOIN dim_machine dm ON fp.machine_id = dm.machine_id
JOIN dim_date dd    ON fp.shift_date = dd.date_key
GROUP BY fp.machine_id, dd.year, dd.month;
