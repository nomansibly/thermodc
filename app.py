"""ThermoDC interactive Streamlit dashboard."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from thermodc.model import Inputs, REFERENCE_INLET_C, simulate
from thermodc.scenarios import SCENARIOS
from thermodc.telemetry import connect, history, record

st.set_page_config(page_title="ThermoDC | Thermal Lab", page_icon="🌡️",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.block-container {padding-top:1.35rem;max-width:1450px}
div[data-testid="stMetric"] {background:rgba(128,150,180,.09);
  border:1px solid rgba(128,150,180,.20);padding:14px;border-radius:12px}
div[data-testid="stMetricLabel"] {font-weight:650}
</style>
""", unsafe_allow_html=True)

st.title("ThermoDC")
st.caption("Data Center Thermal Monitoring & Energy Optimization · Educational steady-state digital twin")
st.warning("Demonstration model — not CFD, real facility telemetry, or a safety/engineering certification tool.",
           icon="⚠️")

with st.sidebar:
    st.header("Operating conditions")
    scenario = st.selectbox("Scenario", list(SCENARIOS), key="scenario")
    base = SCENARIOS[scenario]
    st.caption("Changing a preset reloads its default control values.")
    if st.session_state.get("applied_scenario") != scenario:
        for key, value in {
            "util": base.utilization_pct, "supply": base.supply_c,
            "airflow": base.airflow_pct, "cop": base.cooling_cop,
            "recirc": base.recirculation_pct, "outdoor": base.outdoor_c,
        }.items():
            st.session_state[key] = value
        st.session_state.applied_scenario = scenario
    util = st.slider("IT utilization (%)", 10, 100, key="util", step=5)
    supply = st.slider("Supply air (°C)", 16, 28, key="supply")
    airflow = st.slider("Relative airflow (%)", 40, 150, key="airflow", step=5)
    cop = st.slider("Cooling COP", 1.5, 7.0, key="cop", step=0.5)
    recirc = st.slider("Hot-air recirculation (%)", 0, 50, key="recirc", step=5)
    outdoor = st.slider("Outdoor air (°C)", -20, 40, key="outdoor", step=5)
    st.caption("Outdoor temperature is contextual; COP is adjusted independently.")

inputs = Inputs(util, supply, airflow, cop, recirc, outdoor)
result = simulate(inputs)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Max rack inlet", f"{result.max_inlet_c:.1f} °C")
col2.metric("Facility demand", f"{result.facility_kw:.1f} kW")
col3.metric("PUE", f"{result.pue:.2f}")
col4.metric("Racks above 27°C", f"{result.hot_racks} / 12")

if result.status == "HIGH RISK":
    st.error("HIGH RISK: the simplified model predicts a maximum inlet above 32°C.")
elif result.status == "ELEVATED":
    st.warning("ELEVATED: at least one modeled inlet exceeds the illustrative 27°C reference.")
else:
    st.success("WITHIN REFERENCE: all modeled inlets are at or below 27°C.")

a,b=st.columns([1.25, 1])
with a:
    st.subheader("12-rack inlet heatmap")
    heat = pd.DataFrame([result.rack_inlet_c[:6], result.rack_inlet_c[6:]],
                        index=["Row A", "Row B"],
                        columns=[f"R{i:02}" for i in range(1,7)])
    fig=px.imshow(heat, text_auto=".1f", aspect="auto",
                  color_continuous_scale="RdYlBu_r", zmin=16, zmax=38,
                  labels={"color":"Inlet °C"})
    fig.update_layout(margin=dict(l=5,r=5,t=15,b=5),height=290)
    st.plotly_chart(fig,use_container_width=True)
with b:
    st.subheader("Power breakdown")
    power = pd.DataFrame({"Subsystem":["IT equipment","Cooling","Fan and auxiliaries"],
                          "kW":[result.it_kw,result.cooling_kw,result.auxiliary_kw]})
    fig=px.bar(power,x="Subsystem",y="kW",color="Subsystem",text_auto=".1f")
    fig.update_layout(showlegend=False,margin=dict(l=5,r=5,t=15,b=5),height=290)
    st.plotly_chart(fig,use_container_width=True)

st.subheader("Load sensitivity")
loads=list(range(10,101,5))
maxima=[simulate(Inputs(load,supply,airflow,cop,recirc,outdoor)).max_inlet_c
        for load in loads]
fig=go.Figure()
fig.add_trace(go.Scatter(x=loads,y=maxima,name="Max rack inlet",mode="lines",
                         line=dict(color="#19a7a0",width=3)))
fig.add_hline(y=REFERENCE_INLET_C,line_dash="dash",line_color="#e69a45",
              annotation_text="27°C reference")
fig.add_trace(go.Scatter(x=[util],y=[result.max_inlet_c],mode="markers",
                         name="Current condition",marker=dict(size=12,color="#167fba")))
fig.update_layout(height=310,margin=dict(l=5,r=5,t=15,b=5),
                  xaxis_title="IT utilization (%)",yaxis_title="Rack inlet °C")
st.plotly_chart(fig,use_container_width=True)

st.subheader("Telemetry lab")
st.caption("Snapshots are stored in a local SQLite database. Only simulations you explicitly save are logged.")
if st.button("Save current snapshot",type="primary"):
    connection=connect()
    try:
        record(connection,scenario,inputs,result)
    finally:
        connection.close()
    st.success("Snapshot saved to data/thermodc.sqlite")
try:
    connection=connect()
    try:
        rows=history(connection)
    finally:
        connection.close()
    if rows:
        frame=pd.DataFrame(rows)
        st.dataframe(frame.drop(columns=["rack_inlet_json","id"]),use_container_width=True,
                     hide_index=True)
        st.download_button("Download telemetry CSV",
                           frame.to_csv(index=False).encode("utf-8"),
                           file_name="thermodc_telemetry.csv",mime="text/csv")
    else:
        st.info("No telemetry recorded yet. Save a snapshot to populate this table.")
except (OSError, PermissionError) as exc:
    st.info(f"Telemetry storage is not writable here: {exc}")

with st.expander("Methodology and limitations"):
    st.markdown("""
    **Lumped heat balance:** ΔT = Q_IT / (ρ × V̇ × cₚ).
    Design airflow = 12 m³/s; density = 1.2 kg/m³; cₚ = 1005 J/(kg·K).
    IT installed capacity = 120 kW. Cooling kW = IT kW / user-specified COP.
    Fan/auxiliary kW = 3 + 4 × (relative airflow)³.
    Facility power = IT + cooling + fan/auxiliary; PUE = facility / IT.
    Rack values include synthetic rack factors, not resolved flow physics.
    This is a **steady-state** scenario explorer, not a transient failure simulation.
    The 27°C marker is only an illustrative reference, not a universal rack limit.
    Outdoor conditions do not automatically change cooling performance.
    """)
