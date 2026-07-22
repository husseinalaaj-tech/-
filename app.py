import streamlit as st
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- Page Config ----------
st.set_page_config(
    page_title="Network Simulation Engine",
    page_icon="⚡",
    layout="wide"
)

# ---------- Custom CSS ----------
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    .main-header {
        font-size: 2.3rem;
        color: #3b82f6;
        text-align: center;
        font-weight: 800;
    }
    .success-box {
        background-color: #0d2818;
        border: 1px solid #107C10;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        font-family: monospace;
    }
    .failed-box {
        background-color: #2b1111;
        border: 1px solid #7c1010;
        padding: 8px;
        border-radius: 6px;
        margin-bottom: 6px;
        font-size: 0.9rem;
        font-family: monospace;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>⚡ Multi-Region Network & Data Simulation Engine</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af;'>Distributed performance testing and asynchronous payload verification tool.</p>", unsafe_allow_html=True)
st.markdown("---")

# ---------- Sidebar Configuration ----------
with st.sidebar:
    st.header("⚙️ Engine Configuration")
    total_attempts = st.slider("Total Payload Iterations:", 50, 2000, 200, 50)
    concurrency_threads = st.slider("Concurrent Threads (Workers):", 5, 40, 15)
    selected_nodes = st.multiselect(
        "Select Target Routing Nodes:",
        ["🇺🇸 US-Cluster-Alpha", "🇪🇺 EU-Cluster-Beta", "🇦🇪 ME-Gateway-East", "🇬🇧 UK-Node-Primary"],
        default=["🇺🇸 US-Cluster-Alpha", "🇪🇺 EU-Cluster-Beta", "🇦🇪 ME-Gateway-East"]
    )

VALID_CHARS = "BCDFGHJKMNPQRVWXYZ2346789"

def generate_payload_token():
    return "-".join(["".join(random.choices(VALID_CHARS, k=5)) for _ in range(5)])

# ---------- Session State Initialization ----------
if "simulation_running" not in st.session_state:
    st.session_state.simulation_running = False
if "progress" not in st.session_state:
    st.session_state.progress = {
        "checked": 0,
        "success": 0,
        "speed": 0,
        "accepted": [],
        "failed": [],
        "start_time": None,
        "finished": False,
        "duration": 0
    }
if "worker_thread" not in st.session_state:
    st.session_state.worker_thread = None

# ---------- Background Simulation Runner ----------
def run_simulation(total, workers, nodes):
    st.session_state.progress = {
        "checked": 0,
        "success": 0,
        "speed": 0,
        "accepted": [],
        "failed": [],
        "start_time": time.time(),
        "finished": False,
        "duration": 0
    }

    def worker(token):
        try:
            node = random.choice(nodes)
            latency = random.randint(120, 480)
            time.sleep(random.uniform(0.01, 0.03))
            is_valid = (random.random() < 0.015)
            return token, node, latency, is_valid
        except Exception as e:
            return token, "UNKNOWN", 0, f"THREAD_ERROR: {e}"

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(worker, generate_payload_token()) for _ in range(total)]
            for future in as_completed(futures):
                try:
                    token, node, latency, result = future.result()
                except Exception as e:
                    token = "ERR_TOKEN"
                    node = "UNKNOWN"
                    latency = 0
                    result = f"FUTURE_ERROR: {e}"

                p = st.session_state.progress
                p["checked"] += 1
                elapsed = time.time() - p["start_time"]
                p["speed"] = int(p["checked"] / elapsed) if elapsed > 0 else 0

                if isinstance(result, bool) and result is True:
                    p["success"] += 1
                    record = f"🔑 **{token}**<br>• Node: {node}<br>• Latency: {latency}ms<br>• Status: Verified ✅"
                    p["accepted"].insert(0, record)
                    if len(p["accepted"]) > 8:
                        p["accepted"] = p["accepted"][:8]
                else:
                    error_info = result if isinstance(result, str) else "Dropped ❌"
                    record = f"🔒 `{token}` | {node} | {latency}ms | {error_info}"
                    p["failed"].insert(0, record)
                    if len(p["failed"]) > 10:
                        p["failed"] = p["failed"][:10]

        st.session_state.progress["finished"] = True
        st.session_state.progress["duration"] = round(time.time() - st.session_state.progress["start_time"], 2)

    except Exception as e:
        st.session_state.progress["finished"] = True
        st.session_state.progress["failed"].insert(0, f"💥 SIMULATION CRASH: {e}")

    finally:
        st.session_state.simulation_running = False

# ---------- Start Button ----------
if st.button("🚀 Initialize Distributed Execution", use_container_width=True):
    if not selected_nodes:
        st.warning("⚠️ Please select at least one routing node.")
    elif st.session_state.simulation_running:
        st.warning("A simulation is already running. Wait for it to finish.")
    else:
        st.session_state.simulation_running = True
        t = threading.Thread(
            target=run_simulation,
            args=(total_attempts, concurrency_threads, selected_nodes),
            daemon=True
        )
        st.session_state.worker_thread = t
        t.start()

# ---------- UI Display ----------
p = st.session_state.progress

st.markdown("### 📊 Real-time Execution Telemetry")
m1, m2, m3, m4 = st.columns(4)
m1.metric("🎯 Target Iterations", total_attempts)
m2.metric("🔄 Processed", f"{p['checked']}/{total_attempts}" if not p['finished'] else f"{total_attempts}/{total_attempts}")
m3.metric("🏆 Validated Hits", p["success"])
m4.metric("⚡ Throughput", f"{p['speed']} req/sec")

st.markdown("---")
st.subheader("📋 Stream Execution Logs:")
col_success, col_failed = st.columns(2)

with col_success:
    st.markdown("### ✅ Validated / Successful Payloads")
    if p["accepted"]:
        html = "".join([f"<div class='success-box'>{item}</div>" for item in p["accepted"]])
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown("<p style='color: #6b7280;'>Awaiting verified payloads...</p>", unsafe_allow_html=True)

with col_failed:
    st.markdown("### ❌ Rejected / Dropped Payloads")
    if p["failed"]:
        html = "".join([f"<div class='failed-box'>{item}</div>" for item in p["failed"]])
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown("<p style='color: #6b7280;'>No dropped records displayed.</p>", unsafe_allow_html=True)

# ---------- Completion Message ----------
if p["finished"]:
    st.success(f"🏁 Execution cycle completed in {p['duration']} seconds. Total validated hits: {p['success']}")
    if p["success"] > 0:
        st.balloons()
    st.session_state.simulation_running = False

# ---------- Auto-rerun while simulation is active ----------
if st.session_state.simulation_running and not p["finished"]:
    time.sleep(0.2)
    st.rerun()
