// --- Smart City Command Center Application JS ---

document.addEventListener("DOMContentLoaded", () => {
    // Current Time
    document.getElementById("current-time-display").innerText = `Active Session | ${new Date().toLocaleString()}`;

    // App state
    let map = null;
    let mapMarkers = [];
    let complaintsData = null; // Store complaints geojson
    let charts = {};

    // 1. Navigation Tab Switching with Hash Routing
    const navItems = document.querySelectorAll(".nav-item");
    const tabContents = document.querySelectorAll(".tab-content");
    const pageTitle = document.getElementById("page-title");

    const tabMapping = {
        "": "dashboard-section",
        "#summary": "dashboard-section",
        "#traffic": "traffic-section",
        "#utilities": "utilities-section",
        "#complaints": "complaints-section",
        "#sandbox": "sandbox-section"
    };

    function handleRouting() {
        const hash = window.location.hash;
        const targetId = tabMapping[hash] || "dashboard-section";

        // Remove active class from all
        navItems.forEach(item => {
            const dataTarget = item.getAttribute("data-target");
            if (dataTarget === targetId) {
                item.classList.add("active");
                pageTitle.innerText = item.textContent.trim();
            } else {
                item.classList.remove("active");
            }
        });

        tabContents.forEach(content => {
            if (content.id === targetId) {
                content.classList.add("active");
            } else {
                content.classList.remove("active");
            }
        });

        // Special initializations
        if (targetId === "complaints-section") {
            initMap();
        }
    }

    // Attach click listeners to update hash
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const dataTarget = item.getAttribute("data-target");
            const targetHash = Object.keys(tabMapping).find(key => tabMapping[key] === dataTarget && key !== "");
            window.location.hash = targetHash || "";
        });
    });

    window.addEventListener("hashchange", handleRouting);
    // Trigger routing immediately on DOMContentLoaded
    handleRouting();

    // 2. Fetch KPIs
    async function loadKPIs() {
        try {
            const res = await fetch("/api/kpis");
            const data = await res.json();

            // Set text values
            document.getElementById("kpi-val-complaints").innerText = data.complaints.total.toLocaleString();
            document.getElementById("kpi-val-resrate").innerText = data.complaints.resolution_rate_pct;
            document.getElementById("kpi-val-restime").innerText = data.complaints.avg_resolution_hours;
            document.getElementById("kpi-val-traffic").innerText = data.traffic.congestion_index.toFixed(2);
            document.getElementById("kpi-val-water").innerText = data.water.daily_consumption_m3.toLocaleString();
            document.getElementById("val-power-outages").innerText = data.electricity.total_outage_minutes.toLocaleString();
            document.getElementById("val-sanitation-rating").innerText = data.sanitation.rating.toFixed(2);
        } catch (err) {
            console.error("Error loading KPIs:", err);
        }
    }

    // 3. Load Charts
    async function loadDashboardCharts() {
        try {
            // 3.1 Complaints Trends
            const compRes = await fetch("/api/charts/complaints");
            const compData = await compRes.json();

            // Render Complaint Trends
            const trendDates = compData.trend.map(d => d.date);
            const trendCounts = compData.trend.map(d => d.count);
            
            renderLineChart("complaintsTrendChart", trendDates, trendCounts, "Daily Incidents", "#ef4444");

            // Render Resolution Hours by Dept
            const deptNames = compData.departments.map(d => d.department_name);
            const deptHours = compData.departments.map(d => d.avg_res_hours);
            
            renderBarChart("deptResolutionChart", deptNames, deptHours, "Resolution Hours", "#8b5cf6");

            // Render Complaint Status Doughnut
            const statusLabels = compData.status.map(s => s.status);
            const statusCounts = compData.status.map(s => s.count);
            
            renderDoughnutChart("complaintStatusChart", statusLabels, statusCounts, ["#10b981", "#f59e0b", "#ef4444"]);

            // Populate Trending Issues List
            const issuesList = document.getElementById("trending-issues-list");
            if (issuesList) {
                issuesList.innerHTML = "";
                compData.issues.forEach(issue => {
                    const li = document.createElement("li");
                    li.innerHTML = `<span>${issue.issue_type}</span><span class="count">${issue.count}</span>`;
                    issuesList.appendChild(li);
                });
            }

            // 3.2 Utilities data
            const utilRes = await fetch("/api/charts/utilities");
            const utilData = await utilRes.json();

            // Water Trend
            const waterDates = utilData.water.map(w => w.date);
            const waterCons = utilData.water.map(w => w.total_consumption);
            const waterQual = utilData.water.map(w => w.avg_quality);
            renderDoubleLineChart("waterTrendChart", waterDates, waterCons, "Water Consumption (m³)", waterQual, "Quality Index (0-100)");

            // Electricity Zone Load
            const powerZones = utilData.electricity.map(e => e.grid_zone_id);
            const powerLoads = utilData.electricity.map(e => e.avg_load_factor);
            const powerOutage = utilData.electricity.map(e => e.total_outage_min);
            renderUtilityBarChart("powerZoneChart", powerZones, powerLoads, "Avg Load Factor", powerOutage, "Outage Duration (min)");

            // Sanitation Sector Waste
            const sanitationSectors = utilData.sanitation.map(s => s.sector_id);
            const sanitationWaste = utilData.sanitation.map(s => s.total_waste_tons);
            const sanitationRating = utilData.sanitation.map(s => s.avg_rating);
            renderDoubleUtilityChart("sanitationSectorChart", sanitationSectors, sanitationWaste, "Waste Collected (Tons)", sanitationRating, "Sanitation Rating (1-5)");

            // 3.3 Traffic data
            const trafficRes = await fetch("/api/charts/traffic");
            const trafficData = await trafficRes.json();

            // Intersections Congestion Bar
            const intersections = trafficData.intersections.map(t => `Intersection ${t.intersection_id}`);
            const congestionVals = trafficData.intersections.map(t => t.avg_congestion);
            const speedVals = trafficData.intersections.map(t => t.avg_speed);
            renderTrafficCompareChart("trafficIntersectionChart", intersections, congestionVals, "Avg Congestion Index", speedVals, "Avg Speed (km/h)");

            // Hourly Traffic Curve
            const hourlyLabels = trafficData.hourly.map(t => `${t.hour}:00`);
            const hourlyVals = trafficData.hourly.map(t => t.avg_congestion);
            renderLineChart("trafficHourlyChart", hourlyLabels, hourlyVals, "Hourly Congestion Index", "#f59e0b");

            // Weather Impact
            const weatherLabels = trafficData.weather.map(t => t.weather_condition);
            const weatherVals = trafficData.weather.map(t => t.avg_congestion);
            renderBarChart("trafficWeatherChart", weatherLabels, weatherVals, "Avg Congestion Index", "#3b82f6");

        } catch (err) {
            console.error("Error loading charts:", err);
        }
    }

    // 4. Chart Rendering Helpers (using Chart.js global options)
    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: "#9ca3af", font: { family: "Inter", size: 11 } }
            }
        },
        scales: {
            x: {
                grid: { color: "rgba(255, 255, 255, 0.05)" },
                ticks: { color: "#9ca3af", font: { family: "Inter", size: 10 } }
            },
            y: {
                grid: { color: "rgba(255, 255, 255, 0.05)" },
                ticks: { color: "#9ca3af", font: { family: "Inter", size: 10 } }
            }
        }
    };

    function destroyChartIfExists(id) {
        if (charts[id]) {
            charts[id].destroy();
        }
    }

    function renderLineChart(id, labels, data, label, color) {
        destroyChartIfExists(id);
        const ctx = document.getElementById(id).getContext("2d");
        charts[id] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: data,
                    borderColor: color,
                    backgroundColor: `${color}1a`,
                    fill: true,
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 2
                }]
            },
            options: chartDefaults
        });
    }

    function renderBarChart(id, labels, data, label, color) {
        destroyChartIfExists(id);
        const ctx = document.getElementById(id).getContext("2d");
        charts[id] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: data,
                    backgroundColor: color,
                    borderRadius: 6
                }]
            },
            options: chartDefaults
        });
    }

    function renderDoughnutChart(id, labels, data, colors) {
        destroyChartIfExists(id);
        const ctx = document.getElementById(id).getContext("2d");
        charts[id] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: "#9ca3af", font: { family: "Inter", size: 11 } }
                    }
                }
            }
        });
    }

    function renderDoubleLineChart(id, labels, data1, label1, data2, label2) {
        destroyChartIfExists(id);
        const ctx = document.getElementById(id).getContext("2d");
        charts[id] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: label1,
                        data: data1,
                        borderColor: "#3b82f6",
                        yAxisID: 'y',
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 0
                    },
                    {
                        label: label2,
                        data: data2,
                        borderColor: "#10b981",
                        yAxisID: 'y1',
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                ...chartDefaults,
                scales: {
                    x: chartDefaults.scales.x,
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#3b82f6" }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: { color: "#10b981" }
                    }
                }
            }
        });
    }

    function renderTrafficCompareChart(id, labels, data1, label1, data2, label2) {
        destroyChartIfExists(id);
        const ctx = document.getElementById(id).getContext("2d");
        charts[id] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: label1,
                        data: data1,
                        backgroundColor: "#f59e0b",
                        yAxisID: 'y',
                        borderRadius: 6
                    },
                    {
                        label: label2,
                        data: data2,
                        backgroundColor: "#3b82f6",
                        yAxisID: 'y1',
                        borderRadius: 6
                    }
                ]
            },
            options: {
                ...chartDefaults,
                scales: {
                    x: chartDefaults.scales.x,
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#f59e0b" }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: { color: "#3b82f6" }
                    }
                }
            }
        });
    }

    function renderUtilityBarChart(id, labels, data1, label1, data2, label2) {
        destroyChartIfExists(id);
        const ctx = document.getElementById(id).getContext("2d");
        charts[id] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: label1,
                        data: data1,
                        backgroundColor: "#8b5cf6",
                        yAxisID: 'y',
                        borderRadius: 6
                    },
                    {
                        label: label2,
                        data: data2,
                        backgroundColor: "#ef4444",
                        yAxisID: 'y1',
                        borderRadius: 6
                    }
                ]
            },
            options: {
                ...chartDefaults,
                scales: {
                    x: chartDefaults.scales.x,
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#8b5cf6" }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: { color: "#ef4444" }
                    }
                }
            }
        });
    }

    function renderDoubleUtilityChart(id, labels, data1, label1, data2, label2) {
        destroyChartIfExists(id);
        const ctx = document.getElementById(id).getContext("2d");
        charts[id] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: label1,
                        data: data1,
                        backgroundColor: "#10b981",
                        yAxisID: 'y',
                        borderRadius: 6
                    },
                    {
                        label: label2,
                        data: data2,
                        type: 'line',
                        borderColor: "#3b82f6",
                        borderWidth: 2,
                        pointRadius: 3,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                ...chartDefaults,
                scales: {
                    x: chartDefaults.scales.x,
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#10b981" }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: { color: "#3b82f6" },
                        min: 1,
                        max: 5
                    }
                }
            }
        });
    }

    // 5. Leaflet Map Setup
    async function initMap() {
        if (map) return; // Prevent double initialization

        // Center mapping around NYC (represented in mock data)
        map = L.map("complaintsMap").setView([22.7196, 75.8577], 13);

        // CartoDB Dark Matter tile layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        // Fetch complaints GeoJSON
        try {
            const res = await fetch("/api/complaints/geojson");
            complaintsData = await res.json();
            updateMapMarkers();

            // Hook filters
            document.getElementById("chk-resolved").addEventListener("change", updateMapMarkers);
            document.getElementById("chk-inprogress").addEventListener("change", updateMapMarkers);
            document.getElementById("chk-open").addEventListener("change", updateMapMarkers);
        } catch (err) {
            console.error("Error loading map geojson:", err);
        }
    }

    function updateMapMarkers() {
        if (!complaintsData) return;

        // Clear previous markers
        mapMarkers.forEach(m => map.removeLayer(m));
        mapMarkers = [];

        // Check active filters
        const showResolved = document.getElementById("chk-resolved").checked;
        const showInProgress = document.getElementById("chk-inprogress").checked;
        const showOpen = document.getElementById("chk-open").checked;

        // Colors per status
        const colorMap = {
            "Resolved": "#10b981", // green
            "In Progress": "#f59e0b", // orange/yellow
            "Open": "#ef4444" // red
        };

        complaintsData.features.forEach(feat => {
            const props = feat.properties;
            const coords = feat.geometry.coordinates;

            if (props.status === "Resolved" && !showResolved) return;
            if (props.status === "In Progress" && !showInProgress) return;
            if (props.status === "Open" && !showOpen) return;

            // Render Marker
            const markerColor = colorMap[props.status] || "#3b82f6";
            
            const marker = L.circleMarker([coords[1], coords[0]], {
                radius: 6,
                fillColor: markerColor,
                color: "#ffffff",
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.8
            }).addTo(map);

            const popupContent = `
                <div style="font-family: 'Inter', sans-serif; color: #1e293b; padding: 4px;">
                    <h4 style="margin: 0 0 6px 0; font-size: 14px; font-weight: 600; color: ${markerColor}">${props.issue_type}</h4>
                    <p style="margin: 2px 0; font-size: 12px;"><b>Citizen:</b> ${props.citizen}</p>
                    <p style="margin: 2px 0; font-size: 12px;"><b>Dept:</b> ${props.department}</p>
                    <p style="margin: 2px 0; font-size: 12px;"><b>Status:</b> <span style="color: ${markerColor}; font-weight:600">${props.status}</span></p>
                    <p style="margin: 2px 0; font-size: 11px; color: #64748b;"><b>Filed:</b> ${props.created_at}</p>
                </div>
            `;
            marker.bindPopup(popupContent);
            mapMarkers.push(marker);
        });
    }

    // 6. Machine Learning Predict Sandbox Handles
    
    // 6.1 Traffic Congestion Predictor
    const btnPredictTraffic = document.getElementById("btn-predict-traffic");
    btnPredictTraffic.addEventListener("click", async () => {
        const intersection = parseInt(document.getElementById("tf-intersection").value);
        const hour = parseInt(document.getElementById("tf-hour").value);
        const day = parseInt(document.getElementById("tf-day").value);
        const vehicles = parseInt(document.getElementById("tf-vehicles").value);
        const weather = document.getElementById("tf-weather").value;

        btnPredictTraffic.disabled = true;
        btnPredictTraffic.innerText = "Analyzing Sensor Grid...";

        try {
            const res = await fetch("/api/predict/traffic", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    intersection_id: intersection,
                    hour: hour,
                    day_of_week: day,
                    vehicle_count: vehicles,
                    weather_condition: weather
                })
            });

            const data = await res.json();
            const valEl = document.getElementById("val-pred-traffic");
            const descEl = document.getElementById("desc-pred-traffic");
            const predVal = data.predicted_congestion_index;

            valEl.innerText = `${predVal} / 10`;

            // Give context matching scale
            if (predVal > 7.0) {
                valEl.style.color = "var(--accent-red)";
                descEl.innerText = "Critical gridlock. Automatic rerouting triggered.";
            } else if (predVal > 4.5) {
                valEl.style.color = "var(--accent-amber)";
                descEl.innerText = "Moderate congestion. Standard peak patterns.";
            } else {
                valEl.style.color = "var(--accent-green)";
                descEl.innerText = "Optimal traffic flow. No action required.";
            }
        } catch (err) {
            console.error("Traffic prediction error:", err);
            document.getElementById("val-pred-traffic").innerText = "Err";
        } finally {
            btnPredictTraffic.disabled = false;
            btnPredictTraffic.innerText = "Compute Traffic Index";
        }
    });

    // 6.2 Water Demand Forecast
    const btnPredictWater = document.getElementById("btn-predict-water");
    btnPredictWater.addEventListener("click", async () => {
        const district = document.getElementById("wt-district").value;
        const date = document.getElementById("wt-date").value;
        const lag1 = parseFloat(document.getElementById("wt-lag1").value);
        const lag2 = parseFloat(document.getElementById("wt-lag2").value);
        const lag7 = parseFloat(document.getElementById("wt-lag7").value);

        btnPredictWater.disabled = true;
        btnPredictWater.innerText = "Running Forecasting Model...";

        try {
            const res = await fetch("/api/predict/water", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    district_id: district,
                    target_date: date,
                    historical_consumption: [lag1, lag2, lag7]
                })
            });

            const data = await res.json();
            const valEl = document.getElementById("val-pred-water");
            const descEl = document.getElementById("desc-pred-water");
            const predVal = data.predicted_consumption_m3;

            valEl.innerText = `${predVal.toLocaleString()} m³`;
            valEl.style.color = "var(--accent-blue)";
            descEl.innerText = `Forecasted supply capacity needed for ${district}.`;
        } catch (err) {
            console.error("Water forecast error:", err);
            document.getElementById("val-pred-water").innerText = "Err";
        } finally {
            btnPredictWater.disabled = false;
            btnPredictWater.innerText = "Forecast Water Usage";
        }
    });

    // 6.3 Complaint Daily Volume Predictor
    const btnPredictComplaints = document.getElementById("btn-predict-complaints");
    btnPredictComplaints.addEventListener("click", async () => {
        const dept = parseInt(document.getElementById("cp-dept").value);
        const date = document.getElementById("cp-date").value;
        const lag1 = parseInt(document.getElementById("cp-lag1").value);
        const lag2 = parseInt(document.getElementById("cp-lag2").value);
        const lag7 = parseInt(document.getElementById("cp-lag7").value);

        btnPredictComplaints.disabled = true;
        btnPredictComplaints.innerText = "Estimating Call Center Vol...";

        try {
            const res = await fetch("/api/predict/complaints", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    department_id: dept,
                    target_date: date,
                    historical_volume: [lag1, lag2, lag7]
                })
            });

            const data = await res.json();
            const valEl = document.getElementById("val-pred-complaints");
            const descEl = document.getElementById("desc-pred-complaints");
            const predVal = data.predicted_volume;

            valEl.innerText = `${predVal} Complaints`;
            valEl.style.color = "var(--accent-purple)";
            
            let extra = "";
            if (data.suggested_resource_level) {
                extra = ` | Suggested resource level: ${data.suggested_resource_level} sanitation trucks.`;
            }
            descEl.innerText = `Expected call center inbound ticket volume.${extra}`;
        } catch (err) {
            console.error("Complaint forecast error:", err);
            document.getElementById("val-pred-complaints").innerText = "Err";
        } finally {
            btnPredictComplaints.disabled = false;
            btnPredictComplaints.innerText = "Predict Daily Volume";
        }
    });

    // 7. ETL Pipeline Refresh Trigger
    const btnSync = document.getElementById("btn-sync");
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toast-message");

    btnSync.addEventListener("click", async () => {
        btnSync.disabled = true;
        
        // Show Toast
        toast.style.display = "block";
        toastMsg.innerText = "Syncing local datasets, recreating tables, and running ETL pipeline...";

        try {
            const res = await fetch("/api/etl/refresh", { method: "POST" });
            const data = await res.json();

            if (data.status === "Accepted") {
                toastMsg.innerText = "ETL success. Retraining ML models in background...";
                
                // Wait for background execution to complete (simulate progress for UX)
                setTimeout(async () => {
                    toastMsg.innerHTML = `<i class="fa-solid fa-circle-check" style="color:var(--accent-green)"></i> Sync and ML retraining finished!`;
                    btnSync.disabled = false;
                    
                    // Reload everything
                    await loadKPIs();
                    await loadDashboardCharts();
                    if (map) {
                        map.remove();
                        map = null;
                        initMap();
                    }
                    
                    // Hide toast after a couple of seconds
                    setTimeout(() => {
                        toast.style.display = "none";
                    }, 3000);
                }, 4000);
            }
        } catch (err) {
            console.error("ETL sync trigger error:", err);
            toastMsg.innerText = "Data Pipeline Sync Failed!";
            btnSync.disabled = false;
            setTimeout(() => {
                toast.style.display = "none";
            }, 3000);
        }
    });

    // 8. Initial App Load
    loadKPIs();
    loadDashboardCharts();
});
