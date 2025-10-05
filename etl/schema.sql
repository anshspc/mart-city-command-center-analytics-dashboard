-- SQL DDL Schema for Smart City Command Center Analytics

-- 1. Departments Master Table
CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL,
    head_of_department TEXT,
    contact_number TEXT,
    budget_allocation_million REAL
);

-- 2. Citizen Complaints Table
CREATE TABLE IF NOT EXISTS citizen_complaints (
    complaint_id INTEGER PRIMARY KEY,
    citizen_name TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    issue_type TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL CHECK(status IN ('Open', 'In Progress', 'Resolved')),
    created_at TEXT NOT NULL, -- Format: YYYY-MM-DD HH:MM:SS
    resolved_at TEXT,         -- Format: YYYY-MM-DD HH:MM:SS (nullable)
    latitude REAL,
    longitude REAL,
    satisfaction_rating INTEGER CHECK(satisfaction_rating IS NULL OR (satisfaction_rating >= 1 AND satisfaction_rating <= 5)),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- 3. Traffic Records Table
CREATE TABLE IF NOT EXISTS traffic_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL, -- Format: YYYY-MM-DD HH:MM:SS
    intersection_id INTEGER NOT NULL,
    congestion_index REAL NOT NULL,
    vehicle_count INTEGER NOT NULL,
    average_speed REAL NOT NULL,
    weather_condition TEXT NOT NULL,
    is_peak_hour INTEGER NOT NULL CHECK(is_peak_hour IN (0, 1))
);

-- 4. Water Consumption Table
CREATE TABLE IF NOT EXISTS water_consumption (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL, -- Format: YYYY-MM-DD HH:MM:SS
    district_id TEXT NOT NULL,
    water_consumption_m3 REAL NOT NULL,
    pressure_bar REAL NOT NULL,
    leak_detected INTEGER NOT NULL CHECK(leak_detected IN (0, 1)),
    quality_index REAL NOT NULL
);

-- 5. Electricity Usage Table
CREATE TABLE IF NOT EXISTS electricity_usage (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL, -- Format: YYYY-MM-DD HH:MM:SS
    grid_zone_id TEXT NOT NULL,
    power_consumption_kwh REAL NOT NULL,
    outage_duration_min INTEGER NOT NULL,
    load_factor REAL NOT NULL,
    peak_demand_kwh REAL NOT NULL
);

-- 6. Sanitation Records Table
CREATE TABLE IF NOT EXISTS sanitation_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL, -- Format: YYYY-MM-DD HH:MM:SS
    sector_id TEXT NOT NULL,
    waste_collected_tons REAL NOT NULL,
    waste_type TEXT NOT NULL,
    trucks_deployed INTEGER NOT NULL,
    missed_pickups INTEGER NOT NULL,
    sanitation_rating REAL NOT NULL
);

-- Create Indexes for Performance optimization
CREATE INDEX IF NOT EXISTS idx_complaints_dept ON citizen_complaints(department_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON citizen_complaints(status);
CREATE INDEX IF NOT EXISTS idx_traffic_timestamp ON traffic_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_water_timestamp ON water_consumption(timestamp);
CREATE INDEX IF NOT EXISTS idx_electricity_timestamp ON electricity_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_sanitation_timestamp ON sanitation_records(timestamp);
