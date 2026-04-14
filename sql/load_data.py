"""
Manufacturing KPI Dashboard — SQLite Data Loader
=================================================
Loads cleaned CSV data into a SQLite star schema.

Usage:
    python sql/load_data.py

Creates:
    data/manufacturing.db
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import calendar

# ── Paths ────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"

DB_PATH = DATA_DIR / "manufacturing.db"
CLEANED_CSV = DATA_DIR / "cleaned_production.csv"
MACHINE_CSV = DATA_DIR / "dim_machine.csv"
SCHEMA_SQL = SQL_DIR / "schema.sql"
QUERIES_SQL = SQL_DIR / "queries.sql"


def create_database(conn):
    """Execute the schema SQL to create tables, indexes, and views."""
    print("📐 Creating schema...")
    with open(SCHEMA_SQL, 'r') as f:
        schema = f.read()
    conn.executescript(schema)
    print("   ✅ Tables, indexes, and views created.")


def load_dim_machine(conn):
    """Populate the machine dimension table."""
    print("\n🔧 Loading dim_machine...")
    df = pd.read_csv(MACHINE_CSV)
    df.to_sql('dim_machine', conn, if_exists='replace', index=False)
    count = conn.execute("SELECT COUNT(*) FROM dim_machine").fetchone()[0]
    print(f"   ✅ {count} machines loaded.")


def load_dim_date(conn):
    """Generate and populate the date dimension table for 2023."""
    print("\n📅 Generating dim_date for 2023...")
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    records = []
    for d in dates:
        records.append({
            'date_key': d.strftime('%Y-%m-%d'),
            'day_of_week': d.strftime('%A'),
            'day_of_month': d.day,
            'month': d.month,
            'month_name': d.strftime('%B'),
            'quarter': f'Q{(d.month - 1) // 3 + 1}',
            'year': d.year,
            'week_number': d.isocalendar()[1],
            'is_weekend': 1 if d.weekday() >= 5 else 0,
        })

    df = pd.DataFrame(records)
    df.to_sql('dim_date', conn, if_exists='replace', index=False)
    count = conn.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0]
    print(f"   ✅ {count} dates loaded (2023-01-01 to 2023-12-31).")


def load_fact_production(conn):
    """Load cleaned production data into the fact table."""
    print("\n🏭 Loading fact_production...")
    df = pd.read_csv(CLEANED_CSV)

    # Rename columns to match schema
    col_map = {
        'air_temp_k': 'air_temp_k',
        'process_temp_k': 'process_temp_k',
        'rotational_speed_rpm': 'rotational_speed',
        'torque_nm': 'torque_nm',
        'tool_wear_min': 'tool_wear_min',
    }
    df = df.rename(columns=col_map)

    # Select fact table columns (exclude calculated OEE columns — those are computed in SQL/DAX)
    fact_cols = [
        'machine_id', 'shift_date', 'shift',
        'planned_time_min', 'run_time_min', 'downtime_min',
        'units_produced', 'defects', 'failure_type',
        'air_temp_k', 'process_temp_k',
        'rotational_speed', 'torque_nm', 'tool_wear_min'
    ]
    df_fact = df[fact_cols].copy()

    df_fact.to_sql('fact_production', conn, if_exists='replace', index=False)
    count = conn.execute("SELECT COUNT(*) FROM fact_production").fetchone()[0]
    print(f"   ✅ {count:,} production records loaded.")

    # Quick validation
    null_machines = conn.execute(
        "SELECT COUNT(*) FROM fact_production WHERE machine_id IS NULL"
    ).fetchone()[0]
    print(f"   Null machine_id rows: {null_machines}")

    neg_downtime = conn.execute(
        "SELECT COUNT(*) FROM fact_production WHERE downtime_min < 0"
    ).fetchone()[0]
    print(f"   Negative downtime rows: {neg_downtime}")


def run_sample_queries(conn):
    """Run and display results from key analytical queries."""
    print("\n" + "=" * 60)
    print(" SAMPLE QUERY RESULTS")
    print("=" * 60)

    # Query 1: Overall OEE
    print("\n📊 Overall OEE Scorecard:")
    result = conn.execute("""
        SELECT
            ROUND(SUM(run_time_min) / SUM(planned_time_min) * 100, 2) AS availability,
            ROUND(CAST(SUM(units_produced) AS REAL) / (SUM(run_time_min) * 0.5) * 100, 2) AS performance,
            ROUND(CAST(SUM(units_produced) - SUM(defects) AS REAL) /
                  NULLIF(SUM(units_produced), 0) * 100, 2) AS quality,
            ROUND(
                (SUM(run_time_min) / SUM(planned_time_min)) *
                (CAST(SUM(units_produced) AS REAL) / (SUM(run_time_min) * 0.5)) *
                (CAST(SUM(units_produced) - SUM(defects) AS REAL) /
                 NULLIF(SUM(units_produced), 0)) * 100, 2) AS oee
        FROM fact_production
    """).fetchone()
    print(f"   Availability: {result[0]}%")
    print(f"   Performance:  {result[1]}%")
    print(f"   Quality:      {result[2]}%")
    print(f"   OEE:          {result[3]}%")

    # Query 2: Top 5 downtime machines
    print("\n🔻 Top 5 Downtime Machines:")
    rows = conn.execute("""
        SELECT fp.machine_id, dm.plant_section,
               ROUND(SUM(fp.downtime_min), 1) AS total_downtime,
               ROUND(SUM(fp.downtime_min) / SUM(fp.planned_time_min) * 100, 2) AS downtime_pct
        FROM fact_production fp
        JOIN dim_machine dm ON fp.machine_id = dm.machine_id
        GROUP BY fp.machine_id
        ORDER BY total_downtime DESC
        LIMIT 5
    """).fetchall()
    for r in rows:
        print(f"   {r[0]} ({r[1]}): {r[2]:,.1f} min ({r[3]}%)")

    # Query 3: Shift comparison
    print("\n🌙 Shift Comparison:")
    rows = conn.execute("""
        SELECT shift,
               COUNT(*) AS shifts,
               ROUND(AVG(downtime_min), 1) AS avg_downtime,
               ROUND(AVG(units_produced), 1) AS avg_units
        FROM fact_production
        GROUP BY shift
    """).fetchall()
    for r in rows:
        print(f"   {r[0]}: {r[1]} shifts, avg downtime {r[2]} min, avg {r[3]} units")

    # Query 4: Failure Pareto
    print("\n⚠️  Failure Type Pareto:")
    rows = conn.execute("""
        SELECT failure_type, COUNT(*) AS cnt
        FROM fact_production
        WHERE failure_type IS NOT NULL
        GROUP BY failure_type
        ORDER BY cnt DESC
    """).fetchall()
    total = sum(r[1] for r in rows)
    running = 0
    for r in rows:
        running += r[1]
        pct = r[1] / total * 100
        cum = running / total * 100
        print(f"   {r[0]}: {r[1]} ({pct:.0f}%, cumulative {cum:.0f}%)")


def main():
    print("=" * 60)
    print(" MANUFACTURING KPI DASHBOARD — SQLite Loader")
    print("=" * 60)

    # Remove existing DB
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"🗑️  Removed existing {DB_PATH.name}")

    # Connect and load
    conn = sqlite3.connect(str(DB_PATH))

    try:
        create_database(conn)
        load_dim_machine(conn)
        load_dim_date(conn)
        load_fact_production(conn)
        conn.commit()

        # Verify table counts
        print("\n📋 Table Row Counts:")
        for table in ['dim_machine', 'dim_date', 'fact_production']:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"   {table}: {count:,} rows")

        run_sample_queries(conn)

    finally:
        conn.close()

    print(f"\n✅ Database created: {DB_PATH}")
    print(f"   Size: {DB_PATH.stat().st_size / 1024:.0f} KB")
    print("\n   Next step: Connect Power BI to this database or cleaned_production.csv")


if __name__ == "__main__":
    main()
