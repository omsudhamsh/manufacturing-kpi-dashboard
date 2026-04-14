# Data Dictionary

> Manufacturing KPI Dashboard — Complete Column Reference

---

## Source Data: AI4I 2020 Predictive Maintenance Dataset

| Column | Type | Unit | Description | Source |
|---|---|---|---|---|
| UDI | Integer | — | Unique data identifier (1–10,000) | Kaggle |
| Product ID | String | — | Quality variant prefix (L/M/H) + serial number | Kaggle |
| Type | Categorical | — | Product quality: L (Low), M (Medium), H (High) | Kaggle |
| Air temperature [K] | Float | Kelvin | Ambient air temperature sensor reading | Kaggle |
| Process temperature [K] | Float | Kelvin | Process temperature sensor reading | Kaggle |
| Rotational speed [rpm] | Integer | RPM | Spindle rotational speed | Kaggle |
| Torque [Nm] | Float | Nm | Torque applied to workpiece | Kaggle |
| Tool wear [min] | Integer | Minutes | Cumulative tool usage time | Kaggle |
| Machine failure | Binary | 0/1 | Whether any failure occurred | Kaggle |
| TWF | Binary | 0/1 | Tool Wear Failure flag | Kaggle |
| HDF | Binary | 0/1 | Heat Dissipation Failure flag | Kaggle |
| PWF | Binary | 0/1 | Power Failure flag | Kaggle |
| OSF | Binary | 0/1 | Overstrain Failure flag | Kaggle |
| RNF | Binary | 0/1 | Random Failure flag | Kaggle |

---

## Fact Table: `fact_production`

> One row = one machine-shift production record

| Column | Type | Unit | Description | Derivation |
|---|---|---|---|---|
| production_id | Integer | — | Auto-increment primary key | System |
| machine_id | Text | — | Machine identifier (M001–M010) | Derived from Product ID hash |
| shift_date | Date | YYYY-MM-DD | Production date | Synthetically assigned (2023) |
| shift | Text | — | 'Day' or 'Night' | Randomly assigned (55/45 split) |
| planned_time_min | Real | Minutes | Planned production time (480 = 8hr shift) | Constant |
| run_time_min | Real | Minutes | Actual running time | `planned_time - downtime` |
| downtime_min | Real | Minutes | Unplanned downtime | Derived from tool wear + failure flags |
| units_produced | Integer | Units | Units manufactured in shift | `run_time × ideal_rate × efficiency` |
| defects | Integer | Units | Defective units produced | Failure → 1–5 defects; else 0–1 |
| failure_type | Text | — | TWF/HDF/PWF/OSF/RNF or NULL | First active failure flag |
| air_temp_k | Real | Kelvin | Air temperature sensor | Raw from dataset |
| process_temp_k | Real | Kelvin | Process temperature sensor | Raw from dataset |
| rotational_speed | Integer | RPM | Rotational speed sensor | Raw from dataset |
| torque_nm | Real | Nm | Torque sensor | Raw from dataset |
| tool_wear_min | Integer | Minutes | Tool wear sensor | Raw from dataset |

---

## Dimension Table: `dim_machine`

| Column | Type | Description | Values |
|---|---|---|---|
| machine_id | Text (PK) | Machine identifier | M001–M010 |
| machine_type | Text | Product quality variant | L, M, H |
| line | Text | Production line assignment | Line A, Line B, Line C |
| plant_section | Text | Plant section location | Section 1, Section 2, Section 3 |

### Machine Assignments

| Machine | Type | Line | Section |
|---|---|---|---|
| M001 | L (Low) | Line A | Section 1 |
| M002 | L (Low) | Line A | Section 1 |
| M003 | M (Medium) | Line A | Section 2 |
| M004 | M (Medium) | Line B | Section 2 |
| M005 | M (Medium) | Line B | Section 2 |
| M006 | H (High) | Line B | Section 3 |
| M007 | H (High) | Line C | Section 3 |
| M008 | L (Low) | Line C | Section 1 |
| M009 | M (Medium) | Line C | Section 2 |
| M010 | H (High) | Line A | Section 3 |

---

## Dimension Table: `dim_date`

| Column | Type | Description |
|---|---|---|
| date_key | Date (PK) | Calendar date (2023-01-01 to 2023-12-31) |
| day_of_week | Text | Monday, Tuesday, ... Sunday |
| day_of_month | Integer | 1–31 |
| month | Integer | 1–12 |
| month_name | Text | January, February, ... December |
| quarter | Text | Q1, Q2, Q3, Q4 |
| year | Integer | 2023 |
| week_number | Integer | ISO week number (1–52) |
| is_weekend | Integer | 0 = weekday, 1 = weekend |

---

## Supplementary Data: `shift_incident_log`

> Simulates a Google Form-based incident reporting system

| Column | Type | Description |
|---|---|---|
| incident_id | Text | Unique identifier (INC-0001 format) |
| machine_id | Text | Machine involved (M001–M010) |
| shift_date | Date | Date of incident |
| shift | Text | Day / Night |
| incident_type | Text | Mechanical Jam, Sensor Malfunction, Material Defect, Calibration Error, Power Fluctuation, Tooling Break, Overheating, Conveyor Stop |
| duration_min | Integer | Incident duration (5–120 minutes) |
| severity | Text | Low, Medium, High, Critical |
| reported_by | Text | Operator name |
| notes | Text | Resolution / status note |

---

## KPI Definitions

| KPI | Formula | Target |
|---|---|---|
| **Availability** | `Run Time / Planned Time` | ≥ 90% |
| **Performance** | `Units Produced / (Run Time × Ideal Rate)` | ≥ 95% |
| **Quality** | `(Units - Defects) / Units` | ≥ 99% |
| **OEE** | `Availability × Performance × Quality` | ≥ 85% (world-class) |
| **Defect Rate** | `Defects / Units Produced` | ≤ 1% |
| **Downtime %** | `Downtime / Planned Time` | ≤ 10% |
| **MoM Change** | `(This Month OEE - Last Month OEE) / Last Month OEE` | Positive trend |

> **Ideal Rate**: 0.5 units/minute (30 units/hour) — used as the theoretical maximum throughput for Performance calculation.

---

## Data Quality Notes

1. **No nulls** in the raw Kaggle dataset (verified)
2. **Synthetic augmentation**: machine_id, dates, shift, production metrics are synthetically generated — documented transparently
3. **Outliers**: Rotational speed and torque have IQR outliers (~2–5%) — retained as they represent realistic sensor variation
4. **Date range**: All records mapped to calendar year 2023
5. **Failure rate**: ~3.4% of rows have at least one failure flag
