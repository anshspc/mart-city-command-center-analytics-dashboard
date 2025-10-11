import os
import sqlite3
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error, accuracy_score
from sklearn.preprocessing import LabelEncoder

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "data/smart_city.db")
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

def train_traffic_model(conn):
    print("\n--- Training Traffic Congestion Prediction Model ---")
    # Load traffic data
    df = pd.read_sql_query("SELECT timestamp, intersection_id, congestion_index, vehicle_count, weather_condition FROM traffic_records", conn)
    
    # Parse timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    
    # Encode weather
    weather_encoder = LabelEncoder()
    df['weather_encoded'] = weather_encoder.fit_transform(df['weather_condition'])
    
    # Features & Target
    # Predicting congestion index
    features = ['intersection_id', 'hour', 'day_of_week', 'is_weekend', 'vehicle_count', 'weather_encoded']
    X = df[features]
    y = df['congestion_index']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Model
    model = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    
    print(f"Traffic Model Evaluation:")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  MAE:  {mae:.4f}")
    print(f"  R2 Score: {r2:.4f}")
    
    # Save
    model_data = {
        'model': model,
        'features': features,
        'weather_encoder': weather_encoder,
        'weather_classes': weather_encoder.classes_.tolist()
    }
    joblib.dump(model_data, os.path.join(MODELS_DIR, "traffic_rf.joblib"))
    print("Saved traffic_rf.joblib")

def train_water_forecast_model(conn):
    print("\n--- Training Water Consumption Forecasting Model ---")
    # Load daily water usage per district
    # Since water consumption is recorded every 4 hours, let's aggregate to daily for district consumption forecasting
    df_raw = pd.read_sql_query("SELECT timestamp, district_id, water_consumption_m3 FROM water_consumption", conn)
    df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'])
    
    # Aggregate daily
    df_daily = df_raw.groupby([df_raw['timestamp'].dt.date, 'district_id'])['water_consumption_m3'].sum().reset_index()
    df_daily.columns = ['date', 'district_id', 'consumption']
    df_daily['date'] = pd.to_datetime(df_daily['date'])
    df_daily = df_daily.sort_values(by=['district_id', 'date']).reset_index(drop=True)
    
    # Feature engineering: Lags
    # To forecast next day consumption, we use lag features
    forecast_data = []
    
    for dist in df_daily['district_id'].unique():
        df_dist = df_daily[df_daily['district_id'] == dist].copy()
        
        # Create lag features
        df_dist['lag_1'] = df_dist['consumption'].shift(1)
        df_dist['lag_2'] = df_dist['consumption'].shift(2)
        df_dist['lag_7'] = df_dist['consumption'].shift(7)
        df_dist['rolling_mean_3'] = df_dist['consumption'].shift(1).rolling(window=3).mean()
        df_dist['rolling_mean_7'] = df_dist['consumption'].shift(1).rolling(window=7).mean()
        
        # Drop rows with NaN due to shifting
        df_dist = df_dist.dropna()
        forecast_data.append(df_dist)
        
    df_features = pd.concat(forecast_data, ignore_index=True)
    
    # Encode district
    district_encoder = LabelEncoder()
    df_features['district_encoded'] = district_encoder.fit_transform(df_features['district_id'])
    
    # Date variables
    df_features['day_of_week'] = df_features['date'].dt.dayofweek
    df_features['month'] = df_features['date'].dt.month
    
    # Train / Test split (time-based split is standard, but since we want robust validation we can use last 7 days as test)
    # Let's do a simple train/test split for the demo model
    features = ['district_encoded', 'day_of_week', 'month', 'lag_1', 'lag_2', 'lag_7', 'rolling_mean_3', 'rolling_mean_7']
    X = df_features[features]
    y = df_features['consumption']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, shuffle=False) # Temporal order preserved
    
    model = RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    
    print(f"Water Forecast Model Evaluation:")
    print(f"  RMSE: {rmse:.4f} m3")
    print(f"  MAE:  {mae:.4f} m3")
    print(f"  R2 Score: {r2:.4f}")
    
    # Save
    model_data = {
        'model': model,
        'features': features,
        'district_encoder': district_encoder,
        'district_classes': district_encoder.classes_.tolist()
    }
    joblib.dump(model_data, os.path.join(MODELS_DIR, "water_forecast.joblib"))
    print("Saved water_forecast.joblib")

def train_complaint_volume_model(conn):
    print("\n--- Training Complaint Volume Forecasting Model ---")
    # Load complaint dates
    df_raw = pd.read_sql_query("SELECT created_at, department_id FROM citizen_complaints", conn)
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at'])
    df_raw['date'] = df_raw['created_at'].dt.date
    
    # Aggregate: daily complaints per department
    df_daily = df_raw.groupby(['date', 'department_id']).size().reset_index(name='complaint_count')
    df_daily['date'] = pd.to_datetime(df_daily['date'])
    
    # Pivot to make sure all dates and departments are represented
    all_dates = pd.date_range(start=df_daily['date'].min(), end=df_daily['date'].max(), freq='D')
    all_depts = [1, 2, 3, 4, 5]
    
    idx = pd.MultiIndex.from_product([all_dates, all_depts], names=['date', 'department_id'])
    df_grid = pd.DataFrame(index=idx).reset_index()
    
    df_daily = pd.merge(df_grid, df_daily, on=['date', 'department_id'], how='left').fillna(0)
    df_daily = df_daily.sort_values(by=['department_id', 'date']).reset_index(drop=True)
    
    # Feature engineering: lag features
    forecast_data = []
    for dept in all_depts:
        df_dept = df_daily[df_daily['department_id'] == dept].copy()
        
        df_dept['lag_1'] = df_dept['complaint_count'].shift(1)
        df_dept['lag_2'] = df_dept['complaint_count'].shift(2)
        df_dept['lag_7'] = df_dept['complaint_count'].shift(7)
        df_dept['rolling_mean_3'] = df_dept['complaint_count'].shift(1).rolling(window=3).mean()
        df_dept['rolling_mean_7'] = df_dept['complaint_count'].shift(1).rolling(window=7).mean()
        
        df_dept = df_dept.dropna()
        forecast_data.append(df_dept)
        
    df_features = pd.concat(forecast_data, ignore_index=True)
    
    # Temporal features
    df_features['day_of_week'] = df_features['date'].dt.dayofweek
    df_features['month'] = df_features['date'].dt.month
    
    features = ['department_id', 'day_of_week', 'month', 'lag_1', 'lag_2', 'lag_7', 'rolling_mean_3', 'rolling_mean_7']
    X = df_features[features]
    y = df_features['complaint_count']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, shuffle=False)
    
    model = RandomForestRegressor(n_estimators=50, max_depth=6, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    
    print(f"Complaint Volume Model Evaluation:")
    print(f"  RMSE: {rmse:.4f} complaints/day")
    print(f"  MAE:  {mae:.4f} complaints/day")
    print(f"  R2 Score: {r2:.4f}")
    
    # Save
    model_data = {
        'model': model,
        'features': features
    }
    joblib.dump(model_data, os.path.join(MODELS_DIR, "complaint_volume.joblib"))
    print("Saved complaint_volume.joblib")

def train_resource_model(conn):
    print("\n--- Training Resource Utilization Model ---")
    # Predict sanitation trucks deployed based on sector, waste collected, and missed pickups
    # This is a regression model to estimate truck count
    df = pd.read_sql_query("SELECT sector_id, waste_collected_tons, trucks_deployed FROM sanitation_records", conn)
    
    # Encode sector
    sector_encoder = LabelEncoder()
    df['sector_encoded'] = sector_encoder.fit_transform(df['sector_id'])
    
    features = ['sector_encoded', 'waste_collected_tons']
    X = df[features]
    y = df['trucks_deployed']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=30, max_depth=6, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    print(f"Resource Optimization Model Evaluation:")
    print(f"  RMSE (trucks): {rmse:.4f}")
    print(f"  R2 Score: {r2:.4f}")
    
    model_data = {
        'model': model,
        'features': features,
        'sector_encoder': sector_encoder,
        'sector_classes': sector_encoder.classes_.tolist()
    }
    joblib.dump(model_data, os.path.join(MODELS_DIR, "resource_utilization.joblib"))
    print("Saved resource_utilization.joblib")

def main():
    print("Starting Machine Learning Model Training Pipelines...")
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database file not found: {DB_PATH}. Please run the ETL pipeline first.")
        
    conn = sqlite3.connect(DB_PATH)
    try:
        train_traffic_model(conn)
        train_water_forecast_model(conn)
        train_complaint_volume_model(conn)
        train_resource_model(conn)
        print("\nAll machine learning models trained, evaluated, and saved successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
