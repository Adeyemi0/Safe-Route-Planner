import streamlit as st
import networkx as nx
import folium
from streamlit_folium import folium_static
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

# Page configuration
st.set_page_config(
    page_title="Safe Route Planner - Leeds & Birmingham",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 15px 15px;
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.9;
        margin: 0;
    }
    
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .linkedin-btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #0077b5;
        color: white !important;
        padding: 10px 20px;
        border-radius: 5px;
        text-decoration: none;
        font-weight: 500;
        font-size: 14px;
        transition: background-color 0.3s, transform 0.2s;
        margin-top: 1rem;
    }
    
    .linkedin-btn:hover {
        background: #005885;
        transform: translateY(-1px);
        text-decoration: none;
        color: white !important;
    }
    
    .error-message {
        background: #fee;
        color: #c33;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #c33;
        margin: 20px 0;
    }
    
    .success-message {
        background: #efe;
        color: #363;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #363;
        margin: 20px 0;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 8px;
        font-weight: 600;
        transition: transform 0.2s, box-shadow 0.3s;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🛣️ Safe Route Planner</h1>
    <p>Find the safest routes in Leeds & Birmingham</p>
</div>
""", unsafe_allow_html=True)

# Initialize Google Geocoder
@st.cache_resource
def initialize_geocoder():
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    if not api_key:
        st.error("GOOGLE_MAPS_API_KEY not found in environment variables!")
        st.stop()
    
    return GoogleV3(api_key=api_key, timeout=10)

geolocator = initialize_geocoder()

# Load precomputed data at startup
@st.cache_data
def load_cached_data():
    try:
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
    except Exception as e:
        st.error(f"Error loading cached data: {e}")
        st.info("Please ensure all data files are present in the 'data' directory.")
        st.stop()

# Load data with loading indicator
with st.spinner("Loading network data..."):
    cached_data = load_cached_data()

def get_lat_lng(address):
    """Get latitude and longitude from address using Google Geocoding API"""
    try:
        if not any(city in address.lower() for city in ['leeds', 'birmingham']):
            # Try both cities
            leeds_address = f"{address}, Leeds, UK"
            birmingham_address = f"{address}, Birmingham, UK"
            
            try:
                leeds_location = geolocator.geocode(leeds_address)
                if leeds_location:
                    lat, lng = leeds_location.latitude, leeds_location.longitude
                    in_area, city = is_in_supported_area(lat, lng)
                    if in_area and city == 'leeds':
                        return lat, lng
            except:
                pass
            
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
            location = geolocator.geocode(f"{address}, UK")
            if location:
                return location.latitude, location.longitude
        
        return None, None
        
    except (GeocoderTimedOut, GeocoderQuotaExceeded) as e:
        st.error(f"Geocoding error for address '{address}': {e}")
        return None, None
    except Exception as e:
        st.error(f"Unexpected geocoding error for address '{address}': {e}")
        return None, None

def is_in_supported_area(lat, lng):
    """Check if coordinates are in supported areas"""
    leeds_bbox = (53.6989675, -1.8004214, 53.9458715, -1.2903516)
    birmingham_bbox = (52.381053, -2.0336486, 52.6087058, -1.7288417)
    
    in_leeds = (leeds_bbox[0] <= lat <= leeds_bbox[2] and 
                leeds_bbox[1] <= lng <= leeds_bbox[3])
    in_birmingham = (birmingham_bbox[0] <= lat <= birmingham_bbox[2] and 
                     birmingham_bbox[1] <= lng <= birmingham_bbox[3])
    
    return in_leeds or in_birmingham, 'leeds' if in_leeds else 'birmingham'

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

def calculate_route_improved(network, origin, destination, risk_weight=0.5):
    """Improved route calculation with network connectivity handling"""
    
    # Find nearest nodes
    orig_node = ox.distance.nearest_nodes(network, origin[1], origin[0])
    dest_node = ox.distance.nearest_nodes(network, destination[1], destination[0])
    
    # Check if nodes are in the same connected component
    if not nx.has_path(network, orig_node, dest_node):
        # Find the largest connected component
        largest_cc = max(nx.connected_components(network.to_undirected()), key=len)
        
        # Find nearest nodes that are in the largest connected component
        cc_nodes = list(largest_cc)
        cc_coords = [(network.nodes[node]['y'], network.nodes[node]['x']) for node in cc_nodes]
        
        # Find closest nodes in connected component
        distances = [geodesic((origin[0], origin[1]), coord).meters for coord in cc_coords]
        min_idx = np.argmin(distances)
        orig_node = cc_nodes[min_idx]
        
        distances = [geodesic((destination[0], destination[1]), coord).meters for coord in cc_coords]
        min_idx = np.argmin(distances)
        dest_node = cc_nodes[min_idx]
    
    # Verify we now have a valid path
    if not nx.has_path(network, orig_node, dest_node):
        raise ValueError("Cannot find any connected path between the locations.")
    
    # Calculate fastest route (baseline)
    fastest_route = nx.shortest_path(network, orig_node, dest_node, weight='length')
    
    # Calculate actual travel time for fastest route
    fastest_time = 0
    fastest_total_risk = 0
    
    for i in range(len(fastest_route) - 1):
        u, v = fastest_route[i], fastest_route[i + 1]
        edge_data = network.get_edge_data(u, v)
        
        if edge_data:
            edge = list(edge_data.values())[0]
            
            if 'base_travel_time' in edge:
                base_time = safe_numeric_conversion(edge['base_travel_time'])
                fastest_time += base_time
            else:
                length = safe_numeric_conversion(edge.get('length', 0))
                speed_ms = 50 * 1000 / 3600  # 50 km/h in m/s
                fastest_time += length / speed_ms if speed_ms > 0 else 0
            
            risk = safe_numeric_conversion(edge.get('normalized_risk', 0))
            fastest_total_risk += risk
    
    # Create custom weight function that balances time and risk
    def risk_aware_weight(u, v, d):
        if 'base_travel_time' in d:
            base_time = safe_numeric_conversion(d['base_travel_time'])
        else:
            length = safe_numeric_conversion(d.get('length', 0))
            max_speed = d.get('maxspeed', 50)
            max_speed = safe_numeric_conversion(max_speed, 50)
            speed_ms = max_speed * 1000 / 3600
            base_time = length / speed_ms if speed_ms > 0 else length / 13.89
        
        risk_score = safe_numeric_conversion(d.get('normalized_risk', 0))
        risk_penalty = 1 + (risk_weight * risk_score * 0.5)
        total_weight = base_time * risk_penalty
        
        return total_weight
    
    # Calculate safest route using risk-aware weights
    try:
        safest_route = nx.shortest_path(network, orig_node, dest_node, weight=risk_aware_weight)
    except Exception:
        safest_route = fastest_route
    
    # Calculate actual travel time and risk for safest route
    safest_time = 0
    safest_total_risk = 0
    
    for i in range(len(safest_route) - 1):
        u, v = safest_route[i], safest_route[i + 1]
        edge_data = network.get_edge_data(u, v)
        
        if edge_data:
            edge = list(edge_data.values())[0]
            
            if 'base_travel_time' in edge:
                base_time = safe_numeric_conversion(edge['base_travel_time'])
                safest_time += base_time
            else:
                length = safe_numeric_conversion(edge.get('length', 0))
                speed_ms = 50 * 1000 / 3600
                safest_time += length / speed_ms if speed_ms > 0 else 0
            
            risk = safe_numeric_conversion(edge.get('normalized_risk', 0))
            safest_total_risk += risk
    
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
    """Generate Folium map with routes"""
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
    
    return m

# Sidebar for inputs
st.sidebar.header("Route Planning")

with st.sidebar.form("route_form"):
    start_address = st.text_input(
        "📍 Start Address", 
        placeholder="Enter starting location (Leeds or Birmingham)",
        help="Enter the starting point of your journey"
    )
    
    end_address = st.text_input(
        "🎯 Destination Address", 
        placeholder="Enter destination (same city as start)",
        help="Enter your destination"
    )
    
    risk_weight = st.slider(
        "Risk vs Speed Balance",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.1,
        help="0.0 = Prioritize speed, 1.0 = Prioritize safety"
    )
    
    submit_button = st.form_submit_button("Calculate Safe Route")

# Add LinkedIn link in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### Connect with the Developer")
st.sidebar.markdown("""
<a href="https://www.linkedin.com/in/adediran-adeyemi-17103b114/" target="_blank" class="linkedin-btn">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
    </svg>
    Connect on LinkedIn
</a>
""", unsafe_allow_html=True)

# Main content area
if submit_button:
    if not start_address or not end_address:
        st.error("Please enter both start and end addresses.")
    else:
        with st.spinner("Calculating optimal routes..."):
            try:
                # Geocode addresses
                start_lat, start_lng = get_lat_lng(start_address)
                
                if not start_lat or not start_lng:
                    st.error(f"Could not find location for start address: {start_address}")
                    st.stop()
                
                time.sleep(0.1)  # Rate limiting
                
                end_lat, end_lng = get_lat_lng(end_address)
                
                if not end_lat or not end_lng:
                    st.error(f"Could not find location for end address: {end_address}")
                    st.stop()
                
                # Check if in supported area
                start_in_area, start_city = is_in_supported_area(start_lat, start_lng)
                end_in_area, end_city = is_in_supported_area(end_lat, end_lng)
                
                if not start_in_area:
                    st.error(f"Start address is not in Leeds or Birmingham (found coordinates: {start_lat:.4f}, {start_lng:.4f})")
                    st.stop()
                
                if not end_in_area:
                    st.error(f"End address is not in Leeds or Birmingham (found coordinates: {end_lat:.4f}, {end_lng:.4f})")
                    st.stop()
                
                if start_city != end_city:
                    st.error(f"Both addresses must be in the same city. Start is in {start_city.title()}, end is in {end_city.title()}")
                    st.stop()
                
                # Get appropriate network
                if start_city == 'leeds':
                    network = cached_data['leeds_network']
                else:
                    network = cached_data['birmingham_network']
                
                # Calculate routes
                result = calculate_route_improved(network, (start_lat, start_lng), (end_lat, end_lng), risk_weight)
                
                # Display results
                st.success(f"Route calculated successfully for {start_city.title()}!")
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-container">
                        <h3>🚗 Fastest Route</h3>
                        <div style="font-size: 2rem; font-weight: bold; color: #333;">
                            {result['fastest_time']/60:.1f}
                        </div>
                        <div style="color: #666;">minutes</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-container">
                        <h3>🛡️ Safest Route</h3>
                        <div style="font-size: 2rem; font-weight: bold; color: #333;">
                            {result['safest_time']/60:.1f}
                        </div>
                        <div style="color: #666;">{result['time_difference']/60:.1f} minutes longer</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-container">
                        <h3>📊 Safety Improvement</h3>
                        <div style="font-size: 2rem; font-weight: bold; color: #333;">
                            {result['risk_reduction']*100:.1f}%
                        </div>
                        <div style="color: #666;">risk reduction</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Generate and display map
                route_map = generate_route_map(network, result, start_lat, start_lng, end_lat, end_lng)
                
                st.subheader("🗺️ Route Map")
                
                # Add legend
                with st.expander("📖 Map Legend", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Route Lines:**")
                        st.markdown("🔴 **Red Line:** Fastest Route (Speed Optimized)")
                        st.markdown("🟢 **Green Line:** Safest Route (Risk Optimized)")
                    
                    with col2:
                        st.markdown("**Location Markers:**")
                        st.markdown("🔵 **Blue Play Button:** Start Location")
                        st.markdown("🔴 **Red Stop Button:** Destination")
                
                # Display the map
                folium_static(route_map, width=None, height=500)
                
                # Store results in session state for potential future use
                st.session_state['last_result'] = result
                st.session_state['last_city'] = start_city
                
            except Exception as e:
                st.error(f"An error occurred while calculating the route: {str(e)}")
                st.error("Please check your addresses and try again.")

else:
    # Show instructions when no calculation has been performed
    st.info("👆 Enter your start and destination addresses in the sidebar to calculate the safest route.")
    
    st.markdown("""
    ## How it works
    
    This application helps you find safer routes in Leeds and Birmingham by:
    
    1. **Analyzing Crime Data**: Using historical crime statistics to identify high-risk areas
    2. **Route Optimization**: Balancing travel time with safety considerations
    3. **Visual Comparison**: Showing both fastest and safest routes on an interactive map
    
    ### Features:
    - 🗺️ Interactive maps with route visualization
    - 📊 Detailed route metrics and comparison
    - 🛡️ Risk assessment based on real crime data
    - ⚖️ Adjustable balance between speed and safety
    
    ### Supported Areas:
    - **Leeds**: Full city coverage with real-time route planning
    - **Birmingham**: Comprehensive network analysis and safety scoring
    
    *Start by entering your addresses in the sidebar to get personalized route recommendations.*
    """)
