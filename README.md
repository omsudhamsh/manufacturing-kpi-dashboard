# 🏭 Manufacturing KPI Dashboard

> End-to-end data engineering + BI portfolio project — from raw sensor data to interactive Power BI dashboard.

![Python](https://img.shields.io/badge/Python-3.7+-3776AB?style=flat&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=flat&logo=powerbi&logoColor=black)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat&logo=pandas&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

---

## 📋 Project Overview

This project demonstrates an **end-to-end data pipeline** for monitoring **Overall Equipment Effectiveness (OEE)** in a manufacturing environment. It mirrors the analytics workflows used at companies like **ABB** — from raw data ingestion through SQL-based star schemas to interactive dashboards.

### Architecture

```
Raw Data (Kaggle CSV + Incident Log)
        │
        ▼
Python EDA (pandas, matplotlib)
   • Data profiling & validation
   • Synthetic augmentation
   • OEE calculation
        │
        ▼
SQLite Star Schema
   • fact_production
   • dim_machine / dim_date
   • Analytical views & queries
        │
        ▼
Power BI Dashboard
   • Executive Summary (OEE gauge, KPIs)
   • Drill-down Analysis (Matrix, Slicers)
   • Documentation Page
```

---

## 📊 Key Metrics

| KPI | Formula | Plant Average |
|---|---|---|
| **OEE** | Availability × Performance × Quality | ~70% |
| **Availability** | Run Time / Planned Time | ~95% |
| **Performance** | Actual Output / Ideal Output | ~85% |
| **Quality** | Good Units / Total Units | ~99% |
| **Defect Rate** | Defects / Units Produced | ~1.3% |

> **World-class OEE benchmark: ≥ 85%**

---

## 🗂️ Project Structure

```
manufacturing-kpi-dashboard/
├── data/
│   ├── ai4i2020.csv              ← Raw Kaggle dataset (10,000 rows)
│   ├── cleaned_production.csv    ← Augmented production data
│   ├── dim_machine.csv           ← Machine dimension data
│   ├── shift_incident_log.csv    ← Simulated incident reports
│   └── manufacturing.db          ← SQLite star schema database
├── sql/
│   ├── schema.sql                ← Star schema DDL
│   ├── queries.sql               ← 9 analytical queries
│   └── load_data.py              ← SQLite loader script
├── notebooks/
│   ├── eda.py                    ← Full EDA + augmentation
│   └── plots/                    ← Generated visualizations
├── docs/
│   ├── data_dictionary.md        ← Column reference + KPIs
│   ├── pipeline_overview.md      ← Architecture & data flow
│   └── powerbi_instructions.md   ← Power BI setup guide
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Power BI Desktop (free, for dashboard)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/omsudhamsh/manufacturing-kpi-dashboard.git
cd manufacturing-kpi-dashboard

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run EDA (generates cleaned CSV + charts)
python notebooks/eda.py

# 4. Load data into SQLite
python sql/load_data.py

# 5. Open Power BI Desktop and follow docs/powerbi_instructions.md
```

---

## 🔬 Data Sources

### Primary: AI4I 2020 Predictive Maintenance Dataset
- **Source**: [Kaggle](https://www.kaggle.com/datasets/shivamb/machine-predictive-maintenance-classification) / [UCI ML Repository](https://archive.ics.uci.edu/dataset/601)
- **Size**: 10,000 sensor readings
- **Features**: Temperature, torque, rotational speed, tool wear, 5 failure types
- **License**: CC BY 4.0

### Supplementary: Shift Incident Log
- **Type**: Simulated Google Form responses
- **Size**: 65 incident records
- **Fields**: Machine, shift, incident type, duration, severity, operator

> **Note**: Production KPIs (machine_id, units_produced, downtime, etc.) are synthetically augmented from the raw sensor data. This is transparently documented in the [data dictionary](docs/data_dictionary.md).

---

## 🛢️ SQL Star Schema

```
                    ┌──────────────┐
                    │  dim_machine  │
                    │──────────────│
                    │ machine_id   │◄──┐
                    │ machine_type │   │
                    │ line         │   │
                    │ plant_section│   │
                    └──────────────┘   │
                                      │
┌──────────────┐    ┌─────────────────┴────────────────┐
│   dim_date   │    │         fact_production           │
│──────────────│    │──────────────────────────────────│
│ date_key     │◄───│ machine_id, shift_date, shift     │
│ day_of_week  │    │ planned_time, run_time, downtime  │
│ month        │    │ units_produced, defects            │
│ quarter      │    │ failure_type                       │
│ year         │    │ air_temp, process_temp, rpm, etc.  │
│ is_weekend   │    └──────────────────────────────────┘
└──────────────┘
```

---

## 📈 Power BI Dashboard Pages

### Page 1 — Executive Summary
- OEE gauge visual with 85% target line
- KPI cards for Availability, Performance, Quality
- Downtime % bar chart by machine
- Defect rate line chart over time

### Page 2 — Drill-down Analysis
- Machine × Shift × Failure Type matrix
- Date range, plant section, and machine type slicers
- Decomposition tree for OEE breakdown

### Page 3 — Documentation
- Data model explanation
- Source attribution and assumptions
- DAX measure reference table

> 📖 Full setup instructions: [docs/powerbi_instructions.md](docs/powerbi_instructions.md)

---

## 📝 DAX Measures

```dax
OEE = [Availability] * [Performance] * [Quality]

Availability = DIVIDE(SUM(fact_production[run_time_min]), SUM(fact_production[planned_time_min]))

Performance = DIVIDE(SUM(fact_production[units_produced]), SUM(fact_production[run_time_min]) * 0.5)

Quality = DIVIDE(SUM(fact_production[units_produced]) - SUM(fact_production[defects]),
                 SUM(fact_production[units_produced]))

Defect Rate = DIVIDE(SUM(fact_production[defects]), SUM(fact_production[units_produced]))

MoM OEE Change = VAR Current = [OEE]
                 VAR Previous = CALCULATE([OEE], DATEADD(dim_date[Date], -1, MONTH))
                 RETURN DIVIDE(Current - Previous, Previous)
```

---

## 📚 Documentation

| Document | Description |
|---|---|
| [Data Dictionary](docs/data_dictionary.md) | Column definitions, KPI formulas, data quality notes |
| [Pipeline Overview](docs/pipeline_overview.md) | Architecture diagram, transformation logic, assumptions |
| [Power BI Instructions](docs/powerbi_instructions.md) | Step-by-step dashboard setup guide |

---

## 🛠️ Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Data | Python (pandas) | EDA, augmentation, cleaning |
| Storage | SQLite | Star schema database |
| Visualization | Power BI | Interactive dashboard |
| Version Control | Git/GitHub | Code & documentation |
| IDE | VS Code | Development environment |

---

## 📄 License

This project is licensed under the MIT License. The AI4I 2020 dataset is licensed under CC BY 4.0.

---

## 👤 Author

**Om Sudhamsh**  
[GitHub](https://github.com/omsudhamsh)
