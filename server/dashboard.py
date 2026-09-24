import html
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import streamlit as st

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
# Browser-facing address for the MJPEG stream / snapshot <img> tags (may differ from API_BASE inside Docker)
PUBLIC_API_BASE = os.environ.get("PUBLIC_API_BASE_URL", "http://localhost:8000")
AUTO_REFRESH_DEFAULT = os.environ.get("DASHBOARD_AUTO_REFRESH", "1") == "1"
API_KEY = os.environ.get("EDGESIGHT_API_KEY")  # only needed if the API enforces it (see server/app.py)

st.set_page_config(
    page_title="AD Labs EdgeSight | Retail Operations",
    page_icon="🏪",
    layout="wide"
)


def api_get(path, params=None, timeout=3.0):
    try:
        resp = requests.get(f"{API_BASE}{path}", params=params, timeout=timeout)
        return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None


def api_post(path, payload, timeout=5.0):
    """Returns (ok, body_or_error_message)."""
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    try:
        resp = requests.post(f"{API_BASE}{path}", json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return True, resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return False, detail if isinstance(detail, str) else str(detail)
    except Exception as e:
        return False, str(e)


def render_traffic_charts(hourly, history):
    """Dark, card-styled Chart.js footfall/occupancy charts + a recent-windows table, matching
    the Calibration Studio's Traffic & People Analytics look -- but fed from this page's own
    already-fetched, auto-refreshing `history`/`hourly` data instead of a separate poll, since
    this dashboard (not the Studio) is the client with real historical telemetry filtering
    (camera + date range) already wired up."""
    hourly_labels = [h["hour"][11:16] for h in hourly]
    hourly_in = [h["visitors"] for h in hourly]
    hourly_out = [h["exits"] for h in hourly]

    occ_labels = [h["timestamp_end"].split(" ")[-1] if " " in h["timestamp_end"] else h["timestamp_end"] for h in history]
    occ_data = [h["current_occupancy"] for h in history]

    table_rows = list(reversed(history[-10:]))

    page_html = f"""
    <div style="background:#0B0F17; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; padding:4px;">
      <style>
        .card {{ background:#131B2A; border:1px solid #23324A; border-radius:12px; padding:18px; }}
        .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
        h4 {{ color:#9CA3AF; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; margin:0 0 12px 0; }}
        table {{ width:100%; border-collapse:collapse; font-size:12px; color:#D1D5DB; }}
        th {{ text-align:left; color:#6B7280; font-size:10.5px; text-transform:uppercase; padding:8px 10px; border-bottom:1px solid #23324A; }}
        td {{ padding:7px 10px; border-bottom:1px solid rgba(35,50,74,.5); }}
        .in {{ color:#10B981; font-weight:700; }} .out {{ color:#6366F1; font-weight:700; }} .occ {{ color:#22D3EE; font-weight:600; }}
      </style>
      <div class="grid2">
        <div class="card"><h4>Hourly Footfall (In vs Out)</h4><div style="height:260px;"><canvas id="chartFootfallDash"></canvas></div></div>
        <div class="card"><h4>Store Occupancy Over Time</h4><div style="height:260px;"><canvas id="chartOccDash"></canvas></div></div>
      </div>
      <div class="card" style="margin-top:18px;">
        <h4>Recent 10-Second Telemetry Windows</h4>
        <table>
          <thead><tr><th>Timestamp Window</th><th>Entries (+IN)</th><th>Exits (-OUT)</th><th>Occupancy</th><th>Avg Dwell</th></tr></thead>
          <tbody>
            {"".join(f"<tr><td>{html.escape(str(r['timestamp_end']))}</td><td class='in'>+{r['in_count']}</td><td class='out'>-{r['out_count']}</td><td class='occ'>{r['current_occupancy']}</td><td>{r['avg_dwell_seconds']:.1f}s</td></tr>" for r in table_rows) or "<tr><td colspan='5' style='text-align:center;color:#6B7280;padding:16px;'>No rollups yet</td></tr>"}
          </tbody>
        </table>
      </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
      const axisOpts = {{ ticks: {{ color: '#6B7280' }}, grid: {{ color: '#1F2937' }} }};
      new Chart(document.getElementById('chartFootfallDash'), {{
        type: 'bar',
        data: {{
          labels: {json.dumps(hourly_labels)},
          datasets: [
            {{ label: 'In (Entries)', data: {json.dumps(hourly_in)}, backgroundColor: '#10B981' }},
            {{ label: 'Out (Exits)', data: {json.dumps(hourly_out)}, backgroundColor: '#6366F1' }}
          ]
        }},
        options: {{ responsive: true, maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#9CA3AF' }} }} }},
          scales: {{ x: axisOpts, y: axisOpts }} }}
      }});
      new Chart(document.getElementById('chartOccDash'), {{
        type: 'line',
        data: {{ labels: {json.dumps(occ_labels)}, datasets: [{{
          label: 'Net In-Store Shoppers', data: {json.dumps(occ_data)},
          borderColor: '#22D3EE', backgroundColor: 'rgba(34, 211, 238, 0.1)', fill: true, tension: 0.3
        }}] }},
        options: {{ responsive: true, maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#9CA3AF' }} }} }},
          scales: {{ x: axisOpts, y: axisOpts }} }}
      }});
    </script>
    """
    st.iframe(page_html, height=620)


st.title("🏪 AD Labs EdgeSight — Store Intelligence Dashboard")
st.caption("On-Premise Computer Vision Telemetry & In-Store Operational Analytics · all timestamps are UTC")

# ----------------------------------------------------------------------------
# Sidebar: store, camera and date filters
# ----------------------------------------------------------------------------
config = api_get("/api/v1/config/cameras") or {"cameras": []}
cameras = {c["id"]: c for c in config.get("cameras", []) if c.get("id")}

with st.sidebar:
    st.header("⚙️ Store Controls")
    store_id = st.text_input("Store Identifier", value="store_mumbai_001")

    camera_choice = st.selectbox("Camera", ["All cameras"] + list(cameras), key="camera_filter")
    camera_filter = None if camera_choice == "All cameras" else camera_choice

    today_utc = datetime.now(timezone.utc).date()
    picked = st.date_input(
        "Date range (UTC)",
        value=(today_utc - timedelta(days=6), today_utc),
        max_value=today_utc,
        key="date_range",
    )
    if isinstance(picked, (tuple, list)):
        start_date = picked[0]
        end_date = picked[1] if len(picked) > 1 else picked[0]
    else:
        start_date = end_date = picked

    auto_refresh = st.checkbox("Auto Refresh (every 5s)", value=AUTO_REFRESH_DEFAULT)
    st.markdown("---")
    st.markdown(f"[🎯 Open Calibration Studio (click-to-draw)]({PUBLIC_API_BASE}/)")
    st.info("Pure Vision-Based Analytics — No POS or external sensor integration required.")

scope = {"store_id": store_id}
if camera_filter:
    scope["camera_id"] = camera_filter
range_scope = {**scope, "start_date": start_date.isoformat(), "end_date": end_date.isoformat()}

data = api_get("/api/v1/live", params=scope)
if data is None:
    data = {}
    st.warning(f"Connecting to Edge API at {API_BASE}...")

summary = api_get("/api/v1/analytics/summary", params=range_scope) or {}

# ----------------------------------------------------------------------------
# Live metrics
# ----------------------------------------------------------------------------
if data.get("queue_alert_active"):
    st.error(
        f"🚨 **CHECKOUT CONGESTION ALERT**: Register queue exceeds comfortable SLA! "
        f"Queue: {data.get('queue_length')} people waiting (~{int(data.get('avg_queue_wait_seconds', 0))}s wait time). "
        f"Please dispatch an additional cashier."
    )

st.subheader("🔴 Live — right now" + (f" · {camera_filter}" if camera_filter else " · all cameras"))
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🚶 Visitors Today", data.get("total_visitors", 0),
              help="Tripwire entries if a tripwire is configured; otherwise unique tracker IDs (over-counts when IDs churn)")
with col2:
    st.metric("🏬 People In View", data.get("net_occupancy", 0),
              help="Live tracked people (tripwire entries minus exits when a tripwire is configured)")
with col3:
    queue_len = data.get("queue_length", 0)
    avg_wait = int(data.get("avg_queue_wait_seconds", 0))
    st.metric("⏳ Cashier Queue Length", f"{queue_len} people", delta=f"{avg_wait}s avg wait",
              delta_color="inverse" if queue_len > 4 else "normal",
              help="Requires a 'queue' zone to be drawn for the camera (Camera Setup tab)")
with col4:
    st.metric("⏱️ Avg Store Dwell", f"{data.get('avg_dwell_seconds', 0.0)}s",
              delta=f"{data.get('total_exits', 0)} total exits recorded")

st.subheader(f"📅 Historical — {start_date} → {end_date} (UTC)")
h1, h2, h3, h4 = st.columns(4)
peak = summary.get("peak_period")
with h1:
    st.metric("📈 Peak Traffic Hour", peak["hour"][11:16] if peak else "—",
              delta=f"{peak['visitors']} visitors" if peak else None, delta_color="off",
              help=peak["hour"] if peak else "No traffic in this range")
with h2:
    st.metric("📊 Avg Visitors / Hour", summary.get("avg_visitors_per_hour", 0.0))
with h3:
    st.metric("🚶 Visitors in Range", summary.get("total_visitors", 0))
with h4:
    st.metric("🚪 Exits in Range", summary.get("total_exits", 0))

st.markdown("---")

tab_live, tab_traffic, tab_events, tab_setup = st.tabs(
    ["🎥 Live Vision", "📊 Traffic Analytics", "🧾 Crossing Events", "⚙️ Camera Setup"]
)

# ----------------------------------------------------------------------------
# Live vision
# ----------------------------------------------------------------------------
with tab_live:
    stream_cam = camera_filter or (next(iter(cameras)) if cameras else "cam_entrance_01")
    live_col, legend_col = st.columns([3, 1])
    with live_col:
        st.caption(f"Live inference stream for **{stream_cam}** — YOLO detections, tracker IDs, tripwires and zones.")
        st.markdown(
            f"""
            <div style="background-color: #121212; padding: 6px; border-radius: 10px; text-align: center; border: 1px solid #2a2a2a;">
                <img src="{PUBLIC_API_BASE}/api/v1/stream/{stream_cam}" style="width: 100%; border-radius: 8px; display: block;" alt="Live Model Inference Stream"/>
            </div>
            """,
            unsafe_allow_html=True
        )
    with legend_col:
        current = cameras.get(stream_cam, {})
        st.markdown("#### 📷 Current source")
        st.code(current.get("source", "unknown"), language=None)
        st.markdown("#### 🔍 Visual Legend")
        st.markdown("""
        * 🟩 **Green Line:** Entrance Tripwire (Counts In / Out)
        * 🟨 **Yellow Box:** Detected Person + Track ID
        * 🔴 **Red Contact Point:** Ground Foot Coordinate
        * 🟨 **Yellow Polygon:** Merchandising Dwell Zone
        * 🟦 **Cyan Polygon:** Cashier Queue Staging Area
        """)
        st.info("Frames are decoded, inferred, and rendered entirely on the on-premise edge node.")

# ----------------------------------------------------------------------------
# Traffic analytics
# ----------------------------------------------------------------------------
history = api_get("/api/v1/history", params={**range_scope, "limit": 500}) or []

with tab_traffic:
    hourly = summary.get("hourly_breakdown", [])
    if not hourly and not history:
        st.info("No rollups in the selected date range / camera yet.")
    else:
        render_traffic_charts(hourly, history)

        st.subheader("⏱️ Checkout Queue Congestion Trend")
        if history:
            df = pd.DataFrame(history)
            st.line_chart(df.set_index("timestamp_end")[["queue_length", "avg_queue_wait_seconds"]])
            with st.expander("📋 View Raw Edge Telemetry Feed"):
                st.dataframe(df)
                st.download_button("Download CSV", df.to_csv(index=False), file_name="edgesight_rollups.csv", mime="text/csv")

# ----------------------------------------------------------------------------
# Crossing events
# ----------------------------------------------------------------------------
with tab_events:
    events = (api_get("/api/v1/events", params={**scope, "limit": 200}) or {}).get("events", [])
    if events:
        st.caption("Every individual tripwire crossing, independent of the 10s rollups.")
        st.dataframe(pd.DataFrame(events).iloc[::-1])
    else:
        has_tripwire = any(c.get("tripwires") for c in cameras.values())
        if has_tripwire:
            st.info("No crossings recorded yet.")
        else:
            st.warning(
                "No tripwire is configured, so no crossing events exist and 'visitors' falls back to counting unique "
                "tracker IDs. Draw one in the **Camera Setup** tab."
            )

# ----------------------------------------------------------------------------
# Camera setup: source switching + calibration
# ----------------------------------------------------------------------------
with tab_setup:
    if not cameras:
        st.warning("No cameras found in configs/cameras.yaml (or the API is unreachable).")
    else:
        setup_cam = st.selectbox("Camera to configure", list(cameras), key="setup_cam")
        cam_cfg = cameras[setup_cam]

        st.subheader("📼 Video source")
        st.caption(
            "Switch this camera between sample videos and a live RTSP stream. The edge analyzer picks the change up "
            "within a few seconds and starts this camera with a fresh tracker and counters."
        )
        sources = api_get("/api/v1/config/sources") or {"videos": []}
        videos = sources.get("videos", [])
        current_source = cam_cfg.get("source", "")

        with st.form(f"source_form_{setup_cam}"):
            mode = st.radio("Source type", ["Video file", "RTSP / stream URL"],
                            index=0 if current_source in videos else 1, horizontal=True, key=f"src_mode_{setup_cam}")
            file_choice = st.selectbox(
                "Video file", videos,
                index=videos.index(current_source) if current_source in videos else 0,
                disabled=not videos,
                key=f"src_file_{setup_cam}",
            )
            url_choice = st.text_input(
                "RTSP / stream URL",
                value="" if current_source in videos else current_source,
                placeholder="rtsp://user:password@192.168.1.100:554/Streaming/Channels/102",
                key=f"src_url_{setup_cam}",
            )
            fps_choice = st.number_input("Target FPS", min_value=1, max_value=60, value=int(cam_cfg.get("fps_target", 15)),
                                         key=f"src_fps_{setup_cam}")
            apply_source = st.form_submit_button("Apply source")

        if apply_source:
            new_source = file_choice if mode == "Video file" else url_choice.strip()
            ok, result = api_post(
                f"/api/v1/config/cameras/{setup_cam}/source",
                {"source": new_source, "fps_target": int(fps_choice)},
            )
            if ok:
                st.toast(f"{setup_cam} → {new_source}", icon="✅")
                st.success(f"Source updated to `{new_source}`. The edge will switch within ~3 seconds.")
            else:
                st.error(f"Could not update source: {result}")

        st.markdown("---")
        st.subheader("📐 Tripwires & zones")
        st.caption(
            "Read-only here. Tripwires drive real entry/exit counts; a **queue** zone is what populates queue length "
            "and wait time. Draw and edit both with the click-to-draw **Calibration Studio** — it's the single place "
            "these are created or removed, so this view and the Studio never disagree about what's live."
        )
        st.link_button("🎯 Open Calibration Studio", f"{PUBLIC_API_BASE}/", use_container_width=False)

        tripwires = list(cam_cfg.get("tripwires", []))
        zones = list(cam_cfg.get("zones", []))
        if tripwires:
            st.markdown("**Tripwires**")
            st.dataframe(pd.DataFrame(tripwires))
        if zones:
            st.markdown("**Zones**")
            st.dataframe(pd.DataFrame(zones))
        if not tripwires and not zones:
            st.info("No tripwires or zones configured for this camera yet — add them in the Calibration Studio.")

if auto_refresh:
    time.sleep(5)
    st.rerun()
