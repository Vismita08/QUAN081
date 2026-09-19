import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List
from experiments.results import ExperimentResult

def plot_time_series(result: ExperimentResult):
    st.subheader("Performance Over Time")
    
    metrics = result.metrics
    hist_wait = metrics.get("history_avg_wait", [])
    hist_q = metrics.get("history_avg_queue", [])
    hist_thru = metrics.get("history_throughput", [])
    
    if not hist_wait:
        st.info("Time-series data is not available.")
        return
        
    df = pd.DataFrame({
        "Avg Waiting Time (s)": hist_wait,
        "Avg Queue Length": hist_q,
        "Cumulative Throughput": hist_thru
    })
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Simulation Time vs Average Waiting Time**")
        fig1 = px.line(df, y="Avg Waiting Time (s)", color_discrete_sequence=["#10b981"])
        fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8fafc'))
        st.plotly_chart(fig1, use_container_width=True)
        
        st.write("**Simulation Time vs Average Queue Length**")
        fig2 = px.line(df, y="Avg Queue Length", color_discrete_sequence=["#8b5cf6"])
        fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8fafc'))
        st.plotly_chart(fig2, use_container_width=True)
        
    with col2:
        st.write("**Simulation Time vs Cumulative Throughput**")
        fig3 = px.line(df, y="Cumulative Throughput", color_discrete_sequence=["#3b82f6"])
        fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8fafc'))
        st.plotly_chart(fig3, use_container_width=True)

def plot_comparison(comp_engine, scenario_name: str):
    st.subheader("Distribution Analysis")
    
    # We want to plot box plots for metrics across all runs if possible
    # We'll just extract the raw metric values from results
    results = [r for r in comp_engine.results if r.scenario_name == scenario_name]
    if not results:
        return
        
    metrics_to_plot = ["average_waiting_time", "average_queue_length", "throughput", "runtime_seconds", "fuel_estimate_liters"]
    labels = ["Avg Wait (s)", "Avg Queue", "Throughput", "Runtime (s)", "Fuel (L)"]
    
    tabs = st.tabs(labels)
    
    for i, m in enumerate(metrics_to_plot):
        data = []
        for r in results:
            val = r.runtime_seconds if m == "runtime_seconds" else r.metrics.get(m, 0)
            data.append({"Controller": r.controller, "Value": val})
            
        df = pd.DataFrame(data)
        
        with tabs[i]:
            # Use bar charts for means to mimic Image 3
            avg_df = df.groupby("Controller").mean().reset_index()
            fig = px.bar(avg_df, x="Controller", y="Value", color="Controller", title=f"Average {labels[i]}",
                         color_discrete_map={"Classical": "#3b82f6", "Hybrid Quantum-Classical": "#8b5cf6"})
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f8fafc'),
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)

def plot_time_series_overlay(comp_engine, scenario_name: str):
    st.subheader("Time-Series Comparison Overlays")
    ts_data = comp_engine.get_time_series(scenario_name)
    averaged = ts_data.get("averaged", {})
    
    if not averaged.get("avg_wait"):
        st.info("Time-series overlays not available (no history traces found).")
        return
        
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Average Waiting Time Traces**")
        fig1 = go.Figure()
        for ctrl, trace in averaged["avg_wait"].items():
            color = "#8b5cf6" if "Hybrid" in ctrl else "#3b82f6"
            fig1.add_trace(go.Scatter(y=trace, mode='lines', name=ctrl, line=dict(color=color)))
        fig1.update_layout(xaxis_title="Time Step", yaxis_title="Waiting Time (s)", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8fafc'))
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.write("**Cumulative Throughput Traces**")
        fig2 = go.Figure()
        for ctrl, trace in averaged["throughput"].items():
            color = "#8b5cf6" if "Hybrid" in ctrl else "#3b82f6"
            fig2.add_trace(go.Scatter(y=trace, mode='lines', name=ctrl, line=dict(color=color)))
        fig2.update_layout(xaxis_title="Time Step", yaxis_title="Throughput (Vehicles)", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8fafc'))
        st.plotly_chart(fig2, use_container_width=True)
