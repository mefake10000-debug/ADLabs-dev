import streamlit as st
import pandas as pd
import requests
import time
import os

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AD Labs EdgeSight | Retail Operations",
    page_icon="🏪",
    layout="wide"
)

st.title("🏪 AD Labs EdgeSight — Store Intelligence Dashboard")
st.caption("On-Premise Computer Vision Telemetry & In-Store Operational Analytics")

# Sidebar: Controls
with st.sidebar:
    st.header("⚙️ Store Controls")
    store_id = st.text_input("Store Identifier", value="store_mumbai_001")
    auto_refresh = st.checkbox("Auto Refresh (every 5s)", value=True)
    st.markdown("---")
    st.info("Pure Vision-Based Analytics — No POS or external sensor integration required.")

# Fetch live metrics from API
try:
    live_resp = requests.get(f"{API_BASE}/api/v1/live?store_id={store_id}", timeout=3.0)
    data = live_resp.json() if live_resp.status_code == 200 else {}
except Exception as e:
    data = {}
    st.warning(f"Connecting to Edge API at {API_BASE}... ({e})")

# Alert Banner
if data.get("queue_alert_active"):
    st.error(
        f"🚨 **CHECKOUT CONGESTION ALERT**: Register queue exceeds comfortable SLA! "
        f"Queue: {data.get('queue_length')} people waiting (~{int(data.get('avg_queue_wait_seconds', 0))}s wait time). "
        f"Please dispatch an additional cashier."
    )

# Top KPI Metric Cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🚶 Total Visitors Today",
        value=data.get("total_visitors", 0),
        help="Cumulative footfall counted via entrance tripwires"
    )

with col2:
    st.metric(
        label="🏬 Net Store Occupancy",
        value=data.get("net_occupancy", 0),
        help="Current estimated customers inside the store (In minus Out)"
    )

with col3:
    queue_len = data.get("queue_length", 0)
    avg_wait = int(data.get("avg_queue_wait_seconds", 0))
    st.metric(
        label="⏳ Cashier Queue Length",
        value=f"{queue_len} people",
        delta=f"{avg_wait}s avg wait",
        delta_color="inverse" if queue_len > 4 else "normal"
    )

with col4:
    avg_dwell = data.get("avg_dwell_seconds", 0.0)
    exits = data.get("total_exits", 0)
    st.metric(
        label="⏱️ Avg Store Dwell",
        value=f"{avg_dwell}s",
        delta=f"{exits} total exits recorded",
        help="Average time shoppers spend actively engaged in store zones"
    )

st.markdown("---")

# Live Computer Vision Feed Section
st.subheader("🎥 Live Edge AI Vision Feed (Real-Time Model Output)")
st.caption("Live inference stream showing YOLO person detection, ByteTrack tracking IDs, doorway tripwires, and spatial zones.")

cam_col1, cam_col2 = st.columns([3, 1])

# Fetch available cameras
try:
    cams_resp = requests.get(f"{API_BASE}/api/v1/cameras", timeout=2.0)
    available_cams = cams_resp.json().get("cameras", ["cam_entrance_01"]) if cams_resp.status_code == 200 else ["cam_entrance_01"]
except Exception:
    available_cams = ["cam_entrance_01"]

with cam_col2:
    selected_cam = st.selectbox("Select Active Camera", options=available_cams, index=0)
    st.markdown("#### 🔍 Visual Legend")
    st.markdown("""
    * 🟩 **Green Line:** Entrance Tripwire (Counts In / Out)
    * 🟨 **Yellow Box:** Detected Person + Track ID
    * 🔴 **Red Contact Point:** Ground Foot Coordinate
    * 🟨 **Yellow Polygon:** Merchandising Dwell Zone
    * 🟦 **Cyan Polygon:** Cashier Queue Staging Area
    """)
    st.info("Frames are decoded, inferred, and rendered entirely on the on-premise edge node.")

with cam_col1:
    stream_tab1, stream_tab2 = st.tabs(["🔴 Live Fluid Stream (12 FPS)", "📸 Auto-Refreshing Snapshot"])

    with stream_tab1:
        st.markdown(
            f"""
            <div style="background-color: #121212; padding: 6px; border-radius: 10px; text-align: center; border: 1px solid #2a2a2a;">
                <img src="http://localhost:8000/api/v1/stream/{selected_cam}" style="width: 100%; border-radius: 8px; display: block;" alt="Live Model Inference Stream"/>
            </div>
            """,
            unsafe_allow_html=True
        )

    with stream_tab2:
        st.image(
            f"http://localhost:8000/api/v1/snapshot/{selected_cam}?t={time.time()}",
            caption=f"Latest Inferred Frame ({selected_cam})",
            use_container_width=True
        )

st.markdown("---")

# Historical Graphs
col_left, col_right = st.columns(2)

try:
    hist_resp = requests.get(f"{API_BASE}/api/v1/history?store_id={store_id}&limit=40", timeout=3.0)
    history = hist_resp.json() if hist_resp.status_code == 200 else []
except Exception:
    history = []

if history:
    df = pd.DataFrame(history)

    with col_left:
        st.subheader("📈 Real-Time Footfall (In vs Out)")
        chart_data = df[["timestamp_end", "in_count", "out_count"]].copy()
        chart_data.set_index("timestamp_end", inplace=True)
        st.bar_chart(chart_data)

    with col_right:
        st.subheader("⏱️ Checkout Queue Congestion Trend")
        q_data = df[["timestamp_end", "queue_length", "avg_queue_wait_seconds"]].copy()
        q_data.set_index("timestamp_end", inplace=True)
        st.line_chart(q_data)
else:
    st.info("Awaiting telemetry rollups from edge analyzer. (Run edge pipeline or start containers to view real-time charts).")

# Telemetry raw log table
with st.expander("📋 View Raw Edge Telemetry Feed"):
    if history:
        st.dataframe(pd.DataFrame(history))
    else:
        st.write("No rollups received yet.")

if auto_refresh:
    time.sleep(5)
    st.rerun()

