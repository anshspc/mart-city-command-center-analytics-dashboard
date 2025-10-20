# Power BI Data Model & Report Design Guide

This guide details how to construct the **Smart City Command Center Dashboard** in Power BI Desktop using the datasets generated in the `data/` folder.

---

## 1. Data Connection

To connect Power BI to the project data, you have two options:

### Option A: Connect directly to the SQLite Database (Recommended for Live Sync)
1. Install the **SQLite ODBC Driver** on your system.
2. In Power BI Desktop, go to **Get Data** -> **ODBC**.
3. Select your SQLite DSN or configure a connection string pointing to `data/smart_city.db`.
4. Import all 6 tables: `departments`, `citizen_complaints`, `traffic_records`, `water_consumption`, `electricity_usage`, and `sanitation_records`.

### Option B: Connect to the Aggregated Excel Workbook
1. In Power BI Desktop, select **Get Data** -> **Excel Workbook**.
2. Navigate to `powerbi/Smart_City_Data.xlsx`.
3. Import the loaded sheets.

---

## 2. Data Model Schema (Star / Snowflake Schema)

Power BI automatically detects relationships, but they should be configured as a star schema where `departments` acts as a Dimension table, and others act as Fact tables.

```
       +-------------------------+
       |   departments (Dim)     |
       +-------------------------+
                    |
                    | 1:N (department_id)
                    v
       +-----------------------------+
       |  citizen_complaints (Fact)  |
       +-----------------------------+
```

### Key Relationships:
* **`departments` [1] ---> [N] `citizen_complaints`** on `department_id` (Active relationship, Single filter direction).
* **Calendar Table (Optional but Recommended)**: Create a Date dimension inside Power BI using DAX:
  ```dax
  Calendar = CALENDAR(DATE(2026, 5, 1), DATE(2026, 6, 25))
  ```
  Link `Calendar[Date]` to:
  * `citizen_complaints[created_at]` (Active)
  * `traffic_records[timestamp]` (Inactive)
  * `water_consumption[timestamp]` (Inactive)
  * `electricity_usage[timestamp]` (Inactive)
  * `sanitation_records[timestamp]` (Inactive)

---

## 3. Power BI Pages Layout

We recommend building a 3-page interactive report layout matching executive city needs:

### Page 1: Executive Command Summary
* **Visuals**:
  * **KPI Card 1**: Total Inbound Tickets (Citizen Complaints).
  * **KPI Card 2**: Complaint Resolution Rate (%).
  * **KPI Card 3**: Average Congestion Index.
  * **Line Chart**: Daily ticket volume over time (x-axis: `created_at` date, y-axis: complaint count).
  * **Donut Chart**: Status breakdown (Resolved, In Progress, Open).
  * **Bar Chart**: Ticket volume and avg resolution time by Department.
  * **Slicers**: Date range slider, Status selector.

### Page 2: Smart Utilities & Energy Operations
* **Visuals**:
  * **Line Chart**: Water consumption and water quality index (dual axis: x-axis: date, y1-axis: consumption sum, y2-axis: quality average).
  * **Clustered Column Chart**: Grid zone average load factor and sum of outage minutes (dual axis).
  * **Bar Chart**: Total waste collected tons by sector (colored by Sanitation Rating).
  * **KPI Card**: Leaks detected/repaired and grid downtime minutes.

### Page 3: Traffic & Geospatial Hub
* **Visuals**:
  * **Map Visual**: Plot coordinates (`latitude`, `longitude`) colored by `status` or bubble-sized by `congestion_index` (for traffic).
  * **Line Chart**: 24-hour congestion pattern profile.
  * **Grid Table**: Detailed ticket listing filtered by click-interactions on charts.
