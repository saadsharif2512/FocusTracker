import streamlit as st
import cv2
import time
import pandas as pd
import os
from focus_detector import FocusDetector

# ──────────────── ENVIRONMENT CHECK ────────────────
def is_cloud():
    return os.environ.get("HOME", "") == "/home/adminuser"

# ──────────────── PAGE SETTINGS ────────────────
st.set_page_config(page_title="Focus Session Tracker", layout="wide")

if "log" not in st.session_state or not isinstance(st.session_state.log, list):
    st.session_state.log = []

# --- CSS Styling ---
st.markdown("""
    <style>
    .big-font {
        font-size:24px !important;
        font-weight:600;
    }
    .metric-box {
        padding: 1rem;
        background-color: #f0f2f6;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- To-Do List Initialization ---
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "task_input" not in st.session_state:
    st.session_state.task_input = ""

# --- Timer State Initialization ---
for key, default in {
    "timer_running": False,
    "timer_start": None,
    "session_duration": 0,
    "break_duration": 0,
    "break_start": None,
    "tracking": False,
    "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.caption(f"🕒 Session started at {st.session_state.start_time}")
st.title("🎯 Focus Tracker")
st.markdown("Track your focus sessions using your webcam and download logs to monitor your productivity.")

detector = FocusDetector()
FRAME_WINDOW = st.empty()

# ─────────────────── SIDEBAR ───────────────────
with st.sidebar:
    st.header("🎛️ Controls")

    run_button_label = "▶️ Run" if not st.session_state.tracking else "⏹️ Stop"
    if st.button(run_button_label, key="toggle_tracking"):
        st.session_state.tracking = not st.session_state.tracking
        if not st.session_state.tracking:
            st.session_state.end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    if st.button("🔄 Restart Session"):
        for key in ["log", "tracking", "timer_running", "timer_start", "session_duration", "break_duration", "break_start"]:
            st.session_state[key] = False if isinstance(st.session_state[key], bool) else 0
        st.session_state.start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        st.rerun()

    st.markdown("## ⏱️ Timer Controls")

    if not st.session_state.timer_running:
        if st.button("▶️ Start Timer / Resume"):
            st.session_state.timer_running = True
            st.session_state.timer_start = time.time()
            if st.session_state.break_start is not None:
                st.session_state.break_duration += time.time() - st.session_state.break_start
                st.session_state.break_start = None
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⏸️ Pause Timer"):
                st.session_state.timer_running = False
                st.session_state.session_duration += time.time() - st.session_state.timer_start
                st.session_state.timer_start = None
                st.session_state.break_start = time.time()
        with col2:
            if st.button("🛑 Stop Timer"):
                st.session_state.timer_running = False
                if st.session_state.timer_start:
                    st.session_state.session_duration += time.time() - st.session_state.timer_start
                    st.session_state.timer_start = None
                if st.session_state.break_start:
                    st.session_state.break_duration += time.time() - st.session_state.break_start
                    st.session_state.break_start = None
                st.session_state.log.append({
                    "timestamp": time.time(),
                    "status": "🛑 Timer Stopped",
                    "note": f"Stopped at Session: {int(st.session_state.session_duration // 60)}m, Break: {int(st.session_state.break_duration // 60)}m"
                })

    if st.button("🔄 Reset Timer"):
        st.session_state.timer_running = False
        st.session_state.timer_start = None
        st.session_state.session_duration = 0
        st.session_state.break_duration = 0
        st.session_state.break_start = None
        st.rerun()

def add_task():
    task = st.session_state.new_task.strip()
    if task:
        st.session_state.tasks.append(task)
        st.session_state.new_task = ""
    else:
        st.warning("⚠️ Please enter a task.")

with st.expander("📝 To-Do List", expanded=True):
    st.text_input("Add a new task:", key="new_task", on_change=add_task)

    if st.session_state.tasks:
        st.markdown("### Current Tasks")
        remove_idx = None
        for i, task in enumerate(st.session_state.tasks):
            col1, col2, col3 = st.columns([0.8, 0.2, 0.3])
            with col1:
                st.write(f"{i + 1}. {task}")
            with col2:
                if st.button("❌", key=f"remove_{i}"):
                    remove_idx = i
            with col3:
                st.checkbox("✔️", key=f"done_{i}", value=False)
        if remove_idx is not None:
            removed = st.session_state.tasks.pop(remove_idx)
            st.success(f"✔️ Task '{removed}' removed!")
            st.rerun()

# ─────────────────── TIMER DISPLAY ───────────────────
with st.container():
    st.subheader("⏱️ Live timer summary")

    current_time = time.time()
    elapsed_session = st.session_state.session_duration
    elapsed_break = st.session_state.break_duration

    if st.session_state.timer_running and st.session_state.timer_start:
        elapsed_session += current_time - st.session_state.timer_start
    elif st.session_state.break_start:
        elapsed_break += current_time - st.session_state.break_start

    session_min = int(elapsed_session // 60)
    session_sec = int(elapsed_session % 60)
    break_min = int(elapsed_break // 60)
    break_sec = int(elapsed_break % 60)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-box">🟢 Session Time<br><span class="big-font">{session_min} min {session_sec} sec</span></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box">🟡 Break Time<br><span class="big-font">{break_min} min {break_sec} sec</span></div>', unsafe_allow_html=True)

# ─────────────────── CAMERA TRACKING ───────────────────
if st.session_state.tracking:
    if is_cloud():
        st.warning("⚠️ Webcam tracking is not supported in the cloud. Please run this app locally.")
    else:
        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            st.error("❌ Failed to access the camera.")
        else:
            st.success("📹 Tracking is active. Press stop to end.")
            while st.session_state.tracking:
                ret, frame = cam.read()
                if not ret:
                    st.error("❌ Camera read failed.")
                    break

                frame = cv2.flip(frame, 1)
                focused = detector.is_focused(frame)
                status = "🟢 Focused" if focused else "🔴 Distracted"

                st.session_state.log.append({
                    "timestamp": time.time(),
                    "status": status
                })

                cv2.putText(frame, status, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1,
                            (0, 255, 0) if focused else (0, 0, 255), 2)

                FRAME_WINDOW.image(frame, channels="BGR")
                time.sleep(0.1)
            cam.release()

# ─────────────────── SAVE TIMER LOG ───────────────────
with st.container():
    st.markdown("## 💾 Save Timer Data to Log")
    if st.button("✅ Save Timer Data"):
        st.session_state.log.append({
            "timestamp": time.time(),
            "status": "⏱️ Timer Log",
            "note": f"Session: {session_min}m {session_sec}s, Break: {break_min}m {break_sec}s"
        })
        st.success("✔️ Timer log saved!")

# ─────────────────── LOG & METRICS ───────────────────
with st.container():
    st.subheader("📄 Current Log Data")
    st.write(st.session_state.log)

    if st.session_state.log:
        focus_entries = [entry for entry in st.session_state.log if entry.get("status") in ["🟢 Focused", "🔴 Distracted"]]
        if focus_entries:
            total = len(focus_entries)
            focused_count = sum(1 for entry in focus_entries if entry["status"] == "🟢 Focused")
            focus_score = (focused_count / total) * 100
            st.metric("🎯 Focus Score", f"{focus_score:.2f}%")

# ─────────────────── DOWNLOAD LOG ───────────────────
with st.container():
    st.markdown("## 📥 Download Focus Log")
    if st.button("⬇️ Download CSV"):
        if st.session_state.log and "timestamp" in st.session_state.log[0]:
            df = pd.DataFrame(st.session_state.log)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s', errors='coerce')
            st.download_button("📄 Download CSV", df.to_csv(index=False), file_name="focus_log.csv")
        else:
            st.warning("⚠️ No valid log data available.")

# ─────────────────── READABLE SUMMARY ───────────────────
with st.container():
    if st.session_state.log:
        st.subheader("📝 Readable Log Summary")
        for entry in reversed(st.session_state.log[-100:]):
            readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry["timestamp"]))
            note = entry.get("note", "")
            st.markdown(f"- {readable_time} — {entry['status']} {'– ' + note if note else ''}")

# ─────────────────── END TIME ───────────────────
if not st.session_state.tracking and "end_time" in st.session_state:
    st.caption(f"🕒 Session ended at {st.session_state.end_time}")
