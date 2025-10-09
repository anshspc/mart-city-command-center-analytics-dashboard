import os
import sqlite3
import pandas as pd
import numpy as np

# Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "data/smart_city.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "etl/schema.sql")
RAW_DATA_DIR = os.path.join(BASE_DIR, "data/raw")

def init_db(conn):
    """Executes the DDL schema to initialize tables and indexes."""
    print(f"Reading schema DDL from {SCHEMA_PATH}...")
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    
    cursor = conn.cursor()
    cursor.executescript(schema_sql)
    conn.commit()
    print("Database schema initialized successfully.")

def clean_and_load_departments(conn):
    csv_path = os.path.join(RAW_DATA_DIR, "departments.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing raw CSV: {csv_path}")
    
    print("Ingesting departments...")
    df = pd.read_csv(csv_path)
    
    # Cleaning: strip text fields
    df['department_name'] = df['department_name'].str.strip()
    df['head_of_department'] = df['head_of_department'].str.strip()
    df['contact_number'] = df['contact_number'].str.strip()
    
    # Overwrite departments table (master data)
    df.to_sql('departments', conn, if_exists='replace', index=False, dtype={
        'department_id': 'INTEGER PRIMARY KEY',
        'department_name': 'TEXT NOT NULL',
        'head_of_department': 'TEXT',
        'contact_number': 'TEXT',
        'budget_allocation_million': 'REAL'
    })
    print(f"Loaded {len(df)} departments into database.")

def clean_and_load_complaints(conn):
    csv_path = os.path.join(RAW_DATA_DIR, "complaints.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing raw CSV: {csv_path}")
    
    print("Ingesting complaints...")
    df = pd.read_csv(csv_path)
    
    # Cleaning: Fill empty strings in resolved_at with None (SQLite will treat as NULL)
    df['resolved_at'] = df['resolved_at'].replace({np.nan: None, '': None})
    
    # Satisfaction rating should be numeric, empty values represented as None
    df['satisfaction_rating'] = pd.to_numeric(df['satisfaction_rating'], errors='coerce')
    df['satisfaction_rating'] = df['satisfaction_rating'].astype(object).where(df['satisfaction_rating'].notna(), None)
    
    # Coordinates validation
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # Validate lat/lon limits (NYC coordinates bounds as fallback)
    df = df[df['latitude'].between(22.0, 23.5) & df['longitude'].between(75.0, 76.5)]
    
    # Ingest
    cursor = conn.cursor()
    cursor.execute("DELETE FROM citizen_complaints")
    
    # Insert using sql execution or to_sql (if_exists='append')
    # Since sqlite constraints are verified, append is fine
    df.to_sql('citizen_complaints', conn, if_exists='append', index=False)
    print(f"Cleaned and loaded {len(df)} complaints.")

def clean_and_load_traffic(conn):
    csv_path = os.path.join(RAW_DATA_DIR, "traffic.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing raw CSV: {csv_path}")
    
    print("Ingesting traffic data...")
    df = pd.read_csv(csv_path)
    
    # Validate congestion index limits
    df['congestion_index'] = df['congestion_index'].clip(0.0, 10.0)
    df['vehicle_count'] = df['vehicle_count'].clip(lower=0)
    df['average_speed'] = df['average_speed'].clip(lower=0.0)
    
    # Ensure boolean/integer representation
    df['is_peak_hour'] = df['is_peak_hour'].astype(int)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM traffic_records")
    df.to_sql('traffic_records', conn, if_exists='append', index=False)
    print(f"Cleaned and loaded {len(df)} traffic records.")

def clean_and_load_water(conn):
    csv_path = os.path.join(RAW_DATA_DIR, "water.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing raw CSV: {csv_path}")
    
    print("Ingesting water consumption...")
    df = pd.read_csv(csv_path)
    
    # Validate values
    df['water_consumption_m3'] = df['water_consumption_m3'].clip(lower=0.0)
    df['pressure_bar'] = df['pressure_bar'].clip(lower=0.0)
    df['leak_detected'] = df['leak_detected'].astype(int)
    df['quality_index'] = df['quality_index'].clip(0.0, 100.0)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM water_consumption")
    df.to_sql('water_consumption', conn, if_exists='append', index=False)
    print(f"Cleaned and loaded {len(df)} water consumption logs.")

def clean_and_load_electricity(conn):
    csv_path = os.path.join(RAW_DATA_DIR, "electricity.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing raw CSV: {csv_path}")
    
    print("Ingesting electricity usage...")
    df = pd.read_csv(csv_path)
    
    # Clean data limits
    df['power_consumption_kwh'] = df['power_consumption_kwh'].clip(lower=0.0)
    df['outage_duration_min'] = df['outage_duration_min'].clip(lower=0)
    df['load_factor'] = df['load_factor'].clip(0.0, 1.0)
    df['peak_demand_kwh'] = df['peak_demand_kwh'].clip(lower=0.0)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM electricity_usage")
    df.to_sql('electricity_usage', conn, if_exists='append', index=False)
    print(f"Cleaned and loaded {len(df)} electricity usage records.")

def clean_and_load_sanitation(conn):
    csv_path = os.path.join(RAW_DATA_DIR, "sanitation.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing raw CSV: {csv_path}")
    
    print("Ingesting sanitation records...")
    df = pd.read_csv(csv_path)
    
    # Constraints clipping
    df['waste_collected_tons'] = df['waste_collected_tons'].clip(lower=0.0)
    df['trucks_deployed'] = df['trucks_deployed'].clip(lower=0)
    df['missed_pickups'] = df['missed_pickups'].clip(lower=0)
    df['sanitation_rating'] = df['sanitation_rating'].clip(1.0, 5.0)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sanitation_records")
    df.to_sql('sanitation_records', conn, if_exists='append', index=False)
    print(f"Cleaned and loaded {len(df)} sanitation records.")

def run_etl():
    print("Starting Smart City Command Center ETL Pipeline...")
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        # Step 1: Initialize database schema
        init_db(conn)
        
        # Step 2: Clean and load each table
        clean_and_load_departments(conn)
        clean_and_load_complaints(conn)
        clean_and_load_traffic(conn)
        clean_and_load_water(conn)
        clean_and_load_electricity(conn)
        clean_and_load_sanitation(conn)
        
        print("\nETL Pipeline Completed Successfully!")
        print(f"Database written to: {DB_PATH}")
        
    except Exception as e:
        print(f"\nETL Pipeline FAILED: {str(e)}")
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_etl()
