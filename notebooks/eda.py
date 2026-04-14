# ============================================================
# Manufacturing KPI Dashboard — Exploratory Data Analysis
# ============================================================
# This script:
#   1. Loads the AI4I 2020 Predictive Maintenance dataset
#   2. Performs EDA (profiling, distributions, correlations)
#   3. Augments the data with synthetic OEE-relevant columns
#   4. Calculates OEE = Availability × Performance × Quality
#   5. Generates a shift incident log (multi-source demo)
#   6. Exports cleaned_production.csv + shift_incident_log.csv
# ============================================================

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "data"
PLOTS_DIR = PROJECT_ROOT / "notebooks" / "plots"
PLOTS_DIR.mkdir(exist_ok=True)

RAW_CSV = DATA_DIR / "ai4i2020.csv"

# ── Plot style ───────────────────────────────────────────────
try:
    plt.style.use('seaborn-darkgrid')
except OSError:
    plt.style.use('ggplot')
sns.set_palette("husl")
FIGSIZE = (12, 6)

print("=" * 60)
print(" MANUFACTURING KPI DASHBOARD — EDA")
print("=" * 60)


# ============================================================
# STEP 1: Load & Profile Raw Data
# ============================================================
print("\n📂 Loading raw dataset...")
df_raw = pd.read_csv(RAW_CSV)

print(f"   Shape: {df_raw.shape[0]:,} rows × {df_raw.shape[1]} columns")
print(f"\n   Columns: {list(df_raw.columns)}")
print(f"\n   Data Types:\n{df_raw.dtypes.to_string()}")
print(f"\n   Null Counts:\n{df_raw.isnull().sum().to_string()}")
print(f"\n   Basic Statistics:\n{df_raw.describe().round(2).to_string()}")

# Check for duplicate rows
dupes = df_raw.duplicated().sum()
print(f"\n   Duplicate rows: {dupes}")

# Product type distribution
print(f"\n   Product Type Distribution:")
print(f"{df_raw['Type'].value_counts().to_string()}")

# Machine failure rate
fail_rate = df_raw['Machine failure'].mean() * 100
print(f"\n   Overall Failure Rate: {fail_rate:.2f}%")


# ============================================================
# STEP 2: EDA Visualizations
# ============================================================
print("\n📊 Generating EDA plots...")

# 2a. Distribution of numerical features
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
fig.suptitle('Distribution of Sensor Readings', fontsize=16, fontweight='bold')

num_cols = ['Air temperature [K]', 'Process temperature [K]',
            'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']
for i, col in enumerate(num_cols):
    ax = axes[i // 3][i % 3]
    df_raw[col].hist(bins=40, ax=ax, edgecolor='black', alpha=0.7)
    ax.set_title(col, fontsize=11)
    ax.set_xlabel('')
    ax.axvline(df_raw[col].mean(), color='red', linestyle='--', alpha=0.8, label='Mean')
    ax.legend(fontsize=8)

axes[1][2].axis('off')
plt.tight_layout()
plt.savefig(PLOTS_DIR / "01_distributions.png", dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ 01_distributions.png")

# 2b. Correlation heatmap
fig, ax = plt.subplots(figsize=(10, 8))
corr_cols = ['Air temperature [K]', 'Process temperature [K]',
             'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]',
             'Machine failure']
corr = df_raw[corr_cols].corr()
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdBu_r',
            center=0, square=True, ax=ax, linewidths=0.5)
ax.set_title('Sensor Correlation Matrix', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(PLOTS_DIR / "02_correlation_heatmap.png", dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ 02_correlation_heatmap.png")

# 2c. Failure type breakdown
failure_cols = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
failure_counts = df_raw[failure_cols].sum().sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(10, 5))
colors = sns.color_palette("viridis", len(failure_counts))
failure_counts.plot(kind='barh', ax=ax, color=colors, edgecolor='black')
ax.set_title('Failure Type Distribution (Pareto)', fontsize=14, fontweight='bold')
ax.set_xlabel('Count')
for i, v in enumerate(failure_counts):
    ax.text(v + 1, i, str(v), va='center', fontweight='bold')
plt.tight_layout()
plt.savefig(PLOTS_DIR / "03_failure_types.png", dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ 03_failure_types.png")

# 2d. Outlier detection (IQR method)
print("\n🔍 Outlier Detection (IQR method):")
for col in num_cols:
    Q1 = df_raw[col].quantile(0.25)
    Q3 = df_raw[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    outliers = ((df_raw[col] < lower) | (df_raw[col] > upper)).sum()
    pct = outliers / len(df_raw) * 100
    print(f"   {col}: {outliers} outliers ({pct:.1f}%)")


# ============================================================
# STEP 3: Data Augmentation for OEE
# ============================================================
print("\n🔧 Augmenting data for OEE calculations...")

np.random.seed(42)
df = df_raw.copy()

# 3a. Assign machine IDs (M001–M010) based on Product ID hash
df['machine_id'] = df['Product ID'].apply(
    lambda x: f"M{(hash(x) % 10 + 1):03d}"
)

# 3b. Generate shift dates (spanning 2023-01-01 to 2023-12-31)
n = len(df)
date_range = pd.date_range('2023-01-01', '2023-12-31', freq='D')
# Repeat dates to fill 10,000 rows, then shuffle
dates = np.tile(date_range, (n // len(date_range)) + 1)[:n]
np.random.shuffle(dates)
df['shift_date'] = pd.to_datetime(dates)

# 3c. Assign shifts (Day / Night)
df['shift'] = np.random.choice(['Day', 'Night'], size=n, p=[0.55, 0.45])

# 3d. Planned time (8-hour shift = 480 min)
df['planned_time_min'] = 480.0

# 3e. Downtime — derived from tool wear + failure flags
# Base downtime: proportional to tool wear (higher wear → more downtime)
base_downtime = (df['Tool wear [min]'] / df['Tool wear [min]'].max()) * 30  # 0–30 min base
# Failure penalty: add 15–60 min for each failure
failure_penalty = df['Machine failure'] * np.random.uniform(15, 60, size=n)
df['downtime_min'] = np.clip(base_downtime + failure_penalty + np.random.normal(5, 3, n), 0, 180).round(1)

# 3f. Run time = planned time - downtime
df['run_time_min'] = (df['planned_time_min'] - df['downtime_min']).round(1)

# 3g. Units produced — based on rotational speed + efficiency
# Higher speed → more units; add noise
ideal_rate_per_min = 0.5  # 30 units per hour
efficiency = np.random.uniform(0.75, 0.95, n)
df['units_produced'] = (df['run_time_min'] * ideal_rate_per_min * efficiency).astype(int)

# 3h. Defects — failure rows get 1–5 defects; non-failure get 0–1
df['defects'] = np.where(
    df['Machine failure'] == 1,
    np.random.randint(1, 6, n),
    np.random.choice([0, 0, 0, 0, 1], n)  # 20% chance of 1 defect even without failure
)

# 3i. Map failure type to a single column
def get_failure_type(row):
    for ft in ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']:
        if row[ft] == 1:
            return ft
    return None

df['failure_type'] = df.apply(get_failure_type, axis=1)

# 3j. Machine metadata (for dim_machine)
machine_meta = {
    'M001': ('L', 'Line A', 'Section 1'), 'M002': ('L', 'Line A', 'Section 1'),
    'M003': ('M', 'Line A', 'Section 2'), 'M004': ('M', 'Line B', 'Section 2'),
    'M005': ('M', 'Line B', 'Section 2'), 'M006': ('H', 'Line B', 'Section 3'),
    'M007': ('H', 'Line C', 'Section 3'), 'M008': ('L', 'Line C', 'Section 1'),
    'M009': ('M', 'Line C', 'Section 2'), 'M010': ('H', 'Line A', 'Section 3'),
}

print(f"   Machines created: {df['machine_id'].nunique()}")
print(f"   Date range: {df['shift_date'].min().date()} to {df['shift_date'].max().date()}")
print(f"   Shifts: {df['shift'].value_counts().to_dict()}")


# ============================================================
# STEP 4: Calculate OEE
# ============================================================
print("\n📈 Calculating OEE metrics...")

# Per-row OEE components
df['availability'] = df['run_time_min'] / df['planned_time_min']
df['performance'] = df['units_produced'] / (df['run_time_min'] * ideal_rate_per_min)
df['quality'] = (df['units_produced'] - df['defects']) / df['units_produced'].replace(0, 1)
df['oee'] = df['availability'] * df['performance'] * df['quality']

# Clip to valid range
df['oee'] = df['oee'].clip(0, 1)
df['availability'] = df['availability'].clip(0, 1)
df['performance'] = df['performance'].clip(0, 1)
df['quality'] = df['quality'].clip(0, 1)

print(f"   Overall OEE:          {df['oee'].mean():.1%}")
print(f"   Avg Availability:     {df['availability'].mean():.1%}")
print(f"   Avg Performance:      {df['performance'].mean():.1%}")
print(f"   Avg Quality:          {df['quality'].mean():.1%}")
print(f"   Total Units Produced: {df['units_produced'].sum():,}")
print(f"   Total Defects:        {df['defects'].sum():,}")
print(f"   Defect Rate:          {df['defects'].sum() / df['units_produced'].sum():.2%}")

# OEE by machine summary
print("\n   OEE by Machine:")
oee_by_machine = df.groupby('machine_id')['oee'].mean().sort_values(ascending=False)
for mid, oee_val in oee_by_machine.items():
    print(f"     {mid}: {oee_val:.1%}")

# 4a. OEE distribution plot
fig, axes = plt.subplots(1, 4, figsize=(18, 5))
for i, (col, title) in enumerate([
    ('availability', 'Availability'), ('performance', 'Performance'),
    ('quality', 'Quality'), ('oee', 'OEE')
]):
    axes[i].hist(df[col], bins=40, edgecolor='black', alpha=0.7, color=sns.color_palette("husl")[i])
    axes[i].axvline(df[col].mean(), color='red', linestyle='--', label=f'Mean: {df[col].mean():.3f}')
    axes[i].set_title(title, fontsize=13, fontweight='bold')
    axes[i].legend()
plt.suptitle('OEE Component Distributions', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "04_oee_distributions.png", dpi=150, bbox_inches='tight')
plt.close()
print("\n   ✅ 04_oee_distributions.png")

# 4b. OEE by machine bar chart
fig, ax = plt.subplots(figsize=(12, 6))
oee_by_machine.plot(kind='bar', ax=ax, color=sns.color_palette("coolwarm", len(oee_by_machine)),
                     edgecolor='black')
ax.axhline(y=0.85, color='green', linestyle='--', alpha=0.7, label='World-class (85%)')
ax.axhline(y=df['oee'].mean(), color='red', linestyle='--', alpha=0.7, label=f'Plant avg ({df["oee"].mean():.1%})')
ax.set_title('OEE by Machine', fontsize=14, fontweight='bold')
ax.set_ylabel('OEE')
ax.set_xlabel('Machine ID')
ax.legend()
ax.set_ylim(0, 1)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "05_oee_by_machine.png", dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ 05_oee_by_machine.png")

# 4c. Monthly OEE trend
monthly_oee = df.groupby(df['shift_date'].dt.to_period('M'))['oee'].mean()
fig, ax = plt.subplots(figsize=(14, 5))
monthly_oee.plot(ax=ax, marker='o', linewidth=2, markersize=6, color='#2196F3')
ax.fill_between(range(len(monthly_oee)), monthly_oee.values, alpha=0.15, color='#2196F3')
ax.axhline(y=0.85, color='green', linestyle='--', alpha=0.7, label='World-class (85%)')
ax.set_title('Monthly OEE Trend (2023)', fontsize=14, fontweight='bold')
ax.set_ylabel('OEE')
ax.set_xlabel('Month')
ax.legend()
plt.tight_layout()
plt.savefig(PLOTS_DIR / "06_monthly_oee_trend.png", dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ 06_monthly_oee_trend.png")

# 4d. Downtime by machine
downtime_by_machine = df.groupby('machine_id')['downtime_min'].sum().sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(10, 6))
downtime_by_machine.plot(kind='barh', ax=ax, color=sns.color_palette("Reds_r", len(downtime_by_machine)),
                          edgecolor='black')
ax.set_title('Total Downtime by Machine (minutes)', fontsize=14, fontweight='bold')
ax.set_xlabel('Total Downtime (min)')
for i, v in enumerate(downtime_by_machine):
    ax.text(v + 10, i, f'{v:,.0f}', va='center', fontweight='bold', fontsize=9)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "07_downtime_by_machine.png", dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ 07_downtime_by_machine.png")

# 4e. Defect rate over time (weekly)
weekly_defects = df.set_index('shift_date').resample('W').agg(
    {'defects': 'sum', 'units_produced': 'sum'}
)
weekly_defects.columns = ['defects', 'produced']
weekly_defects['defect_rate'] = weekly_defects['defects'] / weekly_defects['produced']

fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(weekly_defects.index, weekly_defects['defect_rate'] * 100,
        marker='o', linewidth=1.5, markersize=4, color='#E91E63')
ax.fill_between(weekly_defects.index, weekly_defects['defect_rate'] * 100,
                alpha=0.15, color='#E91E63')
ax.set_title('Weekly Defect Rate Trend (2023)', fontsize=14, fontweight='bold')
ax.set_ylabel('Defect Rate (%)')
ax.set_xlabel('Week')
plt.tight_layout()
plt.savefig(PLOTS_DIR / "08_defect_rate_trend.png", dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ 08_defect_rate_trend.png")


# ============================================================
# STEP 5: Generate Shift Incident Log (Multi-source data)
# ============================================================
print("\n📝 Generating shift incident log...")

np.random.seed(123)
n_incidents = 65

incident_types = ['Mechanical Jam', 'Sensor Malfunction', 'Material Defect',
                  'Calibration Error', 'Power Fluctuation', 'Tooling Break',
                  'Overheating', 'Conveyor Stop']
severities = ['Low', 'Medium', 'High', 'Critical']
operators = ['A. Kumar', 'B. Patel', 'C. Sharma', 'D. Singh', 'E. Reddy']

incidents = pd.DataFrame({
    'incident_id': [f'INC-{i+1:04d}' for i in range(n_incidents)],
    'machine_id': np.random.choice([f'M{i:03d}' for i in range(1, 11)], n_incidents),
    'shift_date': pd.to_datetime(
        np.random.choice(pd.date_range('2023-01-01', '2023-12-31'), n_incidents)
    ),
    'shift': np.random.choice(['Day', 'Night'], n_incidents),
    'incident_type': np.random.choice(incident_types, n_incidents),
    'duration_min': np.random.randint(5, 120, n_incidents),
    'severity': np.random.choice(severities, n_incidents, p=[0.3, 0.35, 0.25, 0.1]),
    'reported_by': np.random.choice(operators, n_incidents),
    'notes': np.random.choice([
        'Resolved with standard procedure',
        'Required maintenance team intervention',
        'Part replacement needed',
        'Temporary fix applied, needs follow-up',
        'Root cause under investigation',
        'Recurring issue — escalated to engineering',
        'Resolved within SLA',
        'Machine restarted after cooldown',
    ], n_incidents)
})

incidents = incidents.sort_values('shift_date').reset_index(drop=True)
incidents.to_csv(OUTPUT_DIR / "shift_incident_log.csv", index=False)
print(f"   ✅ Saved {len(incidents)} incidents to data/shift_incident_log.csv")
print(f"   Incident types: {incidents['incident_type'].nunique()}")
print(f"   Severity distribution:\n{incidents['severity'].value_counts().to_string()}")


# ============================================================
# STEP 6: Export Cleaned Production CSV
# ============================================================
print("\n💾 Exporting cleaned production data...")

export_cols = [
    'machine_id', 'shift_date', 'shift',
    'planned_time_min', 'run_time_min', 'downtime_min',
    'units_produced', 'defects', 'failure_type',
    'Air temperature [K]', 'Process temperature [K]',
    'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]',
    'availability', 'performance', 'quality', 'oee'
]

# Rename sensor columns for cleaner export
df_export = df[export_cols].copy()
df_export.columns = [
    'machine_id', 'shift_date', 'shift',
    'planned_time_min', 'run_time_min', 'downtime_min',
    'units_produced', 'defects', 'failure_type',
    'air_temp_k', 'process_temp_k',
    'rotational_speed_rpm', 'torque_nm', 'tool_wear_min',
    'availability', 'performance', 'quality', 'oee'
]

# Sort by date and machine
df_export = df_export.sort_values(['shift_date', 'machine_id']).reset_index(drop=True)

# Save
df_export.to_csv(OUTPUT_DIR / "cleaned_production.csv", index=False)
print(f"   ✅ Saved {len(df_export):,} rows to data/cleaned_production.csv")
print(f"   Columns: {list(df_export.columns)}")


# ============================================================
# STEP 7: Save Machine Metadata for dim_machine
# ============================================================
print("\n💾 Exporting machine metadata...")

machine_df = pd.DataFrame([
    {'machine_id': mid, 'machine_type': meta[0], 'line': meta[1], 'plant_section': meta[2]}
    for mid, meta in machine_meta.items()
])
machine_df.to_csv(OUTPUT_DIR / "dim_machine.csv", index=False)
print(f"   ✅ Saved {len(machine_df)} machines to data/dim_machine.csv")


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print(" EDA COMPLETE — Summary")
print("=" * 60)
print(f"""
  Raw data:            {RAW_CSV.name} ({df_raw.shape[0]:,} rows)
  Cleaned data:        cleaned_production.csv ({len(df_export):,} rows)
  Incident log:        shift_incident_log.csv ({len(incidents)} incidents)
  Machine metadata:    dim_machine.csv ({len(machine_df)} machines)
  Plots generated:     {len(list(PLOTS_DIR.glob('*.png')))} charts in notebooks/plots/

  OEE Summary:
    Overall OEE:       {df['oee'].mean():.1%}
    Availability:      {df['availability'].mean():.1%}
    Performance:       {df['performance'].mean():.1%}
    Quality:           {df['quality'].mean():.1%}
    Defect Rate:       {df['defects'].sum() / df['units_produced'].sum():.2%}

  Next step: Run sql/load_data.py to load into SQLite
""")
