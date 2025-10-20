import os
import sqlite3
import pandas as pd

# Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "data/smart_city.db")
EXCEL_OUT = os.path.join(BASE_DIR, "powerbi/Smart_City_Data.xlsx")

def export_db_to_excel():
    print(f"Reading database tables from {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database missing: {DB_PATH}")
        
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Load tables
        depts = pd.read_sql_query("SELECT * FROM departments", conn)
        complaints = pd.read_sql_query("SELECT * FROM citizen_complaints", conn)
        traffic = pd.read_sql_query("SELECT * FROM traffic_records", conn)
        water = pd.read_sql_query("SELECT * FROM water_consumption", conn)
        electricity = pd.read_sql_query("SELECT * FROM electricity_usage", conn)
        sanitation = pd.read_sql_query("SELECT * FROM sanitation_records", conn)
        
        print("Writing worksheets...")
        with pd.ExcelWriter(EXCEL_OUT, engine='openpyxl') as writer:
            depts.to_excel(writer, sheet_name="Departments", index=False)
            complaints.to_excel(writer, sheet_name="Complaints", index=False)
            traffic.to_excel(writer, sheet_name="Traffic", index=False)
            water.to_excel(writer, sheet_name="Water_Consumption", index=False)
            electricity.to_excel(writer, sheet_name="Electricity_Grid", index=False)
            sanitation.to_excel(writer, sheet_name="Sanitation", index=False)
            
        print(f"Successfully generated Power BI Excel source file: {EXCEL_OUT}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_db_to_excel()
