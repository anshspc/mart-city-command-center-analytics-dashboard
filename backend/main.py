import os
import sqlite3
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "data/smart_city.db")
MODELS_DIR = os.path.join(BASE_DIR, "models")
STATIC_DIR = os.path.join(BASE_DIR, "backend/static")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

app = FastAPI(
    title="Smart City Command Center API",
    description="Backend API serving real-time analytics, machine learning predictions, and reporting for city operations.",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load ML Models
models = {}
def load_ml_models():
    try:
        models['traffic'] = joblib.load(os.path.join(MODELS_DIR, "traffic_rf.joblib"))
        models['water'] = joblib.load(os.path.join(MODELS_DIR, "water_forecast.joblib"))
        models['complaint'] = joblib.load(os.path.join(MODELS_DIR, "complaint_volume.joblib"))
        models['resource'] = joblib.load(os.path.join(MODELS_DIR, "resource_utilization.joblib"))
        print("Successfully loaded all machine learning models.")
    except Exception as e:
        print(f"Warning: Failed to load machine learning models. Ensure train.py has run. Error: {e}")

load_ml_models()

# Helper: Database connection
def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database file not found. Please trigger the ETL pipeline.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# API Models
class TrafficPredictionRequest(BaseModel):
    intersection_id: int
    hour: int
    day_of_week: int
    vehicle_count: int
    weather_condition: str

class WaterPredictionRequest(BaseModel):
    district_id: str
    target_date: str  # Format: YYYY-MM-DD
    historical_consumption: list  # list of previous days' consumption (lag_1, lag_2, lag_7)

class ComplaintPredictionRequest(BaseModel):
    department_id: int
    target_date: str  # Format: YYYY-MM-DD
    historical_volume: list  # list of previous days' volume (lag_1, lag_2, lag_7)

# --- Endpoints ---

@app.get("/api/kpis")
def get_kpis():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Citizen Complaints KPIs
        cursor.execute("SELECT COUNT(*) FROM citizen_complaints")
        total_complaints = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM citizen_complaints WHERE status = 'Resolved'")
        resolved_complaints = cursor.fetchone()[0]
        resolution_rate = round((resolved_complaints / total_complaints * 100), 1) if total_complaints > 0 else 0.0
        
        cursor.execute("""
            SELECT AVG(julianday(resolved_at) - julianday(created_at)) 
            FROM citizen_complaints 
            WHERE status = 'Resolved' AND resolved_at IS NOT NULL
        """)
        avg_res_time_days = cursor.fetchone()[0]
        avg_res_time_hrs = round(avg_res_time_days * 24, 1) if avg_res_time_days else 0.0
        
        # Traffic KPIs (using the latest logged timestamp to represent 'current' state)
        cursor.execute("SELECT MAX(timestamp) FROM traffic_records")
        latest_traffic_ts = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(congestion_index) FROM traffic_records WHERE timestamp = ?", (latest_traffic_ts,))
        current_congestion = round(cursor.fetchone()[0] or 0.0, 2)
        
        # Water consumption (daily sum for the latest date)
        cursor.execute("SELECT MAX(timestamp) FROM water_consumption")
        latest_water_ts = cursor.fetchone()[0]
        latest_water_date = latest_water_ts[:10] if latest_water_ts else ""
        
        cursor.execute("SELECT SUM(water_consumption_m3) FROM water_consumption WHERE timestamp LIKE ?", (latest_water_date + "%",))
        daily_water_m3 = round(cursor.fetchone()[0] or 0.0, 1)
        
        # Electricity Outages (Total outage minutes in the dataset)
        cursor.execute("SELECT SUM(outage_duration_min) FROM electricity_usage")
        total_outage_min = cursor.fetchone()[0] or 0
        
        # Sanitation Rating
        cursor.execute("SELECT AVG(sanitation_rating) FROM sanitation_records")
        avg_sanitation_rating = round(cursor.fetchone()[0] or 0.0, 2)
        
        return {
            "complaints": {
                "total": total_complaints,
                "resolved": resolved_complaints,
                "resolution_rate_pct": resolution_rate,
                "avg_resolution_hours": avg_res_time_hrs
            },
            "traffic": {
                "congestion_index": current_congestion
            },
            "water": {
                "daily_consumption_m3": daily_water_m3
            },
            "electricity": {
                "total_outage_minutes": total_outage_min
            },
            "sanitation": {
                "rating": avg_sanitation_rating
            }
        }
    finally:
        conn.close()

@app.get("/api/charts/traffic")
def get_traffic_chart_data():
    conn = get_db_connection()
    try:
        # 1. Congestion by Intersection
        df_int = pd.read_sql_query("""
            SELECT intersection_id, AVG(congestion_index) as avg_congestion, AVG(average_speed) as avg_speed
            FROM traffic_records
            GROUP BY intersection_id
        """, conn)
        
        # 2. Hourly Profile (Peak vs Off-Peak)
        df_hourly = pd.read_sql_query("""
            SELECT strftime('%H', timestamp) as hour, AVG(congestion_index) as avg_congestion
            FROM traffic_records
            GROUP BY hour
        """, conn)
        
        # 3. Weather impact
        df_weather = pd.read_sql_query("""
            SELECT weather_condition, AVG(congestion_index) as avg_congestion
            FROM traffic_records
            GROUP BY weather_condition
        """, conn)
        
        return {
            "intersections": df_int.to_dict(orient="records"),
            "hourly": df_hourly.to_dict(orient="records"),
            "weather": df_weather.to_dict(orient="records")
        }
    finally:
        conn.close()

@app.get("/api/charts/complaints")
def get_complaints_chart_data():
    conn = get_db_connection()
    try:
        # 1. Status Breakdown
        df_status = pd.read_sql_query("""
            SELECT status, COUNT(*) as count 
            FROM citizen_complaints 
            GROUP BY status
        """, conn)
        
        # 2. Department Breakdown
        df_dept = pd.read_sql_query("""
            SELECT d.department_name, COUNT(c.complaint_id) as count,
                   AVG(julianday(c.resolved_at) - julianday(c.created_at)) * 24 as avg_res_hours
            FROM citizen_complaints c
            JOIN departments d ON c.department_id = d.department_id
            GROUP BY d.department_name
        """, conn)
        # Clean null resolution averages
        df_dept['avg_res_hours'] = df_dept['avg_res_hours'].fillna(0).round(1)
        
        # 3. Issue Types
        df_issues = pd.read_sql_query("""
            SELECT issue_type, COUNT(*) as count
            FROM citizen_complaints
            GROUP BY issue_type
            ORDER BY count DESC
            LIMIT 8
        """, conn)
        
        # 4. Weekly Trend
        df_trend = pd.read_sql_query("""
            SELECT date(created_at) as date, COUNT(*) as count
            FROM citizen_complaints
            GROUP BY date
            ORDER BY date
        """, conn)
        
        return {
            "status": df_status.to_dict(orient="records"),
            "departments": df_dept.to_dict(orient="records"),
            "issues": df_issues.to_dict(orient="records"),
            "trend": df_trend.to_dict(orient="records")
        }
    finally:
        conn.close()

@app.get("/api/charts/utilities")
def get_utilities_chart_data():
    conn = get_db_connection()
    try:
        # 1. Daily water consumption and pressure quality index
        df_water = pd.read_sql_query("""
            SELECT date(timestamp) as date, SUM(water_consumption_m3) as total_consumption, AVG(quality_index) as avg_quality
            FROM water_consumption
            GROUP BY date
            ORDER BY date
        """, conn)
        
        # 2. Grid Zone load factors and total outage duration
        df_power = pd.read_sql_query("""
            SELECT grid_zone_id, AVG(power_consumption_kwh) as avg_consumption, 
                   SUM(outage_duration_min) as total_outage_min, AVG(load_factor) as avg_load_factor
            FROM electricity_usage
            GROUP BY grid_zone_id
        """, conn)
        
        # 3. Sanitation performance by Sector
        df_sanitation = pd.read_sql_query("""
            SELECT sector_id, SUM(waste_collected_tons) as total_waste_tons, 
                   SUM(missed_pickups) as total_missed_pickups, AVG(sanitation_rating) as avg_rating
            FROM sanitation_records
            GROUP BY sector_id
        """, conn)
        
        return {
            "water": df_water.to_dict(orient="records"),
            "electricity": df_power.to_dict(orient="records"),
            "sanitation": df_sanitation.to_dict(orient="records")
        }
    finally:
        conn.close()

@app.get("/api/complaints/geojson")
def get_complaints_geojson():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.complaint_id, c.citizen_name, d.department_name, c.issue_type, 
                   c.status, c.created_at, c.latitude, c.longitude
            FROM citizen_complaints c
            JOIN departments d ON c.department_id = d.department_id
            LIMIT 500 -- Limit to prevent map lag
        """)
        rows = cursor.fetchall()
        
        features = []
        for r in rows:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [r["longitude"], r["latitude"]]
                },
                "properties": {
                    "id": r["complaint_id"],
                    "citizen": r["citizen_name"],
                    "department": r["department_name"],
                    "issue_type": r["issue_type"],
                    "status": r["status"],
                    "created_at": r["created_at"]
                }
            })
            
        return {
            "type": "FeatureCollection",
            "features": features
        }
    finally:
        conn.close()

# --- Predictive Analytics Endpoints ---

@app.post("/api/predict/traffic")
def predict_traffic(req: TrafficPredictionRequest):
    if 'traffic' not in models:
        raise HTTPException(status_code=503, detail="Traffic model not loaded.")
        
    try:
        model_data = models['traffic']
        model = model_data['model']
        weather_encoder = model_data['weather_encoder']
        
        # Encode weather
        try:
            weather_encoded = weather_encoder.transform([req.weather_condition])[0]
        except ValueError:
            # Fallback if unknown weather
            weather_encoded = 0
            
        is_weekend = 1 if req.day_of_week >= 5 else 0
        
        # Prepare feature vector
        # features = ['intersection_id', 'hour', 'day_of_week', 'is_weekend', 'vehicle_count', 'weather_encoded']
        feat_vector = [[
            req.intersection_id,
            req.hour,
            req.day_of_week,
            is_weekend,
            req.vehicle_count,
            weather_encoded
        ]]
        
        prediction = model.predict(feat_vector)[0]
        return {
            "predicted_congestion_index": round(float(prediction), 2),
            "status": "Success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/api/predict/water")
def predict_water(req: WaterPredictionRequest):
    if 'water' not in models:
        raise HTTPException(status_code=503, detail="Water model not loaded.")
        
    try:
        model_data = models['water']
        model = model_data['model']
        district_encoder = model_data['district_encoder']
        
        # Encode district
        try:
            district_encoded = district_encoder.transform([req.district_id])[0]
        except ValueError:
            district_encoded = 0
            
        dt = datetime.strptime(req.target_date, "%Y-%m-%d")
        day_of_week = dt.weekday()
        month = dt.month
        
        # Check historical inputs length
        if len(req.historical_consumption) < 3:
            # fill standard defaults if historical not provided
            lags = [250.0, 240.0, 245.0, 248.0, 246.0] # lag_1, lag_2, lag_7, roll_3, roll_7
        else:
            lag_1 = req.historical_consumption[0]
            lag_2 = req.historical_consumption[1]
            lag_7 = req.historical_consumption[2] if len(req.historical_consumption) > 2 else lag_1
            roll_3 = np.mean([lag_1, lag_2, lag_2])
            roll_7 = np.mean([lag_1, lag_2, lag_7])
            lags = [lag_1, lag_2, lag_7, roll_3, roll_7]
            
        # features = ['district_encoded', 'day_of_week', 'month', 'lag_1', 'lag_2', 'lag_7', 'rolling_mean_3', 'rolling_mean_7']
        feat_vector = [[
            district_encoded,
            day_of_week,
            month,
            *lags
        ]]
        
        prediction = model.predict(feat_vector)[0]
        return {
            "target_date": req.target_date,
            "district_id": req.district_id,
            "predicted_consumption_m3": round(float(prediction), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/api/predict/complaints")
def predict_complaints(req: ComplaintPredictionRequest):
    if 'complaint' not in models:
        raise HTTPException(status_code=503, detail="Complaint volume model not loaded.")
        
    try:
        model_data = models['complaint']
        model = model_data['model']
        
        dt = datetime.strptime(req.target_date, "%Y-%m-%d")
        day_of_week = dt.weekday()
        month = dt.month
        
        if len(req.historical_volume) < 3:
            lags = [5.0, 4.0, 6.0, 5.0, 5.2] # lag_1, lag_2, lag_7, roll_3, roll_7
        else:
            lag_1 = req.historical_volume[0]
            lag_2 = req.historical_volume[1]
            lag_7 = req.historical_volume[2] if len(req.historical_volume) > 2 else lag_1
            roll_3 = np.mean([lag_1, lag_2, lag_2])
            roll_7 = np.mean([lag_1, lag_2, lag_7])
            lags = [lag_1, lag_2, lag_7, roll_3, roll_7]
            
        # features = ['department_id', 'day_of_week', 'month', 'lag_1', 'lag_2', 'lag_7', 'rolling_mean_3', 'rolling_mean_7']
        feat_vector = [[
            req.department_id,
            day_of_week,
            month,
            *lags
        ]]
        
        prediction = model.predict(feat_vector)[0]
        
        # Estimate sanitation trucks needed (resource utilization forecast)
        # Using resource model if department is Sanitation (id = 4)
        est_trucks = None
        if req.department_id == 4 and 'resource' in models:
            res_model_data = models['resource']
            res_model = res_model_data['model']
            sector_encoder = res_model_data['sector_encoder']
            
            # Predict trucks for Sector 1 as representative, assuming 6 tons waste
            sector_encoded = sector_encoder.transform(["Sector 1"])[0]
            truck_feat = [[sector_encoded, 6.5]]
            est_trucks = int(np.round(res_model.predict(truck_feat)[0]))
            
        return {
            "target_date": req.target_date,
            "department_id": req.department_id,
            "predicted_volume": int(np.round(prediction)),
            "suggested_resource_level": est_trucks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

# --- Reports & Pipelines Trigger Endpoints ---

@app.get("/api/reports/download/{report_type}")
def download_report(report_type: str):
    # Determine extension and check if file exists
    if report_type == "pdf":
        file_path = os.path.join(REPORTS_DIR, "Smart_City_Operational_Report.pdf")
        media_type = "application/pdf"
        filename = "Smart_City_Operational_Report.pdf"
    elif report_type == "excel":
        file_path = os.path.join(REPORTS_DIR, "Smart_City_Operational_Report.xlsx")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "Smart_City_Operational_Report.xlsx"
    else:
        raise HTTPException(status_code=400, detail="Invalid report type. Choose 'pdf' or 'excel'.")
        
    # Generate on the fly if missing (requires reports/generator.py execution)
    if not os.path.exists(file_path):
        try:
            print("Report file missing. Generating reports now...")
            import sys
            sys.path.append(REPORTS_DIR)
            import generator
            generator.generate_reports()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")
            
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Requested report could not be generated.")
        
    return FileResponse(file_path, media_type=media_type, filename=filename)

def run_background_pipeline():
    try:
        print("Background task: Starting ETL Pipeline...")
        from etl.pipeline import run_etl
        run_etl()
        
        print("Background task: Starting Model Training...")
        from models.train import main as train_main
        train_main()
        
        print("Background task: Reloading Models in API...")
        load_ml_models()
        
        print("Background task: Refreshing Reports...")
        import sys
        sys.path.append(REPORTS_DIR)
        import generator
        generator.generate_reports()
        
        print("Background task completed successfully!")
    except Exception as e:
        print(f"Background task FAILED: {e}")

@app.post("/api/etl/refresh")
def trigger_etl_refresh(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_background_pipeline)
    return {
        "status": "Accepted",
        "message": "ETL pipeline, ML retraining, and report refresh started in background."
    }

# Serve custom web dashboard static files
# Place this at the end to prevent it overriding /api endpoints
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    
    @app.get("/")
    def read_index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
