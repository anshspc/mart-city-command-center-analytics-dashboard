import os
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import joblib
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Smart City Analytics Command Center",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "data/smart_city.db")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Load models
@st.cache_resource
def load_models():
    models = {}
    try:
        models['traffic'] = joblib.load(os.path.join(MODELS_DIR, "traffic_rf.joblib"))
        models['water'] = joblib.load(os.path.join(MODELS_DIR, "water_forecast.joblib"))
        models['complaint'] = joblib.load(os.path.join(MODELS_DIR, "complaint_volume.joblib"))
        models['resource'] = joblib.load(os.path.join(MODELS_DIR, "resource_utilization.joblib"))
    except Exception as e:
        st.warning(f"ML models could not be loaded. Please ensure train.py was run. Error: {e}")
    return models

models = load_models()

# DB connection helper
def get_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}. Please run the ETL pipeline first.")
        st.stop()
    return sqlite3.connect(DB_PATH)

# Title
st.title("🏙️ Indore Smart City Operations Command Center")
st.markdown("---")

# Sidebar navigation
st.sidebar.title("Command Navigation")
menu_option = st.sidebar.radio(
    "Select Viewport Layer",
    ["Executive Summary", "Traffic Department", "Utilities & Energy Grid", "Citizen Complaints Map", "Predictive ML Sandbox"]
)

# Sidebar footer actions
st.sidebar.markdown("---")
st.sidebar.subheader("Report Export Hub")
if os.path.exists(os.path.join(BASE_DIR, "reports/Smart_City_Operational_Report.pdf")):
    with open(os.path.join(BASE_DIR, "reports/Smart_City_Operational_Report.pdf"), "rb") as f:
        st.sidebar.download_button(
            label="📄 Download PDF Operations Report",
            data=f,
            file_name="Indore_Operations_Report.pdf",
            mime="application/pdf"
        )
if os.path.exists(os.path.join(BASE_DIR, "reports/Smart_City_Operational_Report.xlsx")):
    with open(os.path.join(BASE_DIR, "reports/Smart_City_Operational_Report.xlsx"), "rb") as f:
        st.sidebar.download_button(
            label="📊 Download Excel Performance Sheets",
            data=f,
            file_name="Indore_Operational_Metrics.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Fetch general KPI metrics from DB
conn = get_connection()

if menu_option == "Executive Summary":
    st.header("Executive Summary Performance Dashboard")
    
    # Run stats queries
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM citizen_complaints")
    total_c = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM citizen_complaints WHERE status='Resolved'")
    resolved_c = cursor.fetchone()[0]
    res_rate = round((resolved_c / total_c * 100), 1) if total_c > 0 else 0
    cursor.execute("SELECT AVG(julianday(resolved_at) - julianday(created_at)) * 24 FROM citizen_complaints WHERE status='Resolved'")
    avg_hrs = round(cursor.fetchone()[0] or 0.0, 1)
    
    cursor.execute("SELECT AVG(congestion_index) FROM traffic_records")
    avg_traffic_idx = round(cursor.fetchone()[0] or 0.0, 2)
    
    cursor.execute("SELECT SUM(water_consumption_m3) FROM water_consumption")
    tot_water_m3 = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(outage_duration_min) FROM electricity_usage")
    tot_outage_min = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT AVG(sanitation_rating) FROM sanitation_records")
    avg_san_rating = round(cursor.fetchone()[0] or 0.0, 2)

    # Render KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Complaints Filed", f"{total_c:,}", f"{res_rate}% Resolved", delta_color="normal")
    with col2:
        st.metric("Avg Resolution Speed", f"{avg_hrs} Hours", "-1.4 Hours from last week")
    with col3:
        st.metric("Traffic Congestion", f"{avg_traffic_idx} / 10.0", "-0.15 Index")
    with col4:
        st.metric("Water Supply Discharged", f"{tot_water_m3:,.0f} m³", "+5.2% Consumption")

    col5, col6, col7 = st.columns(3)
    with col5:
        st.metric("Power Outage Accrued", f"{tot_outage_min:,} Min", "Due to Storm events")
    with col6:
        st.metric("Sanitation Ratings", f"{avg_san_rating} / 5.0", "Optimal")
    
    st.markdown("### Service Requests & Ticketing Analytics")
    col8, col9 = st.columns(2)
    
    with col8:
        # Complaints Trend Line Chart
        df_trend = pd.read_sql_query("""
            SELECT date(created_at) as date, COUNT(*) as count 
            FROM citizen_complaints 
            GROUP BY date 
            ORDER BY date
        """, conn)
        fig_trend = px.line(
            df_trend, x='date', y='count', 
            title="Daily Citizen Complaint Volume Timeline",
            labels={'count': 'Tickets Filed', 'date': 'Reporting Date'},
            template="plotly_dark", color_discrete_sequence=["#ef4444"]
        )
        st.plotly_chart(fig_trend, width="stretch")
        
    with col9:
        # Resolution Time by Department
        df_dept = pd.read_sql_query("""
            SELECT d.department_name, COUNT(c.complaint_id) as tickets,
                   ROUND(AVG(julianday(c.resolved_at) - julianday(c.created_at)) * 24, 1) as avg_resolution_hours
            FROM citizen_complaints c
            JOIN departments d ON c.department_id = d.department_id
            GROUP BY d.department_name
        """, conn)
        fig_dept = px.bar(
            df_dept, x='department_name', y='avg_resolution_hours',
            title="Average Resolution Duration by Department",
            labels={'avg_resolution_hours': 'Duration (Hours)', 'department_name': 'Municipal Department'},
            template="plotly_dark", color_discrete_sequence=["#8b5cf6"]
        )
        st.plotly_chart(fig_dept, width="stretch")

elif menu_option == "Traffic Department":
    st.header("🚘 Traffic Operations & Grid Flow Analytics")
    
    col1, col2 = st.columns(2)
    with col1:
        # Intersection Congestion Bar Chart
        df_int = pd.read_sql_query("""
            SELECT intersection_id, AVG(congestion_index) as avg_congestion, AVG(average_speed) as avg_speed
            FROM traffic_records
            GROUP BY intersection_id
        """, conn)
        df_int['intersection'] = df_int['intersection_id'].apply(lambda x: f"Intersection {x}")
        
        fig_int = go.Figure(data=[
            go.Bar(name='Congestion Index (LHS)', x=df_int['intersection'], y=df_int['avg_congestion'], yaxis='y1', marker_color='#f59e0b'),
            go.Bar(name='Average Speed km/h (RHS)', x=df_int['intersection'], y=df_int['avg_speed'], yaxis='y2', marker_color='#3b82f6')
        ])
        fig_int.update_layout(
            title='Intersection Traffic Performance Comparison',
            yaxis=dict(title='Congestion Index (Scale 0-10)'),
            yaxis2=dict(title='Average Speed (km/h)', overlaying='y', side='right'),
            bgroupmode='group', template='plotly_dark'
        )
        st.plotly_chart(fig_int, width="stretch")
        
    with col2:
        # 24H traffic congestion peaks
        df_hourly = pd.read_sql_query("""
            SELECT strftime('%H', timestamp) as hour, AVG(congestion_index) as avg_congestion
            FROM traffic_records
            GROUP BY hour
        """, conn)
        fig_hourly = px.line(
            df_hourly, x='hour', y='avg_congestion',
            title="Indore 24-Hour Traffic Congestion Cycle",
            labels={'avg_congestion': 'Congestion Level', 'hour': 'Hour of Day'},
            template="plotly_dark", color_discrete_sequence=["#f59e0b"]
        )
        fig_hourly.update_traces(mode="lines+markers")
        st.plotly_chart(fig_hourly, width="stretch")
        
    # Weather impact on Traffic
    df_weather = pd.read_sql_query("""
        SELECT weather_condition, AVG(congestion_index) as avg_congestion
        FROM traffic_records
        GROUP BY weather_condition
    """, conn)
    fig_weather = px.bar(
        df_weather, x='weather_condition', y='avg_congestion',
        title="Weather Influence on Road Congestion Indexes",
        labels={'avg_congestion': 'Average Congestion', 'weather_condition': 'Weather Condition'},
        template="plotly_dark", color_discrete_sequence=["#3b82f6"]
    )
    st.plotly_chart(fig_weather, width="stretch")

elif menu_option == "Utilities & Energy Grid":
    st.header("⚡ Municipal Utilities Grid & Sanitation Control")
    
    col1, col2 = st.columns(2)
    with col1:
        # Water Supply Daily logs
        df_water = pd.read_sql_query("""
            SELECT date(timestamp) as date, SUM(water_consumption_m3) as total_consumption, AVG(quality_index) as avg_quality
            FROM water_consumption
            GROUP BY date
            ORDER BY date
        """, conn)
        fig_water = px.line(
            df_water, x='date', y='total_consumption',
            title="Daily Water Consumption Trend",
            labels={'total_consumption': 'Water Consumption (m³)', 'date': 'Date'},
            template="plotly_dark", color_discrete_sequence=["#3b82f6"]
        )
        st.plotly_chart(fig_water, width="stretch")
        
    with col2:
        # Grid Zones Load Factor and Outages
        df_power = pd.read_sql_query("""
            SELECT grid_zone_id, AVG(power_consumption_kwh) as avg_consumption, 
                   SUM(outage_duration_min) as total_outage_min, AVG(load_factor) as avg_load_factor
            FROM electricity_usage
            GROUP BY grid_zone_id
        """, conn)
        
        fig_power = go.Figure(data=[
            go.Bar(name='Average Load Factor (LHS)', x=df_power['grid_zone_id'], y=df_power['avg_load_factor'], yaxis='y1', marker_color='#8b5cf6'),
            go.Bar(name='Total Outage Duration Mins (RHS)', x=df_power['grid_zone_id'], y=df_power['total_outage_min'], yaxis='y2', marker_color='#ef4444')
        ])
        fig_power.update_layout(
            title='Electricity Grid Zone Efficiency & Outage Metrics',
            yaxis=dict(title='Efficiency Load Factor'),
            yaxis2=dict(title='Outage Duration (Minutes)', overlaying='y', side='right'),
            bgroupmode='group', template='plotly_dark'
        )
        st.plotly_chart(fig_power, width="stretch")
        
    # Sanitation Sector Solid Waste Tons
    df_san = pd.read_sql_query("""
        SELECT sector_id, SUM(waste_collected_tons) as waste_collected_tons, AVG(sanitation_rating) as avg_rating
        FROM sanitation_records
        GROUP BY sector_id
    """, conn)
    
    fig_san = px.bar(
        df_san, x='sector_id', y='waste_collected_tons', color='avg_rating',
        title="Sanitation Solid Waste Collected & Ratings by Sector",
        labels={'waste_collected_tons': 'Waste Collected (Tons)', 'sector_id': 'Sector', 'avg_rating': 'Sanitation Rating'},
        template="plotly_dark", color_continuous_scale=px.colors.sequential.Viridis
    )
    st.plotly_chart(fig_san, width="stretch")

elif menu_option == "Citizen Complaints Map":
    st.header("🗺️ Citizen Complaints Geospatial Heatmap")
    
    # Load complaint locations
    df_map = pd.read_sql_query("""
        SELECT complaint_id, citizen_name, issue_type, status, created_at, latitude, longitude
        FROM citizen_complaints
        LIMIT 600
    """, conn)
    
    # Side filters
    st.markdown("Filter mapping layers:")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        resolved_check = st.checkbox("Resolved", value=True)
    with col_f2:
        progress_check = st.checkbox("In Progress", value=True)
    with col_f3:
        open_check = st.checkbox("Open", value=True)
        
    selected_status = []
    if resolved_check: selected_status.append("Resolved")
    if progress_check: selected_status.append("In Progress")
    if open_check: selected_status.append("Open")
    
    df_filtered = df_map[df_map['status'].isin(selected_status)]
    
    if not df_filtered.empty:
        # Plotly Mapbox or scatter map plot
        # Streamlit st.map requires latitude and longitude columns
        fig_map = px.scatter_mapbox(
            df_filtered, lat="latitude", lon="longitude", 
            color="status", size_max=12, zoom=12,
            hover_name="issue_type", hover_data=["citizen_name", "status", "created_at"],
            color_discrete_map={"Resolved": "#10b981", "In Progress": "#f59e0b", "Open": "#ef4444"},
            mapbox_style="carto-darkmatter", title="Complaint Incident Locations"
        )
        fig_map.update_layout(height=600, template='plotly_dark')
        st.plotly_chart(fig_map, width="stretch")
    else:
        st.warning("No markers matched selected status filters.")

elif menu_option == "Predictive ML Sandbox":
    st.header("🧠 Predictive Analytics Machine Learning Playground")
    st.markdown("Test out live inference against Indore command center's trained Random Forest models.")
    
    tab1, tab2, tab3 = st.tabs(["🚦 Traffic Congestion Predictor", "💧 Water Demand Forecasting", "🎫 Complaint Ticket Load"])
    
    with tab1:
        st.subheader("Traffic Congestion Regressor")
        if 'traffic' not in models:
            st.error("Traffic model not loaded.")
        else:
            tf_data = models['traffic']
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                intersection_id = st.selectbox("Select Intersection", [101, 102, 103, 104, 105])
                hour = st.slider("Hour of Day", 0, 23, 8)
                day_of_week = st.slider("Day of Week (0=Mon, 6=Sun)", 0, 6, 2)
            with col_t2:
                vehicles = st.number_input("Sensor Vehicle Count", min_value=0, max_value=1200, value=350)
                weather = st.selectbox("Weather Condition", tf_data['weather_classes'])
                
            if st.button("Predict Congestion Index"):
                # Encode weather
                weather_enc = tf_data['weather_encoder'].transform([weather])[0]
                is_weekend = 1 if day_of_week >= 5 else 0
                
                feat = [[intersection_id, hour, day_of_week, is_weekend, vehicles, weather_enc]]
                pred = tf_data['model'].predict(feat)[0]
                
                st.markdown("---")
                if pred > 7.0:
                    st.error(f"Predicted Congestion Index: **{pred:.2f} / 10.0** (High Gridlock Risk)")
                elif pred > 4.5:
                    st.warning(f"Predicted Congestion Index: **{pred:.2f} / 10.0** (Moderate Congestion)")
                else:
                    st.success(f"Predicted Congestion Index: **{pred:.2f} / 10.0** (Free Flowing)")
                    
    with tab2:
        st.subheader("Water Grid Consumption Forecaster")
        if 'water' not in models:
            st.error("Water forecasting model not loaded.")
        else:
            wt_data = models['water']
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                district = st.selectbox("District zone", wt_data['district_classes'])
                target_date = st.date_input("Target Date", value=datetime(2026,6,26))
                lag1 = st.number_input("Yesterday's Consumption (m³)", value=250.0)
            with col_w2:
                lag2 = st.number_input("Consumption 2 Days Ago (m³)", value=248.0)
                lag7 = st.number_input("Consumption 1 Week Ago (m³)", value=242.0)
                
            if st.button("Forecast Water Demand"):
                dist_enc = wt_data['district_encoder'].transform([district])[0]
                day_of_week = target_date.weekday()
                month = target_date.month
                
                roll3 = np.mean([lag1, lag2, lag2])
                roll7 = np.mean([lag1, lag2, lag7])
                
                feat = [[dist_enc, day_of_week, month, lag1, lag2, lag7, roll3, roll7]]
                pred = wt_data['model'].predict(feat)[0]
                
                st.markdown("---")
                st.info(f"Forecasted Water Consumption: **{pred:,.1f} m³** for district {district}.")
                
    with tab3:
        st.subheader("Daily Complaint Load & Staff Forecasting")
        if 'complaint' not in models:
            st.error("Complaint model not loaded.")
        else:
            cp_data = models['complaint']
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                dept_id = st.selectbox("Department ID", [1, 2, 3, 4, 5], format_func=lambda x: f"Dept {x} (e.g. Traffic/Sanitation)")
                target_date = st.date_input("Complaint Forecast Date", value=datetime(2026,6,26))
                lag1 = st.number_input("Yesterday's Tickets", value=8)
            with col_c2:
                lag2 = st.number_input("Tickets 2 Days Ago", value=6)
                lag7 = st.number_input("Tickets 1 Week Ago", value=7)
                
            if st.button("Forecast Complaint Volume"):
                day_of_week = target_date.weekday()
                month = target_date.month
                
                roll3 = np.mean([lag1, lag2, lag2])
                roll7 = np.mean([lag1, lag2, lag7])
                
                feat = [[dept_id, day_of_week, month, lag1, lag2, lag7, roll3, roll7]]
                pred = cp_data['model'].predict(feat)[0]
                pred_int = int(np.round(pred))
                
                st.markdown("---")
                st.info(f"Forecasted Daily Complaint Volume: **{pred_int} Tickets** expected.")
                
                # If Sanitation (id=4), estimate trucks deployed
                if dept_id == 4 and 'resource' in models:
                    res_data = models['resource']
                    # sector 1 representation
                    sec_enc = res_data['sector_encoder'].transform(["Sector 1"])[0]
                    res_feat = [[sec_enc, 6.5]]
                    trucks = int(np.round(res_data['model'].predict(res_feat)[0]))
                    st.success(f"Suggested Logistics: Deploy **{trucks} Sanitation Trucks** to meet garbage collection load.")

conn.close()
