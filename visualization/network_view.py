"""
Interactive Network topology visualization using Plotly and NetworkX.
Provides both the primary network graph and the guaranteed offline fallback for OpenStreetMap.
"""

from typing import Optional, Dict, Any, List
import plotly.graph_objects as go
import networkx as nx
import config
from simulation.network import TrafficNetwork
from emergency.corridor import EmergencyCorridor

def create_network_figure(network: TrafficNetwork, corridor: Optional[EmergencyCorridor] = None) -> go.Figure:
    """
    Renders an interactive Plotly figure displaying:
    - 2x3 Interconnected urban road network topology
    - Real-time signal states (🟢 Green vs 🔴 Red)
    - Dynamic node sizing based on vehicle queue backlog
    - Pedestrian waiting counts
    - Emergency vehicle position (Ambulance 🚑) & Hospital 🏥
    - Emergency Green Corridor highlighted path
    """
    # Grid layout coordinates: Upper row A-B-C, Lower row D-E-F
    pos = {
        'A': (0.0, 1.0), 'B': (1.2, 1.0), 'C': (2.4, 1.0),
        'D': (0.0, 0.0), 'E': (1.2, 0.0), 'F': (2.4, 0.0)
    }

    ambulance_node = corridor.get_current_ambulance_node() if (corridor and corridor.is_active) else None
    corridor_path = corridor.ambulance_path if (corridor and corridor.is_active) else []

    fig = go.Figure()

    # 1. Draw Normal and Closed Edges
    for u, v in network.graph.edges():
        is_closed = network.is_road_closed(u, v)
        x0, y0 = pos[u]
        x1, y1 = pos[v]

        # Check if part of emergency corridor
        is_corridor = False
        if corridor_path and len(corridor_path) > 1:
            for k in range(len(corridor_path) - 1):
                if (u == corridor_path[k] and v == corridor_path[k+1]) or (v == corridor_path[k] and u == corridor_path[k+1]):
                    is_corridor = True
                    break

        if is_closed:
            line_color = '#6c757d'
            line_width = 3
            line_dash = 'dash'
            hover_info = f"⛔ ROAD CLOSED: {u} ↔ {v}"
        elif is_corridor:
            line_color = '#00f0ff' # High-vis Cyan for Green Corridor
            line_width = 6
            line_dash = 'solid'
            hover_info = f"🚨 EMERGENCY GREEN CORRIDOR: {u} ↔ {v}"
        else:
            line_color = '#adb5bd'
            line_width = 3
            line_dash = 'solid'
            hover_info = f"Road: {u} ↔ {v}"

        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1],
            mode='lines',
            line=dict(width=line_width, color=line_color, dash=line_dash),
            hoverinfo='text',
            text=hover_info,
            showlegend=False
        ))

    # 2. Draw Intersections (Nodes)
    node_x = []
    node_y = []
    node_colors = []
    node_sizes = []
    node_borders = []
    node_border_widths = []
    node_labels = []
    hover_texts = []

    for node in config.INTERSECTION_IDS:
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        state = network.get_state(node)
        meta = config.INTERSECTION_METADATA[node]

        # Node size based on queue length (min 32, max 58)
        size = 32 + int((state.queue_length / config.MAX_QUEUE_CAPACITY) * 26)
        node_sizes.append(size)

        # Base signal color: 1 = Green, 0 = Red
        if state.signal_state == 1:
            fill_color = '#2ecc71' # Green
            signal_text = "🟢 GREEN"
        else:
            fill_color = '#e74c3c' # Red
            signal_text = "🔴 RED"

        border_color = '#2c3e50'
        border_width = 2
        label_prefix = ""

        if ambulance_node == node:
            fill_color = '#3498db' # Bright blue for Ambulance
            border_color = '#f1c40f' # Gold border
            border_width = 4
            label_prefix = "🚑 "
        elif meta.get('is_hospital', False):
            border_color = '#e74c3c'
            border_width = 4
            label_prefix = "🏥 "

        node_colors.append(fill_color)
        node_borders.append(border_color)
        node_border_widths.append(border_width)
        node_labels.append(f"<b>{label_prefix}{node}</b>")

        hover_info = (
            f"<b>Intersection {node} ({meta['name']})</b><br>"
            f"Signal: {signal_text}<br>"
            f"Queue: {state.queue_length} / {state.capacity} vehicles<br>"
            f"Traffic Density: {state.traffic_density}<br>"
            f"Pedestrians Waiting: {state.pedestrian_demand}<br>"
            f"Accident Severity: {int(state.accident_severity * 100)}%<br>"
            f"Emergency Priority: {'ACTIVE 🚨' if state.emergency_priority else 'None'}"
        )
        hover_texts.append(hover_info)

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_labels,
        textposition="top center",
        textfont=dict(size=14, color='#1e293b', family='Arial Black'),
        hoverinfo='text',
        hovertext=hover_texts,
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(color=node_borders, width=node_border_widths)
        ),
        showlegend=False
    ))

    # Layout tuning
    fig.update_layout(
        title=dict(text="Urban Road Network Topology & Signal State Flow", font=dict(size=16)),
        hovermode='closest',
        margin=dict(b=20, l=20, r=20, t=50),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.4, 2.8]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.4, 1.4]),
        plot_bgcolor='#f8fafc',
        height=380
    )

    return fig
