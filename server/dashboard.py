import io
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import streamlit as st
from PIL import Image, ImageDraw

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
# Browser-facing address for the MJPEG stream / snapshot <img> tags (may differ from API_BASE inside Docker)
PUBLIC_API_BASE = os.environ.get("PUBLIC_API_BASE_URL", "http://localhost:8000")
AUTO_REFRESH_DEFAULT = os.environ.get("DASHBOARD_AUTO_REFRESH", "1") == "1"

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
    try:
        resp = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        if resp.status_code == 200:
            return True, resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return False, detail if isinstance(detail, str) else str(detail)
    except Exception as e:
        return False, str(e)


def parse_polygon(text):
    """'100,200 300,200 300,400' -> [[100.0, 200.0], ...]; raises ValueError on bad input."""
    points = []
    for token in text.replace(";", " ").split():
        x, y = token.split(",")
        points.append([float(x), float(y)])
    if len(points) < 3:
        raise ValueError("A zone needs at least three x,y points")
    return points


def snapshot_with_grid(camera_id, step=100):
    """Latest annotated frame with a labelled pixel grid, so tripwire/zone coordinates can be read off it."""
    try:
        resp = requests.get(f"{API_BASE}/api/v1/snapshot/{camera_id}", timeout=3.0)
        if resp.status_code != 200:
            return None
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception:
        return None
    draw = ImageDraw.Draw(img)
    for x in range(0, img.width, step):
        draw.line([(x, 0), (x, img.height)], fill=(255, 255, 255), width=1)
        draw.text((x + 3, 3), str(x), fill=(255, 255, 0))
    for y in range(0, img.height, step):
        draw.line([(0, y), (img.width, y)], fill=(255, 255, 255), width=1)
        draw.text((3, y + 3), str(y), fill=(255, 255, 0))
    return img


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
    if hourly:
        hourly_df = pd.DataFrame(hourly).set_index("hour")
        st.subheader("🕒 Visitors per Hour")
        st.bar_chart(hourly_df[["visitors", "exits"]])
    else:
        st.info("No rollups in the selected date range / camera yet.")

    if history:
        df = pd.DataFrame(history)
        left, right = st.columns(2)
        with left:
            st.subheader("📈 Rollup Footfall (In vs Out)")
            st.bar_chart(df.set_index("timestamp_end")[["in_count", "out_count"]])
        with right:
            st.subheader("⏱️ Checkout Queue Congestion Trend")
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
            "Tripwires drive real entry/exit counts. A **queue** zone is what populates queue length and wait time. "
            "Read pixel coordinates off the gridded frame below (or use the click-to-draw Calibration Studio)."
        )

        grid = snapshot_with_grid(setup_cam)
        if grid is not None:
            st.image(grid, caption=f"Latest frame from {setup_cam} with a 100px coordinate grid")
        else:
            st.info("No frame available yet — is the edge analyzer running?")

        tripwires = list(cam_cfg.get("tripwires", []))
        zones = list(cam_cfg.get("zones", []))
        if tripwires:
            st.markdown("**Tripwires**")
            st.dataframe(pd.DataFrame(tripwires))
        if zones:
            st.markdown("**Zones**")
            st.dataframe(pd.DataFrame(zones))

        existing_ids = [t["id"] for t in tripwires] + [z["id"] for z in zones]
        with st.form(f"remove_form_{setup_cam}"):
            to_remove = st.multiselect("Remove tripwires / zones", existing_ids, key=f"remove_{setup_cam}")
            remove_submit = st.form_submit_button("Remove selected")
        if remove_submit and to_remove:
            ok, result = api_post(f"/api/v1/config/cameras/{setup_cam}/calibration", {
                "tripwires": [t for t in tripwires if t["id"] not in to_remove],
                "zones": [z for z in zones if z["id"] not in to_remove],
            })
            if ok:
                st.success("Removed.")
            else:
                st.error(f"Could not save: {result}")

        add_tw_col, add_zone_col = st.columns(2)
        with add_tw_col:
            with st.form(f"tripwire_form_{setup_cam}"):
                st.markdown("**Add tripwire**")
                tw_id = st.text_input("ID", value="tripwire_door", key=f"tw_id_{setup_cam}")
                c1, c2 = st.columns(2)
                x1 = c1.number_input("x1", value=0.0, key=f"tw_x1_{setup_cam}")
                y1 = c2.number_input("y1", value=0.0, key=f"tw_y1_{setup_cam}")
                x2 = c1.number_input("x2", value=0.0, key=f"tw_x2_{setup_cam}")
                y2 = c2.number_input("y2", value=0.0, key=f"tw_y2_{setup_cam}")
                direction = st.selectbox(
                    "Entering means moving…", ["top_to_bottom", "bottom_to_top"], key=f"tw_dir_{setup_cam}",
                    help="Direction of travel across the line that counts as an ENTRY",
                )
                tw_submit = st.form_submit_button("Add tripwire")
            if tw_submit:
                if (x1, y1) == (x2, y2):
                    st.error("The two points must differ.")
                elif tw_id in existing_ids:
                    st.error(f"'{tw_id}' already exists.")
                else:
                    ok, result = api_post(f"/api/v1/config/cameras/{setup_cam}/calibration", {
                        "tripwires": tripwires + [{"id": tw_id, "name": tw_id, "line": [[x1, y1], [x2, y2]], "in_direction": direction}],
                    })
                    if ok:
                        st.success("Tripwire added.")
                    else:
                        st.error(f"Could not save: {result}")

        with add_zone_col:
            with st.form(f"zone_form_{setup_cam}"):
                st.markdown("**Add zone**")
                zone_id = st.text_input("ID", value="queue_counter", key=f"zone_id_{setup_cam}")
                zone_type = st.selectbox("Type", ["queue", "dwell"], key=f"zone_type_{setup_cam}")
                polygon_text = st.text_input("Polygon points", placeholder="100,200 400,200 400,500 100,500",
                                             help="At least three x,y points, separated by spaces",
                                             key=f"zone_poly_{setup_cam}")
                q1, q2 = st.columns(2)
                max_queue = q1.number_input("Queue alert above (people)", min_value=1, value=4)
                max_wait = q2.number_input("…or wait above (seconds)", min_value=1.0, value=120.0)
                zone_submit = st.form_submit_button("Add zone")
            if zone_submit:
                try:
                    polygon = parse_polygon(polygon_text)
                except ValueError as e:
                    st.error(f"Invalid polygon: {e}")
                else:
                    if zone_id in existing_ids:
                        st.error(f"'{zone_id}' already exists.")
                    else:
                        new_zone = {"id": zone_id, "name": zone_id, "polygon": polygon, "type": zone_type}
                        if zone_type == "queue":
                            new_zone["max_comfortable_queue"] = int(max_queue)
                            new_zone["congestion_threshold_seconds"] = float(max_wait)
                        ok, result = api_post(f"/api/v1/config/cameras/{setup_cam}/calibration", {"zones": zones + [new_zone]})
                        if ok:
                            st.success("Zone added.")
                        else:
                            st.error(f"Could not save: {result}")

if auto_refresh:
    time.sleep(5)
    st.rerun()
