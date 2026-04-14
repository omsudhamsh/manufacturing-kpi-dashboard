# Power BI Setup Instructions

> Step-by-step guide to build the Manufacturing KPI Dashboard in Power BI Desktop

---

## Prerequisites

- [Power BI Desktop](https://powerbi.microsoft.com/desktop/) installed (free)
- Project files: `cleaned_production.csv`, `dim_machine.csv`, `shift_incident_log.csv`
- Optionally: `manufacturing.db` (SQLite) via ODBC driver

---

## Step 1: Import Data

### Option A: CSV Import (Recommended for simplicity)

1. Open Power BI Desktop → **Get Data** → **Text/CSV**
2. Import these files:
   - `data/cleaned_production.csv`
   - `data/dim_machine.csv`
   - `data/shift_incident_log.csv`
3. In the import dialog, verify column types are detected correctly

### Option B: SQLite via ODBC

1. Install [SQLite ODBC Driver](http://www.ch-werner.de/sqliteodbc/)
2. **Get Data** → **ODBC** → Configure DSN pointing to `data/manufacturing.db`
3. Import tables: `fact_production`, `dim_machine`, `dim_date`

---

## Step 2: Power Query Transformations

Open **Transform Data** (Power Query Editor):

### 2a. Clean fact_production / cleaned_production

```
1. Select all columns → Remove Errors
2. Select 'shift_date' → Change Type → Date
3. Add Column → Custom Column:
   Name: Downtime_Pct
   Formula: = [downtime_min] / [planned_time_min]
4. Change Downtime_Pct type → Decimal Number
```

### 2b. Create Date Table

```
1. New Source → Blank Query
2. In formula bar, paste:
   = List.Dates(#date(2023,1,1), 365, #duration(1,0,0,0))
3. Convert to Table → Rename column to 'Date'
4. Add columns:
   - Year = Date.Year([Date])
   - Month = Date.Month([Date])
   - MonthName = Date.MonthName([Date])
   - Quarter = "Q" & Text.From(Date.QuarterOfYear([Date]))
   - DayOfWeek = Date.DayOfWeekName([Date])
   - WeekNumber = Date.WeekOfYear([Date])
   - IsWeekend = if Date.DayOfWeek([Date]) >= 5 then 1 else 0
5. Rename query to 'dim_date'
```

### 2c. Close & Apply

Click **Close & Apply** to load all tables.

---

## Step 3: Data Model (Relationships)

Switch to **Model View** and create these relationships:

```
fact_production[machine_id]  →  dim_machine[machine_id]   (Many-to-One)
fact_production[shift_date]  →  dim_date[Date]            (Many-to-One)
```

Ensure:
- Cross-filter direction: **Single**
- Cardinality: **Many-to-One** (fact → dimension)

This creates a **star schema** — the gold standard for BI data modeling.

---

## Step 4: DAX Measures

Create a new **Measures Table** or add measures to fact_production:

### Core OEE Measures

```dax
// Availability: What % of planned time was the machine running?
Availability = 
    DIVIDE(
        SUM(fact_production[run_time_min]),
        SUM(fact_production[planned_time_min]),
        0
    )
```

```dax
// Performance: How fast is the machine vs. ideal rate?
// Ideal rate = 0.5 units/min (30 units/hour)
Performance = 
    DIVIDE(
        SUM(fact_production[units_produced]),
        SUM(fact_production[run_time_min]) * 0.5,
        0
    )
```

```dax
// Quality: What % of units are defect-free?
Quality = 
    DIVIDE(
        SUM(fact_production[units_produced]) - SUM(fact_production[defects]),
        SUM(fact_production[units_produced]),
        0
    )
```

```dax
// OEE: Overall Equipment Effectiveness
OEE = [Availability] * [Performance] * [Quality]
```

### Supporting Measures

```dax
// Defect Rate
Defect Rate = 
    DIVIDE(
        SUM(fact_production[defects]),
        SUM(fact_production[units_produced]),
        0
    )
```

```dax
// Total Downtime
Total Downtime = SUM(fact_production[downtime_min])
```

```dax
// Downtime Percentage
Downtime % = 
    DIVIDE(
        SUM(fact_production[downtime_min]),
        SUM(fact_production[planned_time_min]),
        0
    )
```

```dax
// Month-over-Month OEE Change
MoM OEE Change = 
    VAR CurrentOEE = [OEE]
    VAR PreviousOEE = 
        CALCULATE(
            [OEE],
            DATEADD(dim_date[Date], -1, MONTH)
        )
    RETURN
        DIVIDE(
            CurrentOEE - PreviousOEE,
            PreviousOEE,
            0
        )
```

```dax
// Total Units Produced
Total Units = SUM(fact_production[units_produced])
```

```dax
// Failure Count
Failure Count = 
    COUNTROWS(
        FILTER(
            fact_production,
            fact_production[failure_type] <> BLANK()
        )
    )
```

---

## Step 5: Build Report Pages

### Page 1 — Executive Summary

| # | Visual | Field(s) | Notes |
|---|---|---|---|
| 1 | **Gauge** | Value: [OEE] | Target: 0.85, Max: 1.0. Green > 0.85, Yellow > 0.65, Red below |
| 2 | **KPI Card** | Value: [Availability] | Trend: shift_date by month |
| 3 | **KPI Card** | Value: [Performance] | Trend: shift_date by month |
| 4 | **KPI Card** | Value: [Quality] | Trend: shift_date by month |
| 5 | **Clustered Bar** | Axis: machine_id, Value: [Downtime %] | Sort descending. Add conditional formatting (red > 15%) |
| 6 | **Line Chart** | Axis: shift_date (Month), Value: [Defect Rate] | Add trend line |
| 7 | **Card** | Value: [Total Units] | Format with thousands separator |
| 8 | **Card** | Value: [Failure Count] | Red accent color |

**Design tips:**
- Dark background (#1B1B2F or #0F0F23)
- Accent colors: #4CAF50 (green), #FF9800 (amber), #F44336 (red)
- Use ABB brand red (#FF000F) for failure indicators
- Add company logo placeholder top-left

### Page 2 — Drill-down Analysis

| # | Visual | Details |
|---|---|---|
| 1 | **Matrix** | Rows: machine_id, shift; Columns: failure_type; Values: COUNT of records, [Downtime %]. Add conditional formatting with color scales |
| 2 | **Slicer** | Field: dim_date[Date] → Date range slider |
| 3 | **Slicer** | Field: dim_machine[plant_section] → Dropdown |
| 4 | **Slicer** | Field: dim_machine[machine_type] → Buttons (L/M/H) |
| 5 | **Decomposition Tree** | Analyze: [OEE]; Explain by: plant_section → line → machine_id → shift |
| 6 | **Stacked Bar** | Axis: month; Values: failure type counts; Legend: failure_type |

### Page 3 — Documentation

1. Add a **Text Box** with:
   ```
   DATA MODEL
   ─────────
   This dashboard uses a star schema with:
   • fact_production: 10,000 shift-level production records
   • dim_machine: 10 machines across 3 lines and 3 sections
   • dim_date: Calendar year 2023 (365 days)

   DATA SOURCES
   ─────────
   • Primary: AI4I 2020 Predictive Maintenance Dataset (Kaggle/UCI)
   • Supplementary: Shift Incident Log (simulated Google Form)

   ASSUMPTIONS
   ─────────
   • Ideal production rate: 30 units/hour (0.5 units/min)
   • Planned time: 480 min per 8-hour shift
   • OEE = Availability × Performance × Quality
   • World-class OEE benchmark: ≥ 85%
   ```

2. Add a **Table Visual** showing DAX measure reference:
   - Measure Name | Formula | Description

3. Optionally embed the star schema diagram as an image

---

## Step 6: Formatting Best Practices

1. **Consistent color palette** across all pages
2. **Title each visual** clearly
3. **Format percentages** to 1 decimal place
4. **Add tooltips** with drill-through context
5. **Use bookmarks** for toggle views (e.g., Day vs Night comparison)
6. **Add a page navigator** button strip across all pages

---

## Troubleshooting

| Issue | Solution |
|---|---|
| Dates not recognized | Ensure `shift_date` is Date type in Power Query |
| OEE shows blank | Check relationships in Model view — ensure proper joins |
| Slicers don't filter | Verify cross-filter direction is Single (fact → dim) |
| Performance is slow | Use Import mode (not DirectQuery) for CSV/SQLite |
| SQLite driver not found | Install 64-bit SQLite ODBC driver to match Power BI bitness |
