import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Output directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
RAW_DATA_DIR = os.path.join(BASE_DIR, "data/raw")
os.makedirs(RAW_DATA_DIR, exist_ok=True)

# Generate timestamps
start_date = datetime(2026, 5, 1)
end_date = datetime(2026, 6, 25)
date_range = pd.date_range(start=start_date, end=end_date, freq='h')

# 1. Departments Master Table (Indore Municipal Context)
departments_data = [
    {"department_id": 1, "department_name": "IMC Traffic & Roads", "head_of_department": "Rajesh Sharma", "contact_number": "+91-731-0192", "budget_allocation_million": 455.0},
    {"department_id": 2, "department_name": "IMC Water Works Dept", "head_of_department": "Amit Patel", "contact_number": "+91-731-0143", "budget_allocation_million": 382.0},
    {"department_id": 3, "department_name": "MPWZ Electricity Board", "head_of_department": "Preeti Vyas", "contact_number": "+91-731-0177", "budget_allocation_million": 520.0},
    {"department_id": 4, "department_name": "Swachh Indore Waste Management", "head_of_department": "Sanjay Verma", "contact_number": "+91-731-0155", "budget_allocation_million": 298.0},
    {"department_id": 5, "department_name": "IMC 311 Help Desk", "head_of_department": "Divya Choudhary", "contact_number": "+91-731-0188", "budget_allocation_million": 154.0}
]
df_departments = pd.DataFrame(departments_data)
df_departments.to_csv(os.path.join(RAW_DATA_DIR, "departments.csv"), index=False)
print("Generated Indore departments.csv")

# 2. Traffic Department Data (hourly logs for 5 Indore intersections)
intersections = [101, 102, 103, 104, 105] # Regal Sq, Vijay Nagar Sq, Bhawarkua Sq, Geeta Bhawan Sq, Palasia Sq
traffic_records = []
weather_options = ["Sunny", "Rainy", "Foggy"]
weather_weights = [0.80, 0.15, 0.05]

# Prepare weather timeline
weather_timeline = np.random.choice(weather_options, size=len(date_range), p=weather_weights)

for i, timestamp in enumerate(date_range):
    hour = timestamp.hour
    day_of_week = timestamp.dayofweek
    weather = weather_timeline[i]
    
    is_weekend = 1 if day_of_week >= 5 else 0
    is_peak = 1 if (hour in [8, 9, 10, 17, 18, 19]) and (not is_weekend) else 0
    
    weather_mult = 1.0
    if weather == "Rainy":
        weather_mult = 1.4
    elif weather == "Foggy":
        weather_mult = 1.2
        
    for intersection in intersections:
        # Base traffic multiplier per Indore square
        # Regal (101) & Vijay Nagar (102) are major congested squares
        intersection_base = 1.6 if intersection in [101, 102] else (1.2 if intersection == 103 else 0.9)
        
        # Peak timing adjustments
        if hour in [8, 9, 10, 17, 18, 19]:
            congestion_base = 6.8
            vehicle_base = 400
            speed_base = 15
        elif hour in [7, 11, 12, 13, 14, 15, 16, 20, 21]:
            congestion_base = 4.2
            vehicle_base = 250
            speed_base = 30
        elif hour in [23, 0, 1, 2, 3, 4, 5]:
            congestion_base = 0.7
            vehicle_base = 20
            speed_base = 50
        else:
            congestion_base = 2.0
            vehicle_base = 100
            speed_base = 40

        if is_weekend:
            congestion_base *= 0.65
            vehicle_base *= 0.65
            speed_base *= 1.25

        congestion = min(10.0, max(0.0, (congestion_base * intersection_base * weather_mult) + np.random.normal(0, 0.4)))
        vehicles = int(max(5, (vehicle_base * intersection_base * weather_mult) + np.random.normal(0, 25)))
        avg_speed = max(5.0, (speed_base / (weather_mult * (0.8 + 0.1 * congestion))) + np.random.normal(0, 2.5))
        
        traffic_records.append({
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "intersection_id": intersection,
            "congestion_index": round(congestion, 2),
            "vehicle_count": vehicles,
            "average_speed": round(avg_speed, 1),
            "weather_condition": weather,
            "is_peak_hour": is_peak
        })

df_traffic = pd.DataFrame(traffic_records)
df_traffic.to_csv(os.path.join(RAW_DATA_DIR, "traffic.csv"), index=False)
print(f"Generated traffic.csv ({len(df_traffic)} rows)")

# 3. Water Supply Department (daily data per Indore District/Zone)
water_records = []
districts = ["Rajwada Central", "Vijay Nagar", "Palasia", "Sudama Nagar", "Bhawarkua"]
water_date_range = pd.date_range(start=start_date, end=end_date, freq='4h')

for timestamp in water_date_range:
    hour = timestamp.hour
    day_of_week = timestamp.dayofweek
    month = timestamp.month
    
    # Peak water demand in morning
    if hour in [4, 8]:
        hour_factor = 1.5
    elif hour in [16, 20]:
        hour_factor = 1.1
    else:
        hour_factor = 0.6
        
    for dist in districts:
        dist_factor = 1.4 if dist == "Vijay Nagar" else (1.1 if dist == "Palasia" else 0.85)
        base_cons = 160.0
        
        temp_trend = 1.2 if month == 6 else 1.0 # High water demand in hot June summer of Central India
        
        consumption = base_cons * dist_factor * hour_factor * temp_trend + np.random.normal(0, 12)
        consumption = max(10.0, consumption)
        
        leak = 1 if (random.random() < 0.012) else 0
        
        if leak:
            pressure = max(0.8, 1.8 + np.random.normal(0, 0.2))
            consumption *= 1.3
        else:
            pressure = max(2.0, 4.0 + np.random.normal(0, 0.3))
            
        quality = min(100.0, max(60.0, 97.0 + np.random.normal(0, 1.2) - (6.0 if leak else 0.0)))
        
        water_records.append({
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "district_id": dist,
            "water_consumption_m3": round(consumption, 2),
            "pressure_bar": round(pressure, 2),
            "leak_detected": leak,
            "quality_index": round(quality, 1)
        })

df_water = pd.DataFrame(water_records)
df_water.to_csv(os.path.join(RAW_DATA_DIR, "water.csv"), index=False)
print(f"Generated water.csv ({len(df_water)} rows)")

# 4. Electricity Department Data (MPWZ Grid Zones)
electricity_records = []
grid_zones = ["Vijay Nagar Grid (Res)", "Pithampur Hub (Ind)", "Rajwada Central (Comm)", "Palasia Grid (Sub)", "Bhawarkua Grid (Edu)"]

for i, timestamp in enumerate(date_range):
    hour = timestamp.hour
    day_of_week = timestamp.dayofweek
    weather = weather_timeline[i]
    is_weekend = 1 if day_of_week >= 5 else 0
    
    for zone in grid_zones:
        if zone == "Pithampur Hub (Ind)":
            base_demand = 1200.0  # Heavy load in Pithampur manufacturing area
            hour_profile = 1.1 if (8 <= hour <= 19) else 0.7
            if is_weekend:
                hour_profile *= 0.5
        elif zone == "Rajwada Central (Comm)":
            base_demand = 650.0
            hour_profile = 1.5 if (10 <= hour <= 22) else 0.3
            if is_weekend:
                hour_profile *= 0.8
        elif zone == "Bhawarkua Grid (Edu)":
            base_demand = 380.0
            hour_profile = 1.2 if (9 <= hour <= 18) else 0.5
            if is_weekend:
                hour_profile *= 0.4
        else: # Residential grids (Vijay Nagar, Palasia)
            base_demand = 400.0
            if hour in [6, 7, 8, 9]:
                hour_profile = 1.3
            elif hour in [18, 19, 20, 21, 22, 23]:
                hour_profile = 1.6
            else:
                hour_profile = 0.65
            if is_weekend:
                hour_profile *= 1.15
        
        # June temperature peaks (AC power load)
        temp_mult = 1.25 if timestamp.month == 6 else 1.0
        if weather == "Rainy":
            temp_mult *= 0.9  # cool breeze
            
        consumption = base_demand * hour_profile * temp_mult + np.random.normal(0, base_demand * 0.04)
        consumption = max(15.0, consumption)
        
        is_stormy = 1 if weather == "Rainy" and random.random() < 0.08 else 0
        overload = 1 if consumption > base_demand * 1.55 else 0
        
        outage = 0
        outage_duration = 0
        if is_stormy and random.random() < 0.20:
            outage = 1
            outage_duration = random.randint(20, 150)
        elif overload and random.random() < 0.06:
            outage = 1
            outage_duration = random.randint(10, 50)
            
        if outage:
            consumption *= (1.0 - (outage_duration / 60.0))
            consumption = max(5.0, consumption)
            
        load_factor = min(0.99, max(0.15, (consumption / (base_demand * 1.7)) + np.random.normal(0, 0.015)))
        peak_demand = consumption * (1.12 + abs(np.random.normal(0, 0.04)))
        
        electricity_records.append({
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "grid_zone_id": zone,
            "power_consumption_kwh": round(consumption, 2),
            "outage_duration_min": outage_duration,
            "load_factor": round(load_factor, 3),
            "peak_demand_kwh": round(peak_demand, 2)
        })

df_electricity = pd.DataFrame(electricity_records)
df_electricity.to_csv(os.path.join(RAW_DATA_DIR, "electricity.csv"), index=False)
print(f"Generated electricity.csv ({len(df_electricity)} rows)")

# 5. Sanitation Department Records (Daily per Sector, Indore municipal sectors)
sanitation_records = []
sectors = ["Rajwada Sector", "Vijay Nagar Sector", "Palasia Sector", "Bhawarkua Sector", "Sudama Nagar Sector", "Khajrana Sector", "Annapurna Sector", "LIG Sector"]
sanitation_dates = pd.date_range(start=start_date, end=end_date, freq='12h')

for timestamp in sanitation_dates:
    shift = "Morning" if timestamp.hour == 0 else "Evening"
    
    for sec in sectors:
        # Waste generated base
        base_waste = 5.0 if "Vijay Nagar" in sec or "Rajwada" in sec else 3.5
        
        shift_mult = 1.4 if shift == "Morning" else 0.6
        is_weekend = 1 if timestamp.dayofweek >= 5 else 0
        weekend_mult = 1.15 if is_weekend else 1.0
        
        waste = base_waste * shift_mult * weekend_mult + np.random.normal(0, 0.5)
        waste = max(0.5, waste)
        
        # Waste type
        waste_type = np.random.choice(["Organic", "Recyclable", "Hazardous"], p=[0.65, 0.28, 0.07])
        
        # Trucks deployed (efficient Swachh Indore routing)
        trucks = int(max(1, np.ceil(waste / 2.5)))
        
        missed = 0
        # Very efficient collection in Indore (lowest missed stops)
        if random.random() < 0.015:
            missed = random.randint(1, 2)
            
        # Ratings typically very high for Indore (cleanest city)
        rating = min(5.0, max(3.0, 4.85 - 0.7 * missed + np.random.normal(0, 0.1)))
        
        sanitation_records.append({
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "sector_id": sec,
            "waste_collected_tons": round(waste, 2),
            "waste_type": waste_type,
            "trucks_deployed": trucks,
            "missed_pickups": missed,
            "sanitation_rating": round(rating, 2)
        })

df_sanitation = pd.DataFrame(sanitation_records)
df_sanitation.to_csv(os.path.join(RAW_DATA_DIR, "sanitation.csv"), index=False)
print(f"Generated sanitation.csv ({len(df_sanitation)} rows)")

# 6. Citizen Complaints - IMC 311 Helpline System (~2000 rows around Indore)
complaints_records = []
names_list = ["Amit", "Sunita", "Rahul", "Priya", "Vijay", "Neeta", "Sanjay", "Anjali", "Rakesh", "Kiran", "Deepak", "Sandhya"]
surnames_list = ["Sharma", "Verma", "Joshi", "Patel", "Gupta", "Mishra", "Choudhary", "Rao", "Nair", "Singh", "Yadav", "Trivedi"]

# Indore coordinates center
city_lat, city_lon = 22.7196, 75.8577

issue_catalog = {
    1: [
        ("Traffic Signal Failure", "The traffic signal lights at Regal Square are non-functional.", 1.0),
        ("Illegal Parking", "Encroachment and illegal parking blocking the road near Vijay Nagar.", 0.4),
        ("Pothole Congestion", "Large potholes on Bypass road causing slow traffic movement.", 3.0),
        ("Road Obstruction", "Tree branch blocking traffic path on Palasia Main Road.", 0.6)
    ],
    2: [
        ("Water Leakage", "Water leakage from the main pipeline near Rajwada Palace.", 2.0),
        ("Low Water Pressure", "Low pressure supply in Sudama Nagar homes.", 1.5),
        ("Dirty Water Supply", "Turbid drinking water supply reported in Bhawarkua.", 3.5),
        ("Broken Pipe", "Narmada water pipeline damaged during road construction.", 1.2)
    ],
    3: [
        ("Power Outage", "Complete blackout in LIG Colony area.", 1.5),
        ("Flickering Lights", "Voltage fluctuations in Annapurna area damaging home appliances.", 2.5),
        ("Fallen Power Line", "Live wire snapped and fell near Khajrana temple.", 0.2),
        ("Streetlight Out", "Dark streetlights making Palasia square unsafe.", 4.0)
    ],
    4: [
        ("Garbage Pile Up", "Garbage collection bin overflowing in Vijay Nagar.", 1.5),
        ("Missed Waste Collection", "IMC garbage collection vehicle missed our lane today.", 1.0),
        ("Clogged Drain", "Clogged drainage line causing overflow near Bhawarkua.", 2.2),
        ("Odor Complaint", "Foul smell coming from public dumpyard.", 3.0)
    ],
    5: [
        ("Public Park Maintenance", "Overgrown grass and broken slides in Meghdoot Garden.", 5.0),
        ("Stray Animal Hazard", "Stray cattle causing traffic hazard near Regal Square.", 1.2),
        ("Noise Pollution", "Loudspeakers running past curfew hours near Bhawarkua student hostels.", 0.5),
        ("Sidewalk Damage", "Damaged tiles on footpath near Rajwada market.", 3.5)
    ]
}

for cid in range(1, 2001):
    citizen = f"{random.choice(names_list)} {random.choice(surnames_list)}"
    dept_id = random.randint(1, 5)
    issue_type, base_desc, avg_resolution_days = random.choice(issue_catalog[dept_id])
    
    desc = f"{base_desc} Registered via Indore 311 Citizen Helpline."
    
    rand_offset_sec = random.randint(0, int((end_date - start_date).total_seconds()))
    created_dt = start_date + timedelta(seconds=rand_offset_sec)
    
    days_old = (end_date - created_dt).days
    
    if days_old > 15:
        status = np.random.choice(["Resolved", "In Progress"], p=[0.95, 0.05])
    elif days_old > 5:
        status = np.random.choice(["Resolved", "In Progress", "Open"], p=[0.65, 0.27, 0.08])
    else:
        status = np.random.choice(["Resolved", "In Progress", "Open"], p=[0.25, 0.45, 0.30])
        
    resolved_dt = None
    satisfaction = None
    
    if status == "Resolved":
        actual_days = np.random.lognormal(mean=np.log(avg_resolution_days), sigma=0.45)
        actual_days = max(0.1, min(actual_days, days_old))
        resolved_dt = created_dt + timedelta(days=actual_days)
        
        if actual_days <= avg_resolution_days:
            satisfaction = int(np.random.choice([5, 4, 3], p=[0.7, 0.2, 0.1]))
        else:
            satisfaction = int(np.random.choice([4, 3, 2, 1], p=[0.3, 0.4, 0.2, 0.1]))
            
    # Spatial offsets around Indore center (Rajwada/Regal Sq area)
    district_angle = random.random() * 2.0 * np.pi
    if random.random() < 0.25: # Hotspot A (Vijay Nagar - North)
        lat_offset = np.random.normal(0.015, 0.004)
        lon_offset = np.random.normal(0.015, 0.004)
    elif random.random() < 0.20: # Hotspot B (Bhawarkua - South)
        lat_offset = np.random.normal(-0.018, 0.003)
        lon_offset = np.random.normal(-0.008, 0.003)
    else: # General spread
        radius = np.sqrt(random.random()) * 0.035
        lat_offset = radius * np.sin(district_angle)
        lon_offset = radius * np.cos(district_angle)
        
    lat = city_lat + lat_offset
    lon = city_lon + lon_offset
    
    complaints_records.append({
        "complaint_id": cid,
        "citizen_name": citizen,
        "department_id": dept_id,
        "issue_type": issue_type,
        "description": desc,
        "status": status,
        "created_at": created_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "resolved_at": resolved_dt.strftime("%Y-%m-%d %H:%M:%S") if resolved_dt else "",
        "latitude": round(lat, 5),
        "longitude": round(lon, 5),
        "satisfaction_rating": satisfaction if satisfaction else ""
    })

df_complaints = pd.DataFrame(complaints_records)
df_complaints.to_csv(os.path.join(RAW_DATA_DIR, "complaints.csv"), index=False)
print(f"Generated complaints.csv ({len(df_complaints)} rows)")

print("\nIndore District Sample Data Generation Complete!")
print(f"Total Rows generated: {len(df_departments) + len(df_traffic) + len(df_water) + len(df_electricity) + len(df_sanitation) + len(df_complaints)}")
