"""
Geographical map visualization using Folium and OpenStreetMap.
"""

from typing import Optional, Dict, Any
import folium
from folium import plugins
import config
from simulation.network import TrafficNetwork
from emergency.corridor import EmergencyCorridor

def create_folium_map(network: TrafficNetwork, corridor: Optional[EmergencyCorridor] = None) -> folium.Map:
    """
    Renders an OpenStreetMap geographical visualization showing:
    - Intersections (color-coded by signal state)
    - Road segments (colored by congestion density)
    - Ambulance location with 🚑 icon
    - Hospital destination with 🏥 icon
    - Active Emergency Green Corridor route highlighted in vibrant cyan/blue
    """
    # Center map on Westminster / Central London
    center_lat = 51.5042
    center_lon = -0.1235

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        tiles="CartoDB positron", # Clean, modern tile style
        control_scale=True
    )

    ambulance_node = corridor.get_current_ambulance_node() if (corridor and corridor.is_active) else None
    corridor_path = corridor.ambulance_path if (corridor and corridor.is_active) else []

    # 1. Render Road Segments (Polylines)
    for u, v in network.graph.edges():
        is_closed = network.is_road_closed(u, v)
        meta_u = config.INTERSECTION_METADATA[u]
        meta_v = config.INTERSECTION_METADATA[v]
        coords = [[meta_u['lat'], meta_u['lon']], [meta_v['lat'], meta_v['lon']]]

        # Determine if this edge is currently part of the active emergency route
        is_corridor_edge = False
        if corridor_path and len(corridor_path) > 1:
            for k in range(len(corridor_path) - 1):
                if (u == corridor_path[k] and v == corridor_path[k+1]) or (v == corridor_path[k] and u == corridor_path[k+1]):
                    is_corridor_edge = True
                    break

        # Edge styling
        if is_closed:
            color = "#444444"
            weight = 3
            dash_array = "5, 10"
            tooltip = f"⛔ ROAD CLOSED: {u} ↔ {v}"
        elif is_corridor_edge:
            color = "#00D2FF" # Vibrant Cyan for Green Corridor
            weight = 7
            dash_array = None
            tooltip = f"🚨 EMERGENCY GREEN CORRIDOR: {u} ↔ {v}"
        else:
            # Color by average congestion of endpoints
            state_u = network.get_state(u)
            state_v = network.get_state(v)
            avg_q = (state_u.queue_length + state_v.queue_length) / 2.0

            if avg_q > 18:
                color = "#E63946" # Red (heavy congestion)
            elif avg_q > 8:
                color = "#F4A261" # Orange (moderate)
            else:
                color = "#2A9D8F" # Green (smooth)
            weight = 4
            dash_array = None
            tooltip = f"Road {u} ↔ {v} (Avg Queue: {avg_q:.1f})"

        folium.PolyLine(
            locations=coords,
            color=color,
            weight=weight,
            dash_array=dash_array,
            opacity=0.85,
            tooltip=tooltip
        ).add_to(m)

    # 2. Render Intersection Markers
    for node_id, state in network.intersections.items():
        meta = config.INTERSECTION_METADATA[node_id]
        loc = [meta['lat'], meta['lon']]

        signal_str = "🟢 GREEN (Priority)" if state.signal_state == 1 else "🔴 RED (Cross)"
        popup_html = f"""
        <div style='font-family: sans-serif; min-width: 170px;'>
            <h4 style='margin: 0 0 5px 0;'>Node {node_id}: {meta['name']}</h4>
            <b>Signal State:</b> {signal_str}<br>
            <b>Queue Length:</b> {state.queue_length} / {state.capacity}<br>
            <b>Traffic Density:</b> {state.traffic_density}<br>
            <b>Pedestrians Waiting:</b> {state.pedestrian_demand}<br>
            <b>Accident Severity:</b> {int(state.accident_severity * 100)}%<br>
            <b>Emergency Priority:</b> {'YES 🚨' if state.emergency_priority else 'NO'}
        </div>
        """

        # Check for special entity on this node:
        if ambulance_node == node_id:
            # 🚑 Ambulance Marker
            folium.Marker(
                location=loc,
                popup=folium.Popup(f"<b>🚑 AMBULANCE IN TRANSIT</b><br>Currently at {meta['name']}", max_width=250),
                tooltip="🚑 Ambulance (Priority Vehicle)",
                icon=folium.Icon(color="blue", icon="plus-sign", prefix="glyphicon")
            ).add_to(m)
        elif meta.get('is_hospital', False):
            # 🏥 Hospital Marker
            folium.Marker(
                location=loc,
                popup=folium.Popup(f"<b>🏥 ST THOMAS HOSPITAL</b><br>Emergency Trauma Destination", max_width=250),
                tooltip="🏥 Trauma Hospital",
                icon=folium.Icon(color="red", icon="heart", prefix="glyphicon")
            ).add_to(m)
        else:
            # Normal Traffic Signal Node
            marker_color = "#2ECC71" if state.signal_state == 1 else "#E74C3C"
            folium.CircleMarker(
                location=loc,
                radius=10,
                color="#2C3E50",
                weight=2,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.9,
                tooltip=f"Node {node_id}: {signal_str} (Queue: {state.queue_length})",
                popup=folium.Popup(popup_html, max_width=280)
            ).add_to(m)

    return m
