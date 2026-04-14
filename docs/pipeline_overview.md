# Data Pipeline Overview

> End-to-end data flow from raw sources to Power BI dashboard

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES (Layer 1)                      │
│                                                                     │
│   ┌──────────────────────┐         ┌──────────────────────┐        │
│   │   Kaggle Dataset     │         │  Google Form (sim.)  │        │
│   │   AI4I 2020 CSV      │         │  Shift Incident Log  │        │
│   │   10,000 rows        │         │  65 incidents         │        │
│   └──────────┬───────────┘         └──────────┬───────────┘        │
│              │                                 │                    │
└──────────────┼─────────────────────────────────┼────────────────────┘
               │                                 │
               ▼                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA PIPELINE (Layer 2)                        │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────┐     │
│   │  Step 1: Python EDA (notebooks/eda.py)                   │     │
│   │  • Data profiling & validation                           │     │
│   │  • Outlier detection (IQR method)                        │     │
│   │  • Synthetic augmentation (machine_id, dates, OEE cols)  │     │
│   │  • OEE calculation: Availability × Performance × Quality │     │
│   │  • 8 visualization charts                                │     │
│   │  • Export: cleaned_production.csv                        │     │
│   └──────────────────────┬───────────────────────────────────┘     │
│                          │                                          │
│                          ▼                                          │
│   ┌──────────────────────────────────────────────────────────┐     │
│   │  Step 2: SQLite Database (sql/load_data.py)              │     │
│   │  • Star schema: fact_production + dim_machine + dim_date │     │
│   │  • Indexes for query performance                         │     │
│   │  • OEE view for pre-aggregated analytics                 │     │
│   │  • 9 analytical query templates                          │     │
│   └──────────────────────┬───────────────────────────────────┘     │
│                          │                                          │
│                          ▼                                          │
│   ┌──────────────────────────────────────────────────────────┐     │
│   │  Step 3: Power Query (Power BI Desktop)                  │     │
│   │  • Connect to SQLite/CSV                                 │     │
│   │  • Remove error rows                                     │     │
│   │  • Create Date table                                     │     │
│   │  • Add calculated column: Downtime %                     │     │
│   │  • Set up star schema relationships                      │     │
│   └──────────────────────┬───────────────────────────────────┘     │
│                          │                                          │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    POWER BI DASHBOARD (Layer 3)                     │
│                                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│   │ Page 1:      │  │ Page 2:      │  │ Page 3:              │    │
│   │ Executive    │  │ Drill-down   │  │ Documentation        │    │
│   │ Summary      │  │ Analysis     │  │                      │    │
│   │              │  │              │  │ • Data model          │    │
│   │ • OEE gauge  │  │ • Matrix     │  │ • Data sources        │    │
│   │ • Downtime % │  │ • Slicers    │  │ • Assumptions         │    │
│   │ • Defect     │  │ • Decomp.    │  │ • DAX reference       │    │
│   │   trend      │  │   tree       │  │                      │    │
│   │ • KPI cards  │  │              │  │                      │    │
│   └──────────────┘  └──────────────┘  └──────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Transformation Summary

### Step 1: Raw → Cleaned (Python)

| Transformation | Input | Output | Logic |
|---|---|---|---|
| Machine ID assignment | Product ID | machine_id (M001–M010) | Hash-based partitioning |
| Date generation | — | shift_date | Random assignment across 2023 |
| Shift assignment | — | shift (Day/Night) | 55%/45% random split |
| Downtime derivation | Tool wear + failure flags | downtime_min | Proportional + failure penalty |
| Production calculation | Rotational speed | units_produced | `run_time × rate × efficiency` |
| Defect generation | Machine failure flag | defects | Failure: 1–5, else: 0–1 |
| OEE computation | Availability, Performance, Quality | oee | Three-component product |

### Step 2: Cleaned CSV → SQLite (Python)

| Operation | Details |
|---|---|
| Schema creation | 3 tables, 4 indexes, 1 view |
| Fact loading | 10,000 records with sensor + production data |
| Dimension loading | 10 machines, 365 dates |
| Validation | Null checks, negative value detection |

### Step 3: SQLite → Power BI (Manual)

| Operation | Details |
|---|---|
| Data connection | ODBC to SQLite or direct CSV import |
| Power Query transforms | Error removal, date table, calculated column |
| Model setup | Star schema relationships in model view |
| DAX measures | 7 measures (OEE, Availability, Performance, Quality, Defect Rate, MoM, Downtime %) |

---

## Assumptions & Limitations

1. **Single-machine source**: The AI4I dataset simulates one machine. We distribute records across 10 synthetic machines for realistic multi-machine analysis.

2. **Ideal rate**: 30 units/hour (0.5 units/min) is assumed as the theoretical maximum throughput. In a real plant, each machine type would have its own ideal rate.

3. **Downtime model**: Downtime is derived from tool wear (continuous degradation) plus failure penalties (event-based). This is a simplification of real unplanned downtime tracking.

4. **No planned downtime**: The model assumes zero planned downtime (maintenance, changeover). In production, Availability would account for planned vs. unplanned stops.

5. **Date coverage**: All data maps to 2023. Distribution across dates is random, not reflecting actual production schedules.

6. **Defect model**: Defects are probabilistic — failures guarantee 1–5 defects, while non-failure shifts have a 20% chance of 1 defect.

---

## File Inventory

```
manufacturing-kpi-dashboard/
├── data/
│   ├── ai4i2020.csv              ← Raw Kaggle dataset (10,000 rows)
│   ├── cleaned_production.csv    ← Augmented + cleaned production data
│   ├── dim_machine.csv           ← Machine dimension data
│   ├── shift_incident_log.csv    ← Simulated incident reports
│   └── manufacturing.db          ← SQLite star schema database
├── sql/
│   ├── schema.sql                ← DDL: tables, indexes, views
│   ├── queries.sql               ← 9 analytical query templates
│   └── load_data.py              ← SQLite loader script
├── notebooks/
│   ├── eda.py                    ← Full EDA + augmentation script
│   └── plots/                    ← 8 generated charts (PNG)
├── docs/
│   ├── data_dictionary.md        ← Column reference + KPIs
│   ├── pipeline_overview.md      ← This document
│   └── powerbi_instructions.md   ← Power BI setup guide
├── requirements.txt              ← Python dependencies
└── README.md                     ← Project summary
```
