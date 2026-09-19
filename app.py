"""
Quantum-Enhanced Adaptive Urban Traffic Optimization
Hybrid Quantum-Classical Traffic Optimization for Social Welfare
Hackathon MVP Interactive Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import time

import config
from simulation.network import TrafficNetwork
from simulation.state import IntersectionState
from simulation.traffic import TrafficSimulator
from simulation.pedestrians import PedestrianManager
from simulation.events import EventManager
from optimization.qubo import TrafficQUBO
from optimization.ising import qubo_to_ising, to_qiskit_pauli_op
from optimization.qaoa_qiskit import QAOAOptimizerQiskit
from optimization.qaoa_pennylane import QAOAOptimizerPennyLane
from optimization.classical import FixedTimeController, RuleBasedAdaptiveController
from quantum.aer_backend import AerBackendManager
from quantum.ibm_backend import IBMQuantumManager
from emergency.corridor import EmergencyCorridor
from visualization.map_view import create_folium_map
from visualization.network_view import create_network_figure
from metrics.evaluation import MetricsEvaluator

try:
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

# --- Streamlit Page Setup ---
st.set_page_config(
    page_title="Quantum Traffic Optimization | Quantexa MVP",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 0.1rem;
    }
    .sub-title {
        font-size: 1.15rem;
        font-weight: 500;
        color: #0284c7;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #f8fafc;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 5px solid #0284c7;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .badge-quantum {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-classical {
        background-color: #fef3c7;
        color: #b45309;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-emergency {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'initialized' not in st.session_state:
    config.set_seed()
    st.session_state.network = TrafficNetwork()
    st.session_state.ped_mgr = PedestrianManager(st.session_state.network)
    st.session_state.simulator = TrafficSimulator(st.session_state.network, st.session_state.ped_mgr)
    st.session_state.events = EventManager(st.session_state.network)
    st.session_state.corridor = EmergencyCorridor(st.session_state.network)

    # Quantum & Classical Solvers
    st.session_state.aer_manager = AerBackendManager()
    st.session_state.ibm_manager = IBMQuantumManager()
    st.session_state.qaoa_qiskit = QAOAOptimizerQiskit(reps=config.QAOA_REPS, shots=config.QAOA_SHOTS)
    st.session_state.qaoa_pennylane = QAOAOptimizerPennyLane(reps=config.QAOA_REPS, shots=config.QAOA_SHOTS)
    st.session_state.fixed_controller = FixedTimeController(st.session_state.network)
    st.session_state.rule_controller = RuleBasedAdaptiveController(st.session_state.network)

    # Metrics Trackers
    st.session_state.metrics_classical = MetricsEvaluator(mode_name="Classical (Fixed-Time)")
    st.session_state.metrics_quantum = MetricsEvaluator(mode_name="Quantum QAOA (Hybrid)")

    # Execution State
    st.session_state.step = 0
    st.session_state.last_mode = "None"
    st.session_state.last_decisions = {node: 0 for node in config.INTERSECTION_IDS}
    st.session_state.last_quantum_telemetry = None
    st.session_state.last_qubo_meta = None
    st.session_state.last_ising_meta = None
    st.session_state.demo_running = False
    st.session_state.demo_logs = []
    st.session_state.initialized = True

# --- Title Header ---
st.markdown('<div class="main-title">Quantum-Enhanced Adaptive Urban Traffic Optimization</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Hybrid Quantum-Classical Traffic Optimization for Social Welfare | Quantexa Hackathon MVP</div>', unsafe_allow_html=True)

# --- Top Status Bar ---
status_col1, status_col2, status_col3, status_col4 = st.columns(4)

with status_col1:
    emg_status = "🚨 ACTIVE IN TRANSIT" if st.session_state.corridor.is_active else ("✅ ARRIVED AT HOSPITAL" if st.session_state.corridor.completed else "IDLE")
    badge_class = "badge-emergency" if st.session_state.corridor.is_active else "badge-classical"
    st.markdown(f"**Emergency Status:** <span class='{badge_class}'>{emg_status}</span>", unsafe_allow_html=True)

with status_col2:
    mode_label = st.session_state.last_mode
    m_badge = "badge-quantum" if "Quantum" in mode_label else "badge-classical"
    st.markdown(f"**Current Mode:** <span class='{m_badge}'>{mode_label}</span>", unsafe_allow_html=True)

with status_col3:
    backend_info = st.session_state.aer_manager.get_backend_info()
    st.markdown(f"**Quantum Backend:** <span class='badge-quantum'>{backend_info['name']}</span>", unsafe_allow_html=True)

with status_col4:
    st.markdown(f"**Simulation Step:** `Step {st.session_state.step}`")

st.markdown("---")

# --- Sidebar Controls ---
st.sidebar.title("🎛️ Platform Controls")

st.sidebar.subheader("1. Quantum Configuration")
quantum_framework = st.sidebar.selectbox(
    "Quantum Framework",
    ["Qiskit Aer Simulator", "PennyLane (default.qubit)", "IBM Quantum Hardware (Optional)"],
    help="Select the quantum execution pipeline. Both use the identical QUBO/Ising formulation."
)

if quantum_framework == "IBM Quantum Hardware (Optional)":
    ibm_stat = st.session_state.ibm_manager.get_status()
    if ibm_stat['is_hardware_available']:
        st.sidebar.success(f"Connected: {ibm_stat['active_backend']}")
    else:
        st.sidebar.info(ibm_stat['status_message'])

st.sidebar.subheader("2. Simulation Stepping")
def execute_optimization_step(mode: str, framework: str):
    """Executes a single end-to-end step under the selected controller."""
    # 1. Simulator arrivals & departures based on existing signal
    step_res = st.session_state.simulator.step()

    # 2. Identify emergency corridor nodes if active
    emg_nodes = st.session_state.corridor.get_corridor_nodes() if st.session_state.corridor.is_active else []

    # 3. Formulate QUBO & Ising
    qubo = TrafficQUBO(st.session_state.network)
    Q, qubo_meta = qubo.build_qubo_matrix(emergency_nodes=emg_nodes)
    h, J, offset = qubo_to_ising(Q, num_variables=config.NUM_INTERSECTIONS)
    st.session_state.last_qubo_meta = (Q, qubo_meta)
    st.session_state.last_ising_meta = (h, J, offset)

    decisions = {}
    q_telemetry = None

    if mode == "Classical (Fixed-Time)":
        decisions = st.session_state.fixed_controller.optimize(emergency_nodes=emg_nodes)
        st.session_state.last_mode = "Classical (Fixed-Time)"
    elif mode == "Classical (Rule-Based Adaptive)":
        decisions = st.session_state.rule_controller.optimize(emergency_nodes=emg_nodes)
        st.session_state.last_mode = "Classical (Rule-Based Adaptive)"
    else:
        # Quantum optimization
        if "PennyLane" in framework:
            q_telemetry = st.session_state.qaoa_pennylane.optimize(h, J, offset, num_qubits=config.NUM_INTERSECTIONS)
            st.session_state.last_mode = "Quantum (PennyLane QAOA)"
        else:
            q_telemetry = st.session_state.qaoa_qiskit.optimize(h, J, offset, num_qubits=config.NUM_INTERSECTIONS)
            st.session_state.last_mode = "Quantum (Qiskit QAOA)"

        bitstring = q_telemetry['best_bitstring']
        decisions = qubo.decode_solution(bitstring)
        q_telemetry['qubo_cost'] = round(qubo.evaluate_cost(Q, bitstring), 3)
        st.session_state.last_quantum_telemetry = q_telemetry

    # 4. Apply emergency override if corridor is active
    if st.session_state.corridor.is_active:
        decisions = st.session_state.corridor.apply_emergency_override(decisions)
        st.session_state.corridor.step()

    # 5. Apply decisions to network signals
    for node, bit in decisions.items():
        st.session_state.network.set_signal(node, bit)
    st.session_state.last_decisions = decisions

    # 6. Record step in appropriate metrics evaluator
    total_q = st.session_state.simulator.get_total_queue_length()
    avg_wait = st.session_state.simulator.get_average_wait_time()
    thru = step_res['step_throughput']
    ped_demand = st.session_state.ped_mgr.get_total_pedestrian_demand()
    emg_step = st.session_state.corridor.travel_time_steps

    if "Classical" in st.session_state.last_mode:
        st.session_state.metrics_classical.record_step(
            st.session_state.step, total_q, avg_wait, thru, ped_demand, decisions, emg_step
        )
    else:
        st.session_state.metrics_quantum.record_step(
            st.session_state.step, total_q, avg_wait, thru, ped_demand, decisions, emg_step
        )

    st.session_state.step += 1

col_btn1, col_btn2 = st.sidebar.columns(2)
if col_btn1.button("▶️ Step Classical", help="Step once with Fixed-Time control"):
    execute_optimization_step("Classical (Fixed-Time)", quantum_framework)
    st.rerun()

if col_btn2.button("⚛️ Step Quantum", help="Step once with QAOA optimization"):
    execute_optimization_step("Quantum QAOA", quantum_framework)
    st.rerun()

if st.sidebar.button("🤖 Step Adaptive Rule-Based", help="Step with classical adaptive rule heuristic"):
    execute_optimization_step("Classical (Rule-Based Adaptive)", quantum_framework)
    st.rerun()

st.sidebar.subheader("3. Dynamic City Events")
st.sidebar.caption("Trigger real-world events that modify network state:")

e_col1, e_col2 = st.sidebar.columns(2)
if e_col1.button("💥 Sudden Congestion"):
    nodes = st.session_state.events.trigger_sudden_congestion(['B', 'E'], extra_vehicles=18)
    st.sidebar.warning(f"Congestion spike injected at intersections {', '.join(nodes)}!")
    st.rerun()

if e_col2.button("🚗 Accident (Lane Block)"):
    acc_node = st.session_state.events.trigger_accident('B', severity=0.75)
    st.sidebar.error(f"Accident at {acc_node}! Capacity reduced by 75%.")
    st.rerun()

e_col3, e_col4 = st.sidebar.columns(2)
if e_col3.button("🚧 Road Closure"):
    edge = st.session_state.events.trigger_road_closure('B', 'C')
    st.sidebar.error(f"Road {edge[0]} ↔ {edge[1]} completely closed!")
    st.rerun()

if e_col4.button("🚑 Dispatch Ambulance"):
    path = st.session_state.corridor.trigger_emergency('A', 'F')
    st.sidebar.success(f"Ambulance dispatched! Route: {' ➔ '.join(path)}")
    st.rerun()

if st.sidebar.button("🧹 Clear Active Events"):
    st.session_state.events.clear_all_events()
    st.session_state.corridor.reset()
    st.sidebar.info("All dynamic incidents and closures cleared.")
    st.rerun()

st.sidebar.subheader("4. Reset Simulation")
if st.sidebar.button("🔄 Reset Entire System"):
    config.set_seed()
    st.session_state.network.reset()
    st.session_state.simulator.reset()
    st.session_state.events.clear_all_events()
    st.session_state.corridor.reset()
    st.session_state.metrics_classical.reset()
    st.session_state.metrics_quantum.reset()
    st.session_state.step = 0
    st.session_state.last_mode = "None"
    st.session_state.last_quantum_telemetry = None
    st.session_state.demo_logs.clear()
    st.sidebar.success("System reset to initial baseline.")
    st.rerun()

# --- Main Dashboard Tabs ---
tab_overview, tab_quantum, tab_corridor, tab_comparison, tab_demo, tab_welfare = st.tabs([
    "🚦 Network & Live Traffic",
    "⚛️ Quantum Optimization Engine",
    "🚑 Emergency Green Corridor",
    "📊 Classical vs Quantum Metrics",
    "🎬 1-Click End-to-End Demo",
    "🌍 Social Welfare & Ethics"
])

# ==============================================================================
# TAB 1: Network & Live Traffic Overview
# ==============================================================================
with tab_overview:
    # KPI Metric Cards Row
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6 = st.columns(6)

    total_q = st.session_state.simulator.get_total_queue_length()
    avg_q = total_q / config.NUM_INTERSECTIONS
    avg_wait = st.session_state.simulator.get_average_wait_time()
    total_thru = st.session_state.simulator.total_vehicles_served
    ped_demand = st.session_state.ped_mgr.get_total_pedestrian_demand()
    emg_time = st.session_state.corridor.travel_time_steps

    kpi_col1.metric("Average Queue", f"{avg_q:.1f} cars", f"{total_q} total")
    kpi_col2.metric("Average Delay", f"{avg_wait:.1f} s", "per vehicle")
    kpi_col3.metric("Total Throughput", f"{total_thru}", "vehicles cleared")
    kpi_col4.metric("Pedestrians Waiting", f"{ped_demand}", "crossing demand")
    kpi_col5.metric("Est. Fuel (L)", f"{total_q * config.FUEL_IDLE_PER_VEHICLE_STEP:.2f} L", "idle consumption")
    kpi_col6.metric("Est. CO2 (kg)", f"{total_q * config.FUEL_IDLE_PER_VEHICLE_STEP * config.CO2_PER_LITER_FUEL:.2f} kg", "emissions")

    st.markdown("<br>", unsafe_allow_html=True)

    view_col1, view_col2 = st.columns([1, 1])

    with view_col1:
        st.subheader("🗺️ OpenStreetMap Geographical Visualization")
        st.caption("Central London Westminster Grid • Intersections, density-colored roads, 🚑 ambulance & 🏥 hospital")

        # Map display with guaranteed offline fallback
        map_rendered = False
        if FOLIUM_AVAILABLE:
            try:
                folium_map = create_folium_map(st.session_state.network, st.session_state.corridor)
                st_folium(folium_map, width="100%", height=400, returned_objects=[])
                map_rendered = True
            except Exception as e:
                st.warning(f"Interactive map rendering offline: {e}. Displaying topological fallback.")

        if not map_rendered:
            st.info("Displaying local network view (offline tile fallback).")
            fallback_fig = create_network_figure(st.session_state.network, st.session_state.corridor)
            st.plotly_chart(fallback_fig, use_container_width=True)

    with view_col2:
        st.subheader("🕸️ Network Topology & Signal State Flow")
        st.caption("NetworkX Connected Graph • Node sizes reflect queue backlog • 🟢 Green / 🔴 Red Signal status")
        net_fig = create_network_figure(st.session_state.network, st.session_state.corridor)
        st.plotly_chart(net_fig, use_container_width=True)

    # Detailed Table of Intersection States
    st.subheader("📋 Live Intersection Telemetry")
    table_data = []
    for node_id in config.INTERSECTION_IDS:
        s = st.session_state.network.get_state(node_id)
        m = config.INTERSECTION_METADATA[node_id]
        table_data.append({
            "Node": node_id,
            "Location Name": m['name'],
            "Current Signal": "🟢 Green (Priority)" if s.signal_state == 1 else "🔴 Red (Cross)",
            "Queue Length": f"{s.queue_length} / {s.capacity}",
            "Effective Capacity": s.effective_capacity,
            "Pedestrian Demand": s.pedestrian_demand,
            "Accident Severity": f"{int(s.accident_severity * 100)}%",
            "Emergency Priority": "🚨 ACTIVE" if s.emergency_priority else "None"
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)

# ==============================================================================
# TAB 2: Quantum Optimization Engine
# ==============================================================================
with tab_quantum:
    st.subheader("⚛️ Mathematical Formulation & Quantum Transparency")
    st.markdown("""
    The traffic signal optimization across interconnected intersections is formulated as a **Quadratic Unconstrained Binary Optimization (QUBO)** problem,
    algebraically converted to an **Ising Spin Hamiltonian** ($x_i = \\frac{1 - Z_i}{2}$), and solved using the **Quantum Approximate Optimization Algorithm (QAOA)**.
    """)

    q_col1, q_col2 = st.columns([1, 1])

    with q_col1:
        st.markdown("#### 1. QUBO Formulation ($x_i \\in \\{0, 1\\}$)")
        st.latex(r"H_{\text{QUBO}}(x) = \sum_{i} Q_{ii} x_i + \sum_{i < j} Q_{ij} x_i x_j")
        st.markdown("""
        - **$x_i = 1$**: Assign Green light to primary congested corridor.
        - **$x_i = 0$**: Assign Green light to secondary / pedestrian walk cycle.
        - **Linear Terms $Q_{ii}$**: Balance queue clearance ($-w_q Q_i$), density relief, pedestrian cross penalty ($+w_p P_i$), and emergency priority ($-w_{\text{emg}} \\times 35$).
        - **Quadratic Terms $Q_{ij}$**: Anti-conflict penalty ($+P$) to prevent adjacent gridlock, or green wave reward ($-2.5P$) along the emergency corridor.
        """)

        if st.session_state.last_qubo_meta:
            Q, meta = st.session_state.last_qubo_meta
            st.markdown("**Active QUBO Linear Coefficients ($Q_{ii}$):**")
            linear_df = pd.DataFrame([
                {"Intersection": node, "Linear Term Q_ii": meta['linear_terms'][node]['total_linear'],
                 "Queue Comp": meta['linear_terms'][node]['queue_term'],
                 "Pedestrian Comp": meta['linear_terms'][node]['ped_term'],
                 "Emergency Comp": meta['linear_terms'][node]['emg_term']}
                for node in config.INTERSECTION_IDS
            ])
            st.dataframe(linear_df, use_container_width=True)

    with q_col2:
        st.markdown("#### 2. Ising Hamiltonian ($Z_i \\in \\{+1, -1\\}$)")
        st.latex(r"H_{\text{Ising}} = \text{Offset} + \sum_{i} h_i Z_i + \sum_{i < j} J_{ij} Z_i Z_j")
        st.markdown("""
        - Using the exact substitution $x_i = \\frac{1 - Z_i}{2}$:
          - $h_i = -\\frac{Q_{ii}}{2} - \\sum_{j \\neq i} \\frac{Q_{ij}}{4}$ (Local longitudinal field)
          - $J_{ij} = \\frac{Q_{ij}}{4}$ (Two-body spin-spin coupling)
        """)

        if st.session_state.last_ising_meta:
            h, J, offset = st.session_state.last_ising_meta
            st.markdown(f"**Energy Offset:** `{offset:.4f}`")
            ising_df = pd.DataFrame([
                {"Qubit / Node": f"q_{i} ({config.INTERSECTION_IDS[i]})", "Local Field h_i": h.get(i, 0.0)}
                for i in range(config.NUM_INTERSECTIONS)
            ])
            st.dataframe(ising_df, use_container_width=True)

    st.markdown("---")
    st.subheader("🔬 QAOA Circuit & Measurement Telemetry")

    if st.session_state.last_quantum_telemetry:
        tel = st.session_state.last_quantum_telemetry
        q_m1, q_m2, q_m3, q_m4 = st.columns(4)
        q_m1.metric("Framework", tel['framework'])
        q_m2.metric("Qubits Used", tel['circuit_info']['qubits'])
        q_m3.metric("Optimal Parameters", f"γ={tel['opt_gamma']}, β={tel['opt_beta']}")
        q_m4.metric("Best Measured Bitstring", tel['best_bitstring'], f"Cost: {tel.get('qubo_cost', 0.0)}")

        # Plot Measurement Probabilities
        st.markdown("##### Measured State Probability Distribution")
        counts = tel['counts']
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
        bitstrings = [item[0] for item in sorted_counts]
        shots_sampled = [item[1] for item in sorted_counts]

        bar_fig = px.bar(
            x=bitstrings, y=shots_sampled,
            labels={'x': 'Measured Bitstring (Little-Endian: [F,E,D,C,B,A])', 'y': 'Measurement Shots'},
            title="Top-10 Sampled Quantum States (QAOA Ansatz p=1)",
            color=shots_sampled, color_continuous_scale='teal'
        )
        bar_fig.update_layout(height=320, plot_bgcolor='#f8fafc')
        st.plotly_chart(bar_fig, use_container_width=True)
    else:
        st.info("No quantum execution yet. Click '⚛️ Step Quantum' in the sidebar or run the 1-Click Demo to inspect live QAOA circuits.")

# ==============================================================================
# TAB 3: Emergency Green Corridor
# ==============================================================================
with tab_corridor:
    st.subheader("🚑 Emergency Green Corridor Management")
    st.markdown("""
    When an emergency occurs, an ambulance is routed from its origin (**Parliament Square - Node A**) to the regional trauma center (**St Thomas Hospital - Node F**).
    The platform creates an active **Green Wave** by holding signals green along the transit path, clearing queues ahead of time while continuing optimal control elsewhere.
    """)

    cor_status = st.session_state.corridor.get_status()

    c_col1, c_col2, c_col3, c_col4 = st.columns(4)
    c_col1.metric("Ambulance Location", cor_status['current_location'] or ("At Hospital" if cor_status['completed'] else "Stationary at Base"))
    c_col2.metric("Destination Hospital", f"Node {cor_status['destination']} (St Thomas)")
    c_col3.metric("Corridor Route", " ➔ ".join(cor_status['route']) if cor_status['route'] else "None")
    c_col4.metric("Transit Duration", f"{cor_status['travel_time_steps']} steps", f"Disruption delay: {cor_status['disruption_delay']} s")

    st.markdown("#### Corridor Progression Timeline")
    if cor_status['route']:
        progress_val = cor_status['progress_step'] / max(1, cor_status['total_route_steps'])
        st.progress(min(1.0, progress_val))
        st.caption(f"Progress: Step {cor_status['progress_step']} of {cor_status['total_route_steps']} intersections traversed.")
    else:
        st.caption("Emergency corridor currently inactive.")

    st.markdown("---")
    st.subheader("🛡️ Road Closure Resilience")
    st.markdown("""
    If an accident or road maintenance causes a road segment to close (e.g., Road B ↔ C is blocked),
    the Emergency Corridor **automatically reroutes** the ambulance through alternative avenues (e.g. A ➔ D ➔ E ➔ F)
    and dynamically re-optimizes the green wave on the fly.
    """)

# ==============================================================================
# TAB 4: Classical vs Quantum Comparison
# ==============================================================================
with tab_comparison:
    st.subheader("📊 Comparative Benchmarking: Classical vs Hybrid Quantum")

    df_class = st.session_state.metrics_classical.to_dataframe()
    df_quant = st.session_state.metrics_quantum.to_dataframe()

    if len(df_class) > 0 or len(df_quant) > 0:
        sum_class = st.session_state.metrics_classical.get_summary()
        sum_quant = st.session_state.metrics_quantum.get_summary()

        comp_metrics = [
            ("Avg Queue Length (cars)", sum_class.get('avg_queue', 0), sum_quant.get('avg_queue', 0), True),
            ("Avg Vehicle Delay (s)", sum_class.get('avg_wait_time', 0), sum_quant.get('avg_wait_time', 0), True),
            ("Total Throughput (cars)", sum_class.get('total_throughput', 0), sum_quant.get('total_throughput', 0), False),
            ("Total Fuel Consumption (L)", sum_class.get('total_fuel_liters', 0), sum_quant.get('total_fuel_liters', 0), True),
            ("Total CO2 Emissions (kg)", sum_class.get('total_co2_kg', 0), sum_quant.get('total_co2_kg', 0), True),
            ("Social Welfare Index", sum_class.get('social_welfare_index', 0), sum_quant.get('social_welfare_index', 0), False)
        ]

        # Metric comparison cards
        st.markdown("##### Consolidated Key Performance Indicators")
        kpi_cols = st.columns(len(comp_metrics))
        for idx, (label, val_c, val_q, lower_is_better) in enumerate(comp_metrics):
            diff = val_q - val_c
            pct = (diff / val_c * 100.0) if val_c != 0 else 0.0
            delta_str = f"{diff:+.1f} ({pct:+.1f}%)"
            delta_color = "inverse" if lower_is_better else "normal"
            kpi_cols[idx].metric(label, f"{val_q}", delta_str, delta_color=delta_color)

        st.markdown("---")

        # Side-by-side comparative charts
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("##### Vehicle Queue Backlog Over Time")
            fig_q = go.Figure()
            if len(df_class) > 0:
                fig_q.add_trace(go.Scatter(x=df_class['step'], y=df_class['total_queue'], mode='lines+markers', name='Classical (Fixed-Time)', line=dict(color='#e74c3c', width=2)))
            if len(df_quant) > 0:
                fig_q.add_trace(go.Scatter(x=df_quant['step'], y=df_quant['total_queue'], mode='lines+markers', name='Quantum (QAOA)', line=dict(color='#0284c7', width=3)))
            fig_q.update_layout(xaxis_title="Simulation Step", yaxis_title="Total Queued Vehicles", height=320, plot_bgcolor='#f8fafc')
            st.plotly_chart(fig_q, use_container_width=True)

        with chart_col2:
            st.markdown("##### Estimated Cumulative CO2 Emissions (kg)")
            fig_co2 = go.Figure()
            if len(df_class) > 0:
                fig_co2.add_trace(go.Scatter(x=df_class['step'], y=df_class['cumulative_co2_kg'], mode='lines', name='Classical Emissions', line=dict(color='#e74c3c', dash='dash')))
            if len(df_quant) > 0:
                fig_co2.add_trace(go.Scatter(x=df_quant['step'], y=df_quant['cumulative_co2_kg'], mode='lines', name='Quantum Emissions', line=dict(color='#0284c7', width=3)))
            fig_co2.update_layout(xaxis_title="Simulation Step", yaxis_title="Cumulative CO2 (kg)", height=320, plot_bgcolor='#f8fafc')
            st.plotly_chart(fig_co2, use_container_width=True)

    else:
        st.info("No comparative execution data recorded yet. Step simulation in Classical and Quantum modes, or click 'Run Full Demo' in Tab 5.")

# ==============================================================================
# TAB 5: 1-Click End-to-End Demo
# ==============================================================================
with tab_demo:
    st.subheader("🎬 1-Click End-to-End Hackathon Demonstration")
    st.markdown("""
    Run the complete, automated hackathon story in a single click:
    1. **Baseline Traffic**: Steps under Classical Fixed-Time control.
    2. **Sudden Congestion & Accident**: Real-time traffic spike injected.
    3. **Emergency Dispatch**: Ambulance dispatched with trauma corridor active.
    4. **Quantum QAOA Optimization**: Formulates QUBO/Ising and executes QAOA.
    5. **Green Corridor Transit**: Ambulance advances through green lights to St Thomas Hospital.
    6. **Signal Restoration**: Corridor cleared, normal adaptive welfare signals restored.
    7. **Comprehensive Benchmarking**: Final side-by-side comparison generated.
    """)

    if st.button("🚀 RUN FULL DEMO NOW", type="primary", use_container_width=True):
        demo_progress = st.progress(0.0)
        status_placeholder = st.empty()
        log_placeholder = st.empty()
        logs = []

        def log_demo(msg):
            logs.append(f"⏱️ {time.strftime('%H:%M:%S')} - {msg}")
            log_placeholder.code("\n".join(logs[-8:]), language="markdown")

        # Step 1: Baseline Classical Run
        status_placeholder.info("Stage 1/6: Running baseline traffic under Classical Fixed-Time control...")
        log_demo("Stage 1: Initializing road network and running 5 steps of Classical control...")
        for i in range(5):
            execute_optimization_step("Classical (Fixed-Time)", quantum_framework)
            demo_progress.progress((i + 1) / 30.0)
            time.sleep(0.05)

        # Step 2: Inject Congestion and Accident
        status_placeholder.warning("Stage 2/6: Injecting sudden traffic congestion spike and road accident...")
        log_demo("Stage 2: Injecting severe congestion on Whitehall (Node B) and accident...")
        st.session_state.events.trigger_sudden_congestion(['B', 'E'], extra_vehicles=15)
        st.session_state.events.trigger_accident('B', severity=0.70)
        demo_progress.progress(0.35)
        time.sleep(0.1)

        # Step 3: Dispatch Ambulance
        status_placeholder.error("Stage 3/6: 🚨 Emergency Vehicle Dispatched from Parliament Sq to Hospital!")
        log_demo("Stage 3: 🚑 Ambulance dispatched from Node A -> Hospital Node F.")
        path = st.session_state.corridor.trigger_emergency('A', 'F')
        log_demo(f"Shortest emergency path computed: {' ➔ '.join(path)}")
        demo_progress.progress(0.45)
        time.sleep(0.1)

        # Step 4: Hybrid Quantum QAOA Optimization & Corridor Progression
        status_placeholder.info("Stage 4/6: Quantum Optimization in progress (QUBO ➔ Ising ➔ QAOA)...")
        log_demo("Stage 4: Executing QAOA variational optimization on Qiskit Aer...")
        step_count = 0
        while st.session_state.corridor.is_active and step_count < 10:
            execute_optimization_step("Quantum QAOA", quantum_framework)
            step_count += 1
            demo_progress.progress(0.45 + (step_count / 10.0) * 0.4)
            log_demo(f"Ambulance moving: current intersection {st.session_state.corridor.get_current_ambulance_node()}")
            time.sleep(0.05)

        # Step 5: Hospital Arrival & Signal Restoration
        status_placeholder.success("Stage 5/6: 🎉 Ambulance arrived safely at Hospital! Restoring normal traffic signals...")
        log_demo("Stage 5: Ambulance arrived at St Thomas Hospital! Restoring balanced welfare signals.")
        demo_progress.progress(0.90)

        # Run 3 additional steps of balanced Quantum control
        for _ in range(3):
            execute_optimization_step("Quantum QAOA", quantum_framework)
            time.sleep(0.05)

        # Step 6: Complete
        demo_progress.progress(1.0)
        status_placeholder.success("Stage 6/6: Complete End-to-End Demonstration Finished! Inspect comparisons below.")
        log_demo("Stage 6: Demonstration complete. Comparative analytics ready.")
        st.session_state.demo_logs = logs
        st.balloons()

    if st.session_state.demo_logs:
        st.markdown("##### Demonstration Execution Log")
        st.code("\n".join(st.session_state.demo_logs), language="markdown")

# ==============================================================================
# TAB 6: Social Welfare & Quantum Honesty
# ==============================================================================
with tab_welfare:
    st.subheader("🌍 Public Interest & Social Welfare Optimization")
    st.markdown("""
    ### Why Traffic Signal Allocation is a Civic Social Welfare Problem:
    In congested metropolitan environments, **road space is a strictly limited civic commons**.
    Traditional traffic systems make static or siloed decisions that disadvantage vulnerable road users,
    induce stop-and-go fuel burns, and delay life-saving emergency services.

    Our platform treats traffic control as a **civic utility allocation optimization**:
    1. **Emergency Priority as Human Welfare**: A medical patient's transit time is prioritized through green waves, mathematically weighted against the temporary delay to cross-traffic.
    2. **Pedestrian Equity**: Pedestrian crosswalk delays are incorporated directly into the objective, preventing high-speed vehicle favoritism from endangering or stranding pedestrians.
    3. **Environmental Justice**: Unnecessary phase flickering and stop-and-go cycles cause elevated particulate and CO2 emissions in urban cores; our switch-penalty terms explicitly mitigate this.
    """)

    st.markdown("---")
    st.subheader("⚖️ Quantum Honesty & Scientific Integrity")
    st.info("""
    **Transparency Notice**:
    - **No False Quantum Advantage**: We explicitly state that this prototype is a proof-of-concept simulation using Qiskit Aer and PennyLane classical simulator backends.
    - **Problem Scale**: For a 6-intersection urban grid (6 qubits), classical heuristics and brute-force solvers can easily solve the problem. Quantum advantage is **not claimed** for this scale.
    - **Future Value**: As urban networks expand to hundreds of intersections, the combinatorial solution space grows exponentially ($2^N$). This project demonstrates the exact mathematical formulation (QUBO $\\rightarrow$ Ising $\\rightarrow$ QAOA) required to scale onto next-generation fault-tolerant quantum processing units.
    """)
