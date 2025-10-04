# Smart City Command Center Architecture Guide

This document describes the architectural flow, database schema, ETL design, and machine learning models of the **Smart City Command Center Analytics Dashboard**.

---

## 1. System Topology

The command center integrates data from 5 municipal departments and exposes them via a REST API backend (FastAPI), a custom executive dashboard UI (HTML/CSS/JS with Leaflet maps), a Python-native Streamlit dashboard, and automated reports.

```
       [Raw CSV Files] ---> [ETL Pipeline (pipeline.py)] ---> [SQLite Database]
                                                                     |
         +-----------------------------------------------------------+-----------------------------------+
         |                                                           |                                   |
         v                                                           v                                   v
  [ML training (train.py)]                                    [FastAPI Server]                 [Streamlit Dashboard]
         |                                                           |                                   |
         v                                                           v                                   v
  [Serialized Models (.joblib)]                                [Static Web App]                   [Plotly Dashboards]
         |                                                           |
         +-------------------> [Inference Engine] <------------------+
```

---

## 2. ETL Data Pipeline Stages

The ETL pipeline (`etl/pipeline.py`) executes standard transaction validation and load protocols:

1. **Extraction**: Reads raw files from `data/raw/` containing traffic sensor logs, power grid logs, water pressure logs, sanitation waste logs, and citizen ticket reports.
2. **Transformation**:
   * Standardizes text spacing (removes padding whitespace).
   * Normalizes timestamps to ISO-8601 (`YYYY-MM-DD HH:MM:SS`).
   * Validates coordinate limits (removes out-of-bound coordinates outside Indore).
   * Fills empty numeric fields (such as `satisfaction_rating` or `resolved_at`) with SQL-compliant `NULL` types.
   * Forces constraints (bounds `congestion_index` strictly between `0.0` and `10.0`).
3. **Load**: Connects to `data/smart_city.db`, applies table indices (optimizing timestamp-based and department-based queries), and executes transactions to update the tables.

---

## 3. Predictive Analytics Modeling

The forecasting engine uses **Scikit-learn** (`models/train.py`) to build robust, fast, and serializable prediction models:

### A. Traffic Congestion Prediction
* **Task**: Regression (estimating current congestion index at an intersection).
* **Model**: Random Forest Regressor ($n=50$, max_depth=10).
* **Features**: Intersection ID, hour of day, day of week, weekend indicator, vehicle count, weather condition (Label Encoded).
* **Validation**: $R^2 \approx 0.95$, indicating very strong predictability of gridlock based on flow sensors and weather.

### B. Water Consumption Forecasting
* **Task**: Auto-regressive Time Series Forecasting.
* **Model**: Random Forest Regressor ($n=50$, max_depth=8).
* **Features**: District ID (Label Encoded), day of week, month, consumption lags (1 day ago, 2 days ago, 7 days ago), rolling averages (3-day and 7-day windows).
* **Approach**: Formulates time-series forecasting as a supervised learning task using lag features. This avoids ARMA convergence complexities.

### C. Citizen Complaint Ticket Load Forecasting
* **Task**: Auto-regressive Forecasting (daily complaint volume per department).
* **Model**: Random Forest Regressor ($n=50$, max_depth=6).
* **Features**: Department ID, day of week, month, ticket count lags (1 day ago, 2 days ago, 7 days ago), rolling averages (3-day and 7-day).
* **Utility**: Helps administrators forecast call-center workloads and staff allocations.

### D. Sanitation Resource Optimization
* **Task**: Regression (estimating trucks needed).
* **Model**: Random Forest Regressor ($n=30$, max_depth=6).
* **Features**: Sector ID, expected waste collected (Tons).
* **Target**: Sanitation Trucks Deployed.
* **Utility**: Automates logistics matching by ensuring the correct number of trucks are scheduled.
