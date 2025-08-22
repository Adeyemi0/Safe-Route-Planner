from flask import Flask, request, jsonify, render_template_string
import networkx as nx
import folium
from geopy.distance import geodesic
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderQuotaExceeded
import pandas as pd
import osmnx as ox
import time
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# HTML Template (updated with LinkedIn link and removed slider)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Safe Route Planner - Leeds & Birmingham</title>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .input-panel {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }
        
        .form-group input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s, box-shadow 0.3s;
        }
        
        .form-group input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .calculate-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.3s;
            width: 100%;
            margin-bottom: 20px;
        }
        
        .calculate-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }
        
        .calculate-btn:active {
            transform: translateY(0);
        }
        
        .connect-section {
            text-align: center;
            padding: 20px 0;
            border-top: 1px solid #e1e5e9;
            margin-top: 10px;
        }
        
        .connect-text {
            color: #666;
            margin-bottom: 10px;
            font-size: 14px;
        }
        
        .linkedin-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #0077b5;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            transition: background-color 0.3s, transform 0.2s;
        }
        
        .linkedin-btn:hover {
            background: #005885;
            transform: translateY(-1px);
            text-decoration: none;
            color: white;
        }
        
        .linkedin-icon {
            width: 18px;
            height: 18px;
        }
        
        .results-panel {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        
        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        
        .stat-card h3 {
            color: #555;
            font-size: 0.9rem;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-card .value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #333;
        }
        
        .stat-card .subtext {
            font-size: 0.9rem;
            color: #777;
            margin-top: 5px;
        }
        
        .map-container {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            height: 500px;
        }
        
        .error-message {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #c33;
            margin: 20px 0;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }
        
        .loading-spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .input-panel, .results-panel {
                padding: 20px;
            }
            
            .map-container {
                height: 400px;
            }
        }
        
        @media (max-width: 480px) {
            .header h1 {
                font-size: 1.5rem;
            }
            
            .results-grid {
                grid-template-columns: 1fr;
            }
            
            .map-container {
                height: 300px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛣️ Safe Route Planner</h1>
            <p>Find the safest routes in Leeds & Birmingham</p>
        </div>
        
        <div class="input-panel">
            <div class="form-group">
                <label for="startAddress">📍 Start Address</label>
                <input type="text" id="startAddress" placeholder="Enter starting location (Leeds or Birmingham)">
            </div>
            
            <div class="form-group">
                <label for="endAddress">🎯 Destination Address</label>
                <input type="text" id="endAddress" placeholder="Enter destination (same city as start)">
            </div>
            
            <button class="calculate-btn" onclick="calculateRoute()">
                Calculate Safe Route
            </button>
            
            <div class="connect-section">
                <p class="connect-text">Want to connect with me or learn more about this project?</p>
                <a href="https://www.linkedin.com/in/adediran-adeyemi-17103b114/" target="_blank" class="linkedin-btn">
                    <svg class="linkedin-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                    </svg>
                    Connect on LinkedIn
                </a>
            </div>
        </div>
        
        <div id="loading" class="loading" style="display: none;">
            <div class="loading-spinner"></div>
            <p>Calculating optimal routes...</p>
        </div>
        
        <div id="results" class="results-panel" style="display: none;">
            <h2>📊 Route Analysis</h2>
            <div class="results-grid">
                <div class="stat-card">
                    <h3>Fastest Route</h3>
                    <div class="value" id="fastestTime">--</div>
                    <div class="subtext">minutes</div>
                </div>
                <div class="stat-card">
                    <h3>Safest Route</h3>
                    <div class="value" id="safestTime">--</div>
                    <div class="subtext" id="timeDiff">-- minutes longer</div>
                </div>
                <div class="stat-card">
                    <h3>Safety Improvement</h3>
                    <div class="value" id="riskReduction">--</div>
                    <div class="subtext">risk reduction</div>
                </div>
            </div>
            
            <div class="map-container">
                <div id="map" style="height: 100%; width: 100%;"></div>
            </div>
        </div>
        
        <div id="error" class="error-message" style="display: none;"></div>
    </div>

    <script>
        function calculateRoute() {
            const start = document.getElementById('startAddress').value;
            const end = document.getElementById('endAddress').value;
            
            if (!start || !end) {
                showError('Please enter both start and end addresses');
                return;
            }
            
            // Show loading
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            
            axios.post('/get_route', {
                start: start,
                end: end,
                risk_weight: 0.5  // Default balanced approach
            })
            .then(response => {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').style.display = 'none';
                const result = response.data.result;
                
                document.getElementById('fastestTime').textContent = (result.fastest_time / 60).toFixed(1);
                document.getElementById('safestTime').textContent = (result.safest_time / 60).toFixed(1);
                document.getElementById('timeDiff').textContent = 
                    (result.time_difference / 60).toFixed(1) + ' minutes longer';
                document.getElementById('riskReduction').textContent = 
                    (result.risk_reduction * 100).toFixed(1) + '%';
                
                document.getElementById('results').style.display = 'block';
                document.getElementById('map').innerHTML = response.data.map_html;
            })
            .catch(error => {
                document.getElementById('loading').style.display = 'none';
                const errorMsg = error.response?.data?.error || 'An error occurred while calculating the route';
                showError(errorMsg);
            });
        }
        
        function showError(message) {
            document.getElementById('error').textContent = message;
            document.getElementById('error').style.display = 'block';
            document.getElementById('results').style.display = 'none';
        }
        
        // Handle Enter key in input fields
        document.getElementById('startAddress').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') calculateRoute();
        });
        
        document.getElementById('endAddress').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') calculateRoute();
        });
    </script>
</body>
</html>
"""

# Get API key from environment variable
api_key = os.getenv('GOOGLE_MAPS_API_KEY')

if not api_key:
    raise ValueError("GOOGLE_MAPS_API_KEY environment variable is not set!")

# Initialize Google Geocoder
geolocator = GoogleV3(api_key=api_key, timeout=10)

# Load precomputed data at startup
def load_cached_data():
    data = {}
    
    # Load risk grids
    data['risk_grid'] = pd.read_pickle('data/risk_grid.pkl')
    
    # Load networks
    data['leeds_network'] = ox.load_graphml('data/leeds_network.graphml')
    data['birmingham_network'] = ox.load_graphml('data/birmingham_network.graphml')
    
    # Load edges with risk scores
    data['leeds_edges'] = pd.read_pickle('data/leeds_edges.pkl')
    data['birmingham_edges'] = pd.read_pickle('data/birmingham_edges.pkl')
    
    return data

cached_data = load_cached_data()

def get_lat_lng(address):
    """
    Get latitude and longitude from address using Google Geocoding API
    """
    try:
        # Add some context to help with geocoding accuracy
        if not any(city in address.lower() for city in ['leeds', 'birmingham']):
            # If no city is specified, we'll try both and see which gives better results
            leeds_address = f"{address}, Leeds, UK"
            birmingham_address = f"{address}, Birmingham, UK"
            
            # Try Leeds first
            try:
                leeds_location = geolocator.geocode(leeds_address)
                if leeds_location:
                    lat, lng = leeds_location.latitude, leeds_location.longitude
                    in_area, city = is_in_supported_area(lat, lng)
                    if in_area and city == 'leeds':
                        return lat, lng
            except:
                pass
            
            # Try Birmingham
            try:
                birmingham_location = geolocator.geocode(birmingham_address)
                if birmingham_location:
                    lat, lng = birmingham_location.latitude, birmingham_location.longitude
                    in_area, city = is_in_supported_area(lat, lng)
                    if in_area and city == 'birmingham':
                        return lat, lng
            except:
                pass
        else:
            # Direct geocoding if city is already specified
            location = geolocator.geocode(f"{address}, UK")
            if location:
                return location.latitude, location.longitude
        
        return None, None
        
    except (GeocoderTimedOut, GeocoderQuotaExceeded) as e:
        print(f"Geocoding error for address '{address}': {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected geocoding error for address '{address}': {e}")
        return None, None

def is_in_supported_area(lat, lng):
    # Define bounding boxes for Leeds and Birmingham
    leeds_bbox = (53.6989675, -1.8004214, 53.9458715, -1.2903516)  # min_lat, min_lon, max_lat, max_lon
    birmingham_bbox = (52.381053, -2.0336486, 52.6087058, -1.7288417)
    
    in_leeds = (leeds_bbox[0] <= lat <= leeds_bbox[2] and 
                leeds_bbox[1] <= lng <= leeds_bbox[3])
    in_birmingham = (birmingham_bbox[0] <= lat <= birmingham_bbox[2] and 
                     birmingham_bbox[1] <= lng <= birmingham_bbox[3])
    
    return in_leeds or in_birmingham, 'leeds' if in_leeds else 'birmingham'

def calculate_route_improved(network, origin, destination, risk_weight=0.5):
    """
    Improved route calculation with better weight function and type safety
    """
    # Find nearest nodes
    orig_node = ox.distance.nearest_nodes(network, origin[1], origin[0])
    dest_node = ox.distance.nearest_nodes(network, destination[1], destination[0])
    
    print(f"Origin node: {orig_node}, Destination node: {dest_node}")
    print(f"Risk weight: {risk_weight}")
    
    def safe_numeric_conversion(value, default=0):
        """Safely convert value to float, handling strings and other types"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        if isinstance(value, list) and value:
            try:
                return float(value[0])
            except (ValueError, TypeError):
                return default
        return default
    
    # Calculate fastest route (baseline) - using length only
    try:
        fastest_route = nx.shortest_path(network, orig_node, dest_node, weight='length')
        
        # Calculate actual travel time for fastest route
        fastest_time = 0
        fastest_total_risk = 0
        
        for i in range(len(fastest_route) - 1):
            u, v = fastest_route[i], fastest_route[i + 1]
            edge_data = network.get_edge_data(u, v)
            
            if edge_data:
                # Get the first edge (there might be multiple edges between nodes)
                edge = list(edge_data.values())[0]
                
                # Get base travel time if available, otherwise calculate from length
                if 'base_travel_time' in edge:
                    base_time = safe_numeric_conversion(edge['base_travel_time'])
                    fastest_time += base_time
                else:
                    length = safe_numeric_conversion(edge.get('length', 0))
                    # Assume 50 km/h average speed if no speed limit
                    speed_ms = 50 * 1000 / 3600  # 50 km/h in m/s
                    fastest_time += length / speed_ms if speed_ms > 0 else 0
                
                # Get risk score
                risk = safe_numeric_conversion(edge.get('normalized_risk', 0))
                fastest_total_risk += risk
                
        print(f"Fastest route: {len(fastest_route)} nodes, {fastest_time:.1f}s, risk: {fastest_total_risk:.2f}")
        
    except Exception as e:
        print(f"Error calculating fastest route: {e}")
        raise ValueError(f"Cannot find route between the specified locations: {e}")
    
    # Create custom weight function that balances time and risk
    def risk_aware_weight(u, v, d):
        """
        Custom weight function combining time and risk
        """
        # Get base travel time
        if 'base_travel_time' in d:
            base_time = safe_numeric_conversion(d['base_travel_time'])
        else:
            # Calculate from length and speed
            length = safe_numeric_conversion(d.get('length', 0))
            max_speed = d.get('maxspeed', 50)
            
            # Handle speed properly
            max_speed = safe_numeric_conversion(max_speed, 50)
            
            # Convert speed to m/s
            speed_ms = max_speed * 1000 / 3600
            base_time = length / speed_ms if speed_ms > 0 else length / 13.89  # fallback to 50km/h
        
        # Get risk score
        risk_score = safe_numeric_conversion(d.get('normalized_risk', 0))
        
        # Risk penalty: higher risk_weight means more penalty for risky edges
        # Scale risk penalty: risk_score ranges 0-5, so we scale it
        risk_penalty = 1 + (risk_weight * risk_score * 0.5)  # 0-150% penalty based on risk
        
        total_weight = base_time * risk_penalty
        
        return total_weight
    
    # Calculate safest route using risk-aware weights
    try:
        safest_route = nx.shortest_path(network, orig_node, dest_node, weight=risk_aware_weight)
        
        # Calculate actual travel time and risk for safest route
        safest_time = 0
        safest_total_risk = 0
        
        for i in range(len(safest_route) - 1):
            u, v = safest_route[i], safest_route[i + 1]
            edge_data = network.get_edge_data(u, v)
            
            if edge_data:
                edge = list(edge_data.values())[0]
                
                # Get base travel time
                if 'base_travel_time' in edge:
                    base_time = safe_numeric_conversion(edge['base_travel_time'])
                    safest_time += base_time
                else:
                    length = safe_numeric_conversion(edge.get('length', 0))
                    speed_ms = 50 * 1000 / 3600  # 50 km/h in m/s
                    safest_time += length / speed_ms if speed_ms > 0 else 0
                
                # Get risk score
                risk = safe_numeric_conversion(edge.get('normalized_risk', 0))
                safest_total_risk += risk
                
        print(f"Safest route: {len(safest_route)} nodes, {safest_time:.1f}s, risk: {safest_total_risk:.2f}")
        
    except Exception as e:
        print(f"Error calculating safest route: {e}")
        # Fallback to fastest route if safest fails
        safest_route = fastest_route
        safest_time = fastest_time
        safest_total_risk = fastest_total_risk
    
    # Calculate risk reduction
    risk_reduction = 0
    if fastest_total_risk > 0:
        risk_reduction = max(0, (fastest_total_risk - safest_total_risk) / fastest_total_risk)
    
    # Calculate high-risk points for visualization
    def get_high_risk_points(route, threshold=2.0):
        risk_points = []
        for i in range(len(route) - 1):
            u, v = route[i], route[i + 1]
            edge_data = network.get_edge_data(u, v)
            
            if edge_data:
                edge = list(edge_data.values())[0]
                risk_val = safe_numeric_conversion(edge.get('normalized_risk', 0))
                
                if risk_val > threshold:
                    node_data = network.nodes[u]
                    risk_points.append({
                        'lat': node_data['y'],
                        'lng': node_data['x'],
                        'risk': risk_val
                    })
        return risk_points
    
    fastest_risk_points = get_high_risk_points(fastest_route)
    safest_risk_points = get_high_risk_points(safest_route)
    
    print(f"Risk reduction: {risk_reduction*100:.1f}%")
    print(f"Time difference: {(safest_time - fastest_time)/60:.1f} minutes")
    
    return {
        'fastest_route': fastest_route,
        'safest_route': safest_route,
        'fastest_time': fastest_time,
        'safest_time': safest_time,
        'fastest_risk': fastest_total_risk,
        'safest_risk': safest_total_risk,
        'fastest_risk_points': fastest_risk_points,
        'safest_risk_points': safest_risk_points,
        'time_difference': safest_time - fastest_time,
        'risk_reduction': risk_reduction
    }

def generate_route_map(network, result, start_lat, start_lng, end_lat, end_lng):
    # Create base map centered between start and end
    center_lat = (start_lat + end_lat) / 2
    center_lng = (start_lng + end_lng) / 2
    
    m = folium.Map(location=[center_lat, center_lng], zoom_start=12)
    
    # Add fastest route in red
    fastest_coords = [(network.nodes[node]['y'], network.nodes[node]['x']) for node in result['fastest_route']]
    folium.PolyLine(
        fastest_coords, 
        color='red', 
        weight=4, 
        opacity=0.8, 
        popup=f"Fastest Route: {result['fastest_time']/60:.1f} min, Risk: {result['fastest_risk']:.1f}"
    ).add_to(m)
    
    # Add safest route in green
    safest_coords = [(network.nodes[node]['y'], network.nodes[node]['x']) for node in result['safest_route']]
    folium.PolyLine(
        safest_coords, 
        color='green', 
        weight=4, 
        opacity=0.8, 
        popup=f"Safest Route: {result['safest_time']/60:.1f} min, Risk: {result['safest_risk']:.1f}"
    ).add_to(m)
    
    # Add high-risk points for fastest route
    for point in result['fastest_risk_points']:
        folium.CircleMarker(
            [point['lat'], point['lng']], 
            radius=6, 
            color='darkred',
            fill=True, 
            fillColor='red',
            fillOpacity=0.7,
            popup=f"High Risk Area (Fastest): {point['risk']:.2f}"
        ).add_to(m)
    
    # Add high-risk points for safest route  
    for point in result['safest_risk_points']:
        folium.CircleMarker(
            [point['lat'], point['lng']], 
            radius=6, 
            color='darkgreen',
            fill=True, 
            fillColor='orange',
            fillOpacity=0.7,
            popup=f"High Risk Area (Safest): {point['risk']:.2f}"
        ).add_to(m)
    
    # Add start marker
    folium.Marker(
        [start_lat, start_lng], 
        popup='Start Location', 
        icon=folium.Icon(color='blue', icon='play')
    ).add_to(m)
    
    # Add end marker
    folium.Marker(
        [end_lat, end_lng], 
        popup='Destination', 
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <b>Route Legend</b><br>
    <i class="fa fa-minus" style="color:red"></i> Fastest Route<br>
    <i class="fa fa-minus" style="color:green"></i> Safest Route<br>
    <i class="fa fa-circle" style="color:red"></i> High Risk (Fastest)<br>
    <i class="fa fa-circle" style="color:orange"></i> High Risk (Safest)
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m._repr_html_()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_route', methods=['POST'])
def get_route():
    try:
        data = request.json
        start_address = data.get('start', '').strip()
        end_address = data.get('end', '').strip()
        risk_weight = data.get('risk_weight', 0.5)  # Default to balanced approach
        
        if not start_lat or not start_lng:
            return jsonify({'error': f'Could not find location for start address: {start_address}'}), 400
        
        # Small delay to respect API limits
        time.sleep(0.1)
        
        print(f"Geocoding end address: {end_address}")
        end_lat, end_lng = get_lat_lng(end_address)
        
        if not end_lat or not end_lng:
            return jsonify({'error': f'Could not find location for end address: {end_address}'}), 400
        
        # Check if in supported area
        start_in_area, start_city = is_in_supported_area(start_lat, start_lng)
        end_in_area, end_city = is_in_supported_area(end_lat, end_lng)
        
        if not start_in_area:
            return jsonify({'error': f'Start address is not in Leeds or Birmingham (found coordinates: {start_lat:.4f}, {start_lng:.4f})'}), 400
        
        if not end_in_area:
            return jsonify({'error': f'End address is not in Leeds or Birmingham (found coordinates: {end_lat:.4f}, {end_lng:.4f})'}), 400
        
        if start_city != end_city:
            return jsonify({'error': f'Both addresses must be in the same city. Start is in {start_city.title()}, end is in {end_city.title()}'}), 400
        
        print(f"Calculating route in {start_city.title()} from ({start_lat:.4f}, {start_lng:.4f}) to ({end_lat:.4f}, {end_lng:.4f})")
        
        # Get appropriate network
        if start_city == 'leeds':
            network = cached_data['leeds_network']
        else:
            network = cached_data['birmingham_network']
        
        # Calculate routes using improved method
        result = calculate_route_improved(network, (start_lat, start_lng), (end_lat, end_lng), risk_weight)
        
        # Generate map
        map_html = generate_route_map(network, result, start_lat, start_lng, end_lat, end_lng)
        
        return jsonify({
            'result': result,
            'map_html': map_html,
            'city': start_city.title()
        })
        
    except Exception as e:
        print(f"Error in get_route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)_address or not end_address:
            return jsonify({'error': 'Please provide both start and end addresses'}), 400
        
        # Geocode addresses with rate limiting
        print(f"Geocoding start address: {start_address}")
        start_lat, start_lng = get_lat_lng(start_address)
        
        if not start
