import streamlit as st
from experiments.results import ExperimentResult
from experiments.comparison import ComparisonEngine
from dashboard.charts import plot_time_series, plot_comparison
from visualization.data_adapter import build_network_visualization_state
from visualization.network_visualizer import TrafficNetworkVisualizer

def render_kpis(result: ExperimentResult):
    metrics = result.metrics
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Waiting Time", f"{metrics.get('average_waiting_time', 0):.2f} s")
    col2.metric("Max Waiting Time", f"{metrics.get('max_waiting_time', 0):.2f} s")
    col3.metric("Average Queue Length", f"{metrics.get('average_queue_length', 0):.2f}")
    col4.metric("Max Queue Length", f"{metrics.get('maximum_queue_length', 0)}")
    
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Throughput", f"{metrics.get('true_throughput_per_sec', 0):.2f} veh/s")
    col6.metric("Completed Vehicles", f"{metrics.get('throughput', 0)}")
    col7.metric("Average Travel Time", f"{metrics.get('average_travel_time', 0):.2f} s")
    col8.metric("Runtime", f"{result.runtime_seconds:.2f} s")
    
def render_environmental(result: ExperimentResult):
    metrics = result.metrics
    col1, col2 = st.columns(2)
    col1.metric("Estimated Fuel Consumption", f"{metrics.get('fuel_estimate_liters', 0):.2f} L")
    col2.metric("Estimated CO₂ Emissions", f"{metrics.get('co2_estimate_kg', 0):.2f} kg")

def render_quantum_details(result: ExperimentResult):
    q_config = result.quantum_configuration
    if not q_config:
        st.info("Classical controller selected. No quantum details available.")
        return
        
    st.write("### Quantum Solver Configuration")
    col1, col2, col3 = st.columns(3)
    col1.metric("Quantum Backend", q_config.get("backend", "N/A"))
    col2.metric("Shots", q_config.get("shots", "N/A"))
    col3.metric("Optimization Iterations", q_config.get("maxiter", "N/A"))

    st.divider()
    st.write("### Deep Quantum Analytics")
    st.write("Visualizations generated from the underlying QUBO matrices and QAOA execution profiles.")
    
    q_data = result.quantum_data
    if q_data and "hybrid_history" in q_data and len(q_data["hybrid_history"]) > 0:
        history_list = q_data["hybrid_history"]
        
        cycle_options = [f"Timestep {h['time']}" for h in history_list]
        selected_cycle = st.selectbox("Select Optimization Cycle:", cycle_options)
        idx = cycle_options.index(selected_cycle)
        
        h = history_list[idx]
        q_payload = h.get("quantum_data", {})
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("QAOA Objective Value", f"{h['objective_value']:.4f}")
            st.metric("Selected Bitstring", h['quantum_solution'])
        with col_b:
            st.metric("Number of Qubits", len(q_payload.get("variables", [])))
            st.metric("Status", "SUCCESS")
            
        from visualization.quantum_visualizer import QuantumVisualizer
        
        st.divider()
        if "history" in q_payload and q_payload["history"]:
            st.plotly_chart(QuantumVisualizer.render_convergence(q_payload["history"]), use_container_width=True)
            
        if "samples" in q_payload and q_payload["samples"]:
            st.plotly_chart(QuantumVisualizer.render_distribution(q_payload["samples"]), use_container_width=True)
            
        if "qubo_matrix" in q_payload and "variables" in q_payload:
            with st.expander("View Raw QUBO Matrix Heatmap", expanded=False):
                st.plotly_chart(QuantumVisualizer.render_qubo_heatmap(q_payload["qubo_matrix"], q_payload["variables"]), use_container_width=True)
                
        with st.expander("Variable to Signal Decoding Mapping", expanded=False):
            st.write("How the selected bitstring maps to physical traffic green times:")
            st.json(h["signal_plan"])
    else:
        st.warning("Quantum data payload missing from this run.")

def render_comparison_tab(comp_engine):
    if not comp_engine:
        st.info("Run the Benchmark Comparison from the sidebar to view results.")
        return
        
    summary = comp_engine.generate_summary()
    agg = summary["aggregated"]
    improv = summary["improvements"]
    
    if not agg:
        st.error("No valid comparison data.")
        return
        
    scenarios = list(agg.keys())
    if not scenarios:
        return
        
    selected_scenario = st.selectbox("Select Scenario:", scenarios, index=0)
    
    st.write("### Normalized Performance Improvements")
    st.write("Comparing Quantum Hybrid against Classical Baseline.")
    
    header = "| Metric | Classical | Hybrid | Absolute Diff | % Change |"
    sep = "|---|---|---|---|---|"
    rows = []
    
    scenario_improv = improv.get(selected_scenario, {})
    if scenario_improv:
        for ctrl, metrics_comp in scenario_improv.items():
            if "Hybrid" in ctrl:
                for m, stats in metrics_comp.items():
                    c = f"{stats['baseline_mean']:.2f}"
                    h = f"{stats['comparison_mean']:.2f}"
                    d = f"{stats['absolute_diff']:+.2f}"
                    p = f"{stats['percentage_change']:+.1f}%"
                    rows.append(f"| {m} | {c} | {h} | {d} | {p} |")
                    
        if rows:
            st.markdown("\n".join([header, sep] + rows))
        else:
            st.info("No hybrid controller found in this scenario to compare against.")
    else:
        st.info("Could not calculate improvements (Missing classical baseline).")
        
    st.divider()
    from dashboard.charts import plot_comparison, plot_time_series_overlay
    plot_comparison(comp_engine, selected_scenario)
    plot_time_series_overlay(comp_engine, selected_scenario)

def render_network_overview(result: ExperimentResult, simulator=None, emergency_controller=None, event_manager=None):
    if not simulator:
        st.write("### Network Topology (4 Intersections)")
        st.code('''
        I1 ---- I2
        |       |
        |       |
        I3 ---- I4
        ''', language="text")
        return
        
    st.write("### Live Network Visualization")
    state = build_network_visualization_state(simulator, emergency_controller, event_manager)
    fig = TrafficNetworkVisualizer.render_network(state)
    st.plotly_chart(fig, use_container_width=True)
        
def render_emergency_corridor(result: ExperimentResult):
    if not result.configuration.get("emergency_enabled", False):
        st.info("No active emergency corridor.")
        return
        
    st.warning("🚨 EMERGENCY VEHICLE DETECTED 🚨")
    col1, col2 = st.columns(2)
    col1.metric("Emergency Avg Travel Time", f"{result.metrics.get('emergency_average_travel_time', 0):.2f} s")
    col2.metric("Emergency Vehicles Processed", f"{result.metrics.get('emergency_vehicles', 0)}")
    
    st.write("**Route:** I1 → I2 → I4")
    
def render_congestion_events(result: ExperimentResult):
    if not result.configuration.get("congestion_event_enabled", False):
        st.info("No congestion event active.")
        return
        
    st.warning("🚦 DYNAMIC CONGESTION EVENT DETECTED 🚦")
    st.write("Target Intersection: **I2**")
    st.write("Demand Increase: **60 veh/min**")
