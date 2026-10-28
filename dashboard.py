import html
import os
import random
import sqlite3
from contextlib import closing
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="VitalNode | Smart ER Triage",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Constants ----------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SmartHospital.db")
DOCTOR_PIN = "2026"
ER_CAPACITY = 30  # total ER beds, used by the capacity gauge

BLUE, TEXT, GRID = "#0F4C81", "#0B1F3A", "#E2E8F0"
STATUSES = ["Waiting", "In Treatment", "Admitted", "Discharged"]
ACTIVE_STATUSES = ["Waiting", "In Treatment", "Admitted"]
SEV_NAME = {1: "Non-urgent", 2: "Minor", 3: "Urgent", 4: "Critical", 5: "Resuscitation"}
SEV_COLOR = {1: "#16A34A", 2: "#65A30D", 3: "#D97706", 4: "#EA580C", 5: "#DC2626"}

MENU = [
    "Live Command Center",
    "Rapid Emergency Intake",
    "Rapid Response Team",
    "Active ER Monitor",
    "Bottleneck Analytics",
    "Secure Master Records",
]
ROLES = ["System Admin", "Doctor", "Front Desk Receptionist"]
ACCESS = {  # which menu pages each role may open
    "System Admin": set(MENU),
    "Doctor": set(MENU),  # Master Records additionally needs the PIN
    "Front Desk Receptionist": {
        "Live Command Center", "Rapid Emergency Intake", "Active ER Monitor",
    },
}
DOCTORS = ["Dr. Meera Iyer", "Dr. Arjun Rao", "Dr. Sana Khan", "Dr. Vikram Sethi"]
NURSES = ["Nurse Priya", "Nurse John", "Nurse Fatima", "Nurse Ravi"]

# ---------- Session state (staff assignments, vitals, notes, files) ----------
for _key, _default in {
    "assignments": {},  # patient id -> {"doctor", "nurse", "time"}
    "vitals": {},       # patient id -> [{"time", "hr"}]
    "notes": {},        # patient id -> [{"time", "by", "text"}]
    "contacts": {},     # patient id -> [{"name", "relation", "phone"}]
    "files": {},        # patient id -> [{"name", "size"}]
}.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default

# ---------- Custom CSS: unified light SaaS theme + premium watermarks ----------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, button, input, textarea, select { font-family: 'Inter', sans-serif !important; }
.stApp { background: #F8FAFC; color: #0B1F3A; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.5rem; max-width: 1300px; }
h1, h2, h3, h4 { color: #0B1F3A; font-weight: 700; letter-spacing: -0.01em; }

/* ===== MAIN AREA WATERMARK: faint heartbeat line, medical crosses and nodes (~4.5% opacity) ===== */
[data-testid="stAppViewContainer"] {
    background-color: #F8FAFC;
    background-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='640' height='640' viewBox='0 0 640 640' fill='none' stroke='%230F4C81' stroke-opacity='0.045' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M0 320 H200 L228 320 L246 262 L270 392 L296 232 L318 320 H345 L360 296 L376 320 H640'/%3E%3Cg stroke-width='3'%3E%3Cpath d='M96 96 v44 M74 118 h44'/%3E%3Cpath d='M508 486 v44 M486 508 h44'/%3E%3C/g%3E%3Cpath d='M440 90 L520 140 L580 80 M520 140 L540 210'/%3E%3Ccircle cx='440' cy='90' r='6' fill='%230F4C81' fill-opacity='0.045' stroke='none'/%3E%3Ccircle cx='520' cy='140' r='6' fill='%230F4C81' fill-opacity='0.045' stroke='none'/%3E%3Ccircle cx='580' cy='80' r='6' fill='%230F4C81' fill-opacity='0.045' stroke='none'/%3E%3Ccircle cx='540' cy='210' r='6' fill='%230F4C81' fill-opacity='0.045' stroke='none'/%3E%3Cpath d='M70 500 L150 550 L210 490 M150 550 L170 600'/%3E%3Ccircle cx='70' cy='500' r='6' fill='%230F4C81' fill-opacity='0.045' stroke='none'/%3E%3Ccircle cx='150' cy='550' r='6' fill='%230F4C81' fill-opacity='0.045' stroke='none'/%3E%3Ccircle cx='210' cy='490' r='6' fill='%230F4C81' fill-opacity='0.045' stroke='none'/%3E%3Ccircle cx='170' cy='600' r='6' fill='%230F4C81' fill-opacity='0.045' stroke='none'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 640px 640px;
    background-attachment: fixed;
}

/* Sidebar: crisp white base + faint geometric tech-node watermark (~5% opacity) */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    background-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140' viewBox='0 0 140 140' fill='none' stroke='%231E7BC6' stroke-opacity='0.05' stroke-width='1.5' stroke-linejoin='round'%3E%3Cpolygon points='100,70 85,96 55,96 40,70 55,44 85,44'/%3E%3Cpath d='M100 70 L140 70 M40 70 L0 70 M85 96 L105 130 M55 96 L35 130 M55 44 L35 10 M85 44 L105 10'/%3E%3Ccircle cx='70' cy='70' r='4' fill='%231E7BC6' fill-opacity='0.05' stroke='none'/%3E%3Ccircle cx='100' cy='70' r='3' fill='%231E7BC6' fill-opacity='0.05' stroke='none'/%3E%3Ccircle cx='40' cy='70' r='3' fill='%231E7BC6' fill-opacity='0.05' stroke='none'/%3E%3Ccircle cx='85' cy='96' r='3' fill='%231E7BC6' fill-opacity='0.05' stroke='none'/%3E%3Ccircle cx='55' cy='96' r='3' fill='%231E7BC6' fill-opacity='0.05' stroke='none'/%3E%3Ccircle cx='55' cy='44' r='3' fill='%231E7BC6' fill-opacity='0.05' stroke='none'/%3E%3Ccircle cx='85' cy='44' r='3' fill='%231E7BC6' fill-opacity='0.05' stroke='none'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 140px 140px;
    background-attachment: fixed;
    border-right: 1px solid #E2E8F0;
}
[data-testid="stSidebarContent"] { background: transparent !important; }
section[data-testid="stSidebar"] label p { color: #0B1F3A; font-weight: 600; }

/* Metric cards: white, 12px radius, soft shadow, blue left border */
[data-testid="stMetric"] {
    background: #FFFFFF; border-radius: 12px; border-left: 5px solid #0F4C81;
    padding: 16px 18px; box-shadow: 0 4px 16px rgba(15, 76, 129, 0.08);
}
[data-testid="stMetricLabel"] p { color: #64748B; font-weight: 600; font-size: 0.78rem;
    text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { color: #0F4C81; font-weight: 800; }

/* Form containers */
[data-testid="stForm"] {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;
    padding: 20px; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
}

/* Multiselect tags: medical blue instead of Streamlit red/salmon */
span[data-baseweb="tag"] { background-color: #0F4C81 !important; color: #FFFFFF !important; border-radius: 6px !important; }
span[data-baseweb="tag"] span, span[data-baseweb="tag"] svg { color: #FFFFFF !important; fill: #FFFFFF !important; }

/* Inputs */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, div[data-baseweb="textarea"] {
    background: #FFFFFF !important; border-color: #CBD5E1 !important; border-radius: 8px !important;
}
div[data-baseweb="slider"] div[role="slider"] { background-color: #0F4C81 !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #0F4C81 !important; }
div[data-baseweb="tab-highlight"] { background-color: #0F4C81 !important; }

/* Buttons */
.stButton > button, .stFormSubmitButton > button {
    background: #0F4C81; color: #FFFFFF; border: none; border-radius: 8px;
    font-weight: 600; padding: 0.55rem 1.2rem; box-shadow: 0 2px 8px rgba(15, 76, 129, 0.25);
}
.stButton > button p, .stFormSubmitButton > button p { color: #FFFFFF !important; }
.stButton > button:hover, .stFormSubmitButton > button:hover { background: #0B3A66; color: #FFFFFF; }

/* Custom components */
.hero { background: linear-gradient(135deg, #0F4C81 0%, #1E7BC6 100%); color: #FFFFFF;
    border-radius: 14px; padding: 22px 28px; margin-bottom: 20px;
    box-shadow: 0 8px 24px rgba(15, 76, 129, 0.22); }
.hero h2 { color: #FFFFFF; margin: 0; font-size: 1.6rem; }
.hero p { color: #DBEAFE; margin: 4px 0 0 0; font-size: 0.92rem; }
.badge { background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px;
    padding: 10px 14px; color: #0F4C81; font-weight: 600; font-size: 0.9rem; margin: 6px 0 14px 0; }
.secure { background: #0B1F3A; color: #FFFFFF; border-radius: 12px; padding: 22px; margin-bottom: 14px; }
.secure h3 { color: #FFFFFF; margin: 0 0 6px 0; }
.secure p { color: #CBD5E1; margin: 0; }
.idcard { background: #FFFFFF; border-radius: 14px; border: 1px solid #E2E8F0; padding: 20px 24px;
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08); margin: 12px 0 18px 0; }
.idcard .pname { font-size: 1.35rem; font-weight: 800; color: #0B1F3A; }
.idcard .meta { color: #64748B; font-size: 0.85rem; }
.idcard .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 14px; }
.idcard .cell { background: #F8FAFC; border-radius: 10px; padding: 10px 12px; }
.idcard .cell span { display: block; color: #64748B; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; }
.idcard .cell b { color: #0B1F3A; }
.sevpill { display: inline-block; color: #FFFFFF; border-radius: 999px; padding: 3px 12px; font-size: 0.78rem; font-weight: 700; }
</style>
    """,
    unsafe_allow_html=True,
)

# =====================================================================
# PART 2 - Database helpers and chart styling
# =====================================================================
_NEW_API = tuple(int(p) for p in st.__version__.split(".")[:2] if p.isdigit()) >= (1, 50)

def show_plot(fig, key=None):
    if _NEW_API:
        st.plotly_chart(fig, width="stretch", key=key)
    else:
        st.plotly_chart(fig, use_container_width=True, key=key)

def show_table(df):
    try:
        if _NEW_API:
            st.dataframe(df, hide_index=True, width="stretch")
            return
    except TypeError:
        pass
    st.dataframe(df, hide_index=True, use_container_width=True)

def style_fig(fig, title=None, height=360):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=TEXT, size=13),
        margin=dict(l=20, r=20, t=60 if title else 30, b=20),
        height=height,
        legend=dict(font=dict(color=TEXT)),
    )
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=16, color=TEXT)))
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, tickfont=dict(color=TEXT))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, tickfont=dict(color=TEXT))
    return fig

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_conn():
    return sqlite3.connect(DB_PATH)

def table_columns(conn):
    return {r[1].lower(): r[1] for r in conn.execute("PRAGMA table_info(patients)")}

def insert_patient(name, symptoms, severity, status, timestamp, ward=None):
    with closing(get_conn()) as conn:
        cols = table_columns(conn)
        fields = [("name", name), ("symptoms", symptoms), ("severity", severity),
                  ("status", status), ("timestamp", timestamp)]
        if ward and "ward" in cols:
            fields.append(("ward", ward))
        names = ", ".join(cols[k] for k, _ in fields)
        marks = ", ".join("?" for _ in fields)
        cur = conn.execute(f"INSERT INTO patients ({names}) VALUES ({marks})", [v for _, v in fields])
        conn.commit()
        return cur.lastrowid

def guess_ward(symptoms):
    s = str(symptoms).lower()
    if any(k in s for k in ("chest", "heart", "cardiac", "palpitation")):
        return "Cardiology"
    if any(k in s for k in ("head", "stroke", "seizure", "faint", "unconscious")):
        return "Neurology"
    if any(k in s for k in ("fracture", "bleed", "accident", "burn", "wound", "trauma")):
        return "Trauma"
    if any(k in s for k in ("breath", "asthma", "cough", "lung")):
        return "Pulmonology"
    return "General Medicine"

def init_db():
    with closing(get_conn()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS patients (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT NOT NULL, Symptoms TEXT, Severity INTEGER NOT NULL,
                Status TEXT NOT NULL DEFAULT 'Waiting', Timestamp TEXT NOT NULL, Ward TEXT)"""
        )
        conn.commit()
        empty = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0
    if not empty:
        return
    demo = [
        ("Rohan Mehta", "Severe chest pain, sweating", 5, "In Treatment", 3),
        ("Ananya Singh", "Road accident, heavy bleeding", 5, "Waiting", 1),
        ("Imran Qureshi", "Difficulty breathing, asthma attack", 4, "Waiting", 2),
        ("Kavita Nair", "Sudden weakness, slurred speech", 4, "In Treatment", 4),
        ("Deepak Joshi", "Fractured forearm after fall", 3, "Waiting", 2),
        ("Sneha Kulkarni", "High fever, persistent cough", 2, "Waiting", 5),
        ("Arjun Verma", "Palpitations and dizziness", 3, "Admitted", 9),
        ("Meena Pillai", "Burn injury on left hand", 3, "Admitted", 11),
        ("Farhan Sheikh", "Seizure episode, now conscious", 4, "Admitted", 8),
        ("Lakshmi Reddy", "Mild abdominal pain", 1, "Waiting", 6),
        ("Vikas Gupta", "Head injury after bike accident", 5, "Admitted", 14),
        ("Pooja Bansal", "Shortness of breath at rest", 4, "Admitted", 12),
        ("Harsh Tiwari", "Sprained ankle", 1, "Discharged", 20),
        ("Nisha Dubey", "Food poisoning, vomiting", 2, "Discharged", 18),
        ("Ravi Shankar", "Chest tightness on exertion", 3, "Waiting", 3),
        ("Sara Fernandes", "Deep wound on leg, bleeding", 4, "Waiting", 1),
    ]
    now = datetime.now()
    for name, sym, sev, status, hrs in demo:
        ts = (now - pd.Timedelta(hours=hrs, minutes=random.randint(0, 40))).strftime("%Y-%m-%d %H:%M:%S")
        insert_patient(name, sym, sev, status, ts, guess_ward(sym))

def load_patients():
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT rowid AS PID, * FROM patients", conn)
    canon = {"name": "Name", "symptoms": "Symptoms", "severity": "Severity",
             "status": "Status", "timestamp": "Timestamp", "ward": "Ward"}
    df = df.rename(columns={c: canon[c.lower()] for c in df.columns if c.lower() in canon})
    for col, default in [("Name", "Unknown"), ("Symptoms", ""), ("Severity", 1),
                         ("Status", "Waiting"), ("Timestamp", now_str())]:
        if col not in df.columns:
            df[col] = default
    df["Severity"] = pd.to_numeric(df["Severity"], errors="coerce").fillna(1).astype(int).clip(1, 5)
    if "Ward" not in df.columns:
        df["Ward"] = df["Symptoms"].map(guess_ward)
    df["Ward"] = df["Ward"].fillna("").replace("", "General Medicine")
    df["TS"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df["SevLabel"] = "Level " + df["Severity"].astype(str)
    return df

def priority_sort(df):
    return df.sort_values(["Severity", "TS"], ascending=[False, True])

init_db()

# =====================================================================
# PART 3 - Sidebar logic, RBAC (role-based access control) and Hero Header
# =====================================================================
LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 64" width="240" height="64">'
    '<rect x="4" y="6" width="52" height="52" rx="14" fill="#0F4C81"/>'
    '<rect x="27" y="16" width="6" height="32" rx="2" fill="#FFFFFF"/>'
    '<rect x="14" y="29" width="32" height="6" rx="2" fill="#FFFFFF"/>'
    '<text x="66" y="31" font-family="Arial, Helvetica, sans-serif" font-size="21" '
    'font-weight="700" fill="#0F4C81">VitalNode</text>'
    '<text x="66" y="49" font-family="Arial, Helvetica, sans-serif" font-size="11" '
    'fill="#64748B">Smart ER Triage System</text></svg>'
)
st.sidebar.image(LOGO_SVG)

role = st.sidebar.selectbox("Simulate System Login", ROLES)
ROLE_BADGES = {
    "System Admin": "🛡️ System Admin - Full Access",
    "Doctor": "👨‍⚕️ Dr. Admin - Clinical Access",
    "Front Desk Receptionist": "🧑‍💼 Front Desk - Intake Access",
}
st.sidebar.markdown(f'<div class="badge">{ROLE_BADGES[role]}</div>', unsafe_allow_html=True)
page = st.sidebar.radio("Main Menu", MENU)

if page != "Secure Master Records" or st.session_state.get("pin_role") != role:
    st.session_state["pin_input"] = ""
st.session_state["pin_role"] = role

all_df = load_patients()
with st.sidebar.expander("⚙️ Advanced Filters", expanded=False):
    status_filter = st.multiselect("🩺 Patient Status", STATUSES, default=STATUSES)
    sev_filter = st.slider("⚠️ Severity Range", 1, 5, (1, 5))
    search_text = st.text_input("🔍 Search Patient", placeholder="Name or symptom")

fdf = all_df[
    all_df["Status"].isin(status_filter)
    & all_df["Severity"].between(sev_filter[0], sev_filter[1])
]
if search_text.strip():
    q = search_text.strip().lower()
    fdf = fdf[
        fdf["Name"].astype(str).str.lower().str.contains(q, regex=False)
        | fdf["Symptoms"].astype(str).str.lower().str.contains(q, regex=False)
    ]

PAGE_SUBTITLE = {
    "Live Command Center": "Real-time ER capacity, triage queue and ward occupancy",
    "Rapid Emergency Intake": "Register new arrivals straight into the triage queue",
    "Rapid Response Team": "Deploy doctors and nurses to critical patients",
    "Active ER Monitor": "Patient ID card, vitals tracking and emergency clearance",
    "Bottleneck Analytics": "Spot where patients pile up by severity and arrival time",
    "Secure Master Records": "HIPAA-protected full patient database",
}

st.markdown(
    f"""<div class="hero"><h2>🏥 VitalNode | {html.escape(page)}</h2>
    <p>{html.escape(PAGE_SUBTITLE[page])} &nbsp;•&nbsp; {html.escape(role)} &nbsp;•&nbsp; {datetime.now().strftime('%d %b %Y, %H:%M')}</p></div>""",
    unsafe_allow_html=True,
)

def gate():
    if page in ACCESS[role]:
        return True
    st.error(f"🔒 Access Denied: Role '{role}' does not have clearance for {page}.")
    st.caption("Modules available to this role: " + ", ".join(m for m in MENU if m in ACCESS[role]))
    return False

# =====================================================================
# PART 4 - Live Command Center and Rapid Emergency Intake
# =====================================================================
def page_command_center():
    active_all = all_df[all_df["Status"].isin(ACTIVE_STATUSES)]
    active = fdf[fdf["Status"].isin(ACTIVE_STATUSES)]
    if fdf.empty:
        st.info("No patients match the current filters.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Patients", len(active))
    c2.metric("Waiting in Queue", int((fdf["Status"] == "Waiting").sum()))
    c3.metric("Critical (Sev 4-5)", int((active["Severity"] >= 4).sum()))
    c4.metric("Avg Severity", f"{active['Severity'].mean():.1f}" if len(active) else "0.0")
    st.write("")

    left, right = st.columns(2)
    occupancy = min(100, round(len(active_all) / ER_CAPACITY * 100, 1))
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=occupancy,
        number={"suffix": "%", "font": {"color": TEXT}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": TEXT},
            "bar": {"color": BLUE},
            "bgcolor": "rgba(0,0,0,0)",
            "steps": [
                {"range": [0, 60], "color": "#DBEAFE"},
                {"range": [60, 85], "color": "#FDE68A"},
                {"range": [85, 100], "color": "#FCA5A5"},
            ],
        },
    ))
    with left:
        show_plot(style_fig(gauge, f"ER Capacity ({len(active_all)} of {ER_CAPACITY} beds)"), key="gauge")

    admitted = fdf[fdf["Status"] == "Admitted"]
    with right:
        if admitted.empty:
            st.info("No admitted patients in the current view.")
        else:
            sun = px.sunburst(
                admitted, path=["Ward", "SevLabel"],
                color_discrete_sequence=["#0F4C81", "#1E7BC6", "#60A5FA", "#93C5FD", "#BFDBFE", "#64748B"],
            )
            show_plot(style_fig(sun, "Admitted Wards"), key="sunburst")

    queue = priority_sort(fdf[fdf["Status"] == "Waiting"]).head(12)
    if queue.empty:
        st.success("The triage queue is clear.")
    else:
        bar = px.bar(
            queue, x="Severity", y="Name", orientation="h", color="Severity",
            color_continuous_scale=["#93C5FD", "#0F4C81", "#DC2626"], range_color=[1, 5],
            hover_data={"Symptoms": True, "Timestamp": True},
        )
        bar.update_yaxes(autorange="reversed", title=None)
        bar.update_xaxes(range=[0, 5.2], dtick=1, title="Severity")
        show_plot(style_fig(bar, "Active Triage Queue (highest priority first)", 420), key="queue")
        top = queue.iloc[0]
        st.caption(f"Next to be treated: **{top['Name']}** (Severity {top['Severity']}) - {top['Symptoms']}")

def page_intake():
    st.markdown("#### Log a new arrival")
    with st.form("intake_form", clear_on_submit=True):
        name = st.text_input("Patient Name")
        symptoms = st.text_area("Exact Symptoms", height=100)
        severity = st.select_slider(
            "Initial Severity Score", options=[1, 2, 3, 4, 5], value=3,
            format_func=lambda v: f"{v} - {SEV_NAME[v]}",
        )
        submitted = st.form_submit_button("🚑 Register Patient")
    if submitted:
        if not name.strip() or not symptoms.strip():
            st.error("Please enter both the patient name and the symptoms.")
        else:
            try:
                new_id = insert_patient(
                    name.strip(), symptoms.strip(), int(severity), "Waiting", now_str(),
                    ward=guess_ward(symptoms),
                )
                st.success(f"✅ {name.strip()} was registered (ID {new_id}) with status Waiting "
                           f"and added to the triage queue.")
            except sqlite3.Error as exc:
                st.error(f"Could not save the patient: {exc}")

    st.markdown("#### Latest arrivals")
    recent = load_patients().sort_values("TS", ascending=False).head(8)
    show_table(recent[["PID", "Name", "Symptoms", "Severity", "Status", "Timestamp"]])

# =====================================================================
# PART 5 - Rapid Response Team and Active ER Monitor
# =====================================================================
def _deploy_team():
    pid = st.session_state.get("deploy_pid")
    if pid is None:
        return
    st.session_state.assignments[int(pid)] = {
        "doctor": st.session_state["deploy_doc"],
        "nurse": st.session_state["deploy_nurse"],
        "time": now_str(),
    }
    st.session_state["flash"] = (
        f"✅ {st.session_state['deploy_doc']} and {st.session_state['deploy_nurse']} deployed."
    )

def _release_team():
    pid = st.session_state.get("release_pid")
    if pid is not None:
        st.session_state.assignments.pop(int(pid), None)
        st.session_state["flash"] = "Team released and returned to the available pool."

def page_response_team():
    critical = priority_sort(all_df[(all_df["Severity"] >= 4) & (all_df["Status"] != "Discharged")])
    names = dict(zip(all_df["PID"].astype(int), all_df["Name"]))
    crit_ids = [int(p) for p in critical["PID"]]
    assigned = st.session_state.assignments

    doc_load = {d: 0 for d in DOCTORS}
    nurse_load = {n: 0 for n in NURSES}
    for pid, a in assigned.items():
        if pid in crit_ids:
            doc_load[a["doctor"]] += 1
            nurse_load[a["nurse"]] += 1

    if st.session_state.get("flash"):
        st.success(st.session_state.pop("flash"))

    if not crit_ids:
        st.info("No critical patients (Severity 4-5) at the moment.")
        return

    st.markdown("#### Deploy a trauma team")
    with st.form("deploy_form"):
        st.selectbox(
            "Critical Patient", crit_ids, key="deploy_pid",
            format_func=lambda p: f"#{p} - {names[p]} (Severity {int(all_df.loc[all_df['PID'] == p, 'Severity'].iloc[0])})",
        )
        c1, c2 = st.columns(2)
        c1.selectbox("ER Doctor", DOCTORS, key="deploy_doc",
                     format_func=lambda d: f"{d}  ({doc_load[d]} critical)")
        c2.selectbox("ER Nurse", NURSES, key="deploy_nurse",
                     format_func=lambda n: f"{n}  ({nurse_load[n]} critical)")
        st.form_submit_button("🚨 Deploy Team", on_click=_deploy_team)

    staff = pd.DataFrame(
        [{"Staff": d, "Role": "Doctor", "Critical Patients": v} for d, v in doc_load.items()]
        + [{"Staff": n, "Role": "Nurse", "Critical Patients": v} for n, v in nurse_load.items()]
    )
    fig = px.bar(
        staff, x="Staff", y="Critical Patients", color="Role", text="Critical Patients",
        barmode="group", color_discrete_map={"Doctor": BLUE, "Nurse": "#60A5FA"},
    )
    fig.update_yaxes(dtick=1, rangemode="tozero")
    fig.update_traces(textposition="outside")
    show_plot(style_fig(fig, "Staff Workload (critical patients per staff member)"), key="workload")

    board = critical[["PID", "Name", "Symptoms", "Severity", "Status"]].copy()
    board["Doctor"] = [assigned.get(int(p), {}).get("doctor", "- unassigned -") for p in board["PID"]]
    board["Nurse"] = [assigned.get(int(p), {}).get("nurse", "- unassigned -") for p in board["PID"]]
    st.markdown("#### Critical patient board")
    show_table(board)

    live_assigned = [p for p in assigned if p in crit_ids]
    if live_assigned:
        with st.expander("Release a team"):
            st.selectbox("Patient", live_assigned, key="release_pid",
                         format_func=lambda p: f"#{p} - {names.get(p, 'Unknown')}")
            st.button("Release Team", on_click=_release_team)

def medical_id_card(row):
    sev = int(row["Severity"])
    team = st.session_state.assignments.get(int(row["PID"]))
    if pd.notna(row["TS"]):
        mins = int((datetime.now() - row["TS"]).total_seconds() // 60)
        waited = f"{max(mins, 0) // 60}h {max(mins, 0) % 60}m"
    else:
        waited = "-"
    doctor = team["doctor"] if team else "Not assigned"
    nurse = team["nurse"] if team else "Not assigned"
    e = lambda v: html.escape(str(v))
    st.markdown(
        f"""<div class="idcard">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
            <div><div class="pname">{e(row['Name'])}</div>
            <div class="meta">Patient ID #{e(row['PID'])} &nbsp;•&nbsp; Arrived {e(row['Timestamp'])}</div></div>
            <span class="sevpill" style="background:{SEV_COLOR[sev]};">Severity {sev} - {SEV_NAME[sev]}</span>
        </div>
        <div class="grid">
            <div class="cell"><span>Status</span><b>{e(row['Status'])}</b></div>
            <div class="cell"><span>Ward</span><b>{e(row['Ward'])}</b></div>
            <div class="cell"><span>Time in ER</span><b>{waited}</b></div>
            <div class="cell"><span>ER Doctor</span><b>{e(doctor)}</b></div>
            <div class="cell"><span>ER Nurse</span><b>{e(nurse)}</b></div>
        </div>
        <div class="cell" style="margin-top:12px;"><span>Presenting symptoms</span><b>{e(row['Symptoms'])}</b></div>
        </div>""",
        unsafe_allow_html=True,
    )

def page_er_monitor():
    pool = priority_sort(all_df)
    if pool.empty:
        st.info("No patients in the system yet.")
        return
    ids = [int(p) for p in pool["PID"]]
    lookup = pool.set_index(pool["PID"].astype(int))
    pid = st.selectbox(
        "Select patient", ids,
        format_func=lambda p: f"#{p} - {lookup.loc[p, 'Name']} (Severity {lookup.loc[p, 'Severity']}, {lookup.loc[p, 'Status']})",
    )
    medical_id_card(lookup.loc[pid].to_dict() | {"PID": pid})

    tab_vitals, tab_clear = st.tabs(["🩺 Vitals & Treatment", "🗂️ Admin Clearance"])
    with tab_vitals:
        readings = st.session_state.vitals.setdefault(pid, [])
        notes = st.session_state.notes.setdefault(pid, [])
        if role in ("System Admin", "Doctor"):
            with st.form(f"vitals_form_{pid}", clear_on_submit=True):
                c1, c2 = st.columns([1, 2])
                hr = c1.number_input("Heart Rate (bpm)", min_value=0, max_value=250, value=80, step=1)
                note = c2.text_input("Treatment note", placeholder="e.g. Pushed IV Epinephrine 1 mg")
                if st.form_submit_button("➕ Log Vitals / Treatment"):
                    readings.append({"time": datetime.now().strftime("%H:%M:%S"), "hr": int(hr)})
                    if note.strip():
                        notes.append({"time": now_str(), "by": role, "text": note.strip()})
            if st.button("📡 Simulate telemetry reading", key=f"sim_{pid}"):
                last = readings[-1]["hr"] if readings else 80
                new_hr = max(30, min(180, last + random.randint(-18, 18)))
                readings.append({"time": datetime.now().strftime("%H:%M:%S"), "hr": new_hr})
        else:
            st.caption("Clinical entry is restricted to Doctors and System Admins. Showing read-only data.")

        if not readings:
            st.info("No heart-rate readings logged for this patient yet.")
        else:
            latest = readings[-1]["hr"]
            if latest < 50 or latest > 130:
                st.warning(f"🚨 Code Blue / Crash Risk: heart rate is {latest} bpm "
                           f"(safe range 50-130). Alert the resuscitation team immediately.")
            else:
                st.success(f"Latest heart rate {latest} bpm is within the safe range.")

            fig = go.Figure(go.Scatter(
                x=list(range(1, len(readings) + 1)), y=[r["hr"] for r in readings],
                mode="lines+markers", line=dict(color=BLUE, width=3),
                customdata=[r["time"] for r in readings],
                hovertemplate="Reading %{x}<br>%{y} bpm<br>%{customdata}<extra></extra>",
            ))
            fig.add_hrect(y0=50, y1=130, fillcolor="#DBEAFE", opacity=0.35, line_width=0)
            fig.add_hline(y=130, line_dash="dash", line_color="#DC2626")
            fig.add_hline(y=50, line_dash="dash", line_color="#DC2626")
            fig.update_xaxes(title="Reading #", dtick=1)
            fig.update_yaxes(title="Heart Rate (bpm)", range=[20, 190])
            show_plot(style_fig(fig, "Heart Rate History"), key=f"hr_{pid}")

        if notes:
            st.markdown("**Treatment log**")
            for n in reversed(notes):
                st.markdown(f"- `{n['time']}` - {n['text']} _({n['by']})_")

    with tab_clear:
        st.markdown("##### Identity & Insurance Clearance")
        uploads = st.file_uploader(
            "Upload ID / insurance documents", type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True, key=f"up_{pid}",
        )
        if uploads:
            st.session_state.files[pid] = [{"name": f.name, "size": f.size} for f in uploads]
        if st.session_state.files.get(pid):
            for f in st.session_state.files[pid]:
                st.success(f"📎 {f['name']} ({f['size'] / 1024:.1f} KB) received - clearance pending review.")

        st.markdown("##### Emergency Contacts / Next-of-Kin")
        with st.form(f"kin_form_{pid}", clear_on_submit=True):
            k1, k2, k3 = st.columns(3)
            kname = k1.text_input("Contact name")
            krel = k2.selectbox("Relationship", ["Parent", "Spouse", "Sibling", "Child", "Friend", "Guardian", "Other"])
            kphone = k3.text_input("Phone number")
            if st.form_submit_button("💾 Save Contact"):
                if kname.strip() and kphone.strip():
                    st.session_state.contacts.setdefault(pid, []).append(
                        {"Name": kname.strip(), "Relationship": krel, "Phone": kphone.strip()})
                    st.success("Contact saved.")
                else:
                    st.error("Contact name and phone number are required.")
        if st.session_state.contacts.get(pid):
            show_table(pd.DataFrame(st.session_state.contacts[pid]))

# =====================================================================
# PART 6 - Bottleneck Analytics, Secure Master Records and page router
# =====================================================================
def page_analytics():
    if fdf.empty:
        st.info("No patients match the current filters.")
        return

    left, right = st.columns(2)
    ct = (pd.crosstab(fdf["Severity"], fdf["Status"])
          .reindex(index=[1, 2, 3, 4, 5], columns=STATUSES, fill_value=0))
    heat = px.imshow(
        ct.values, x=STATUSES, y=[f"Level {i}" for i in ct.index],
        text_auto=True, color_continuous_scale="Blues", aspect="auto",
        labels=dict(x="Status", y="Severity", color="Patients"),
    )
    with left:
        show_plot(style_fig(heat, "Severity vs Status Heatmap"), key="heatmap")

    ts = fdf.dropna(subset=["TS"])
    with right:
        if ts.empty:
            st.info("No valid arrival timestamps to plot.")
        else:
            hourly = ts.groupby(ts["TS"].dt.floor("60min")).size()
            full_range = pd.date_range(hourly.index.min(), hourly.index.max(), freq="60min")
            hourly = hourly.reindex(full_range, fill_value=0).rename_axis("Hour").reset_index(name="Arrivals")
            area = px.area(hourly, x="Hour", y="Arrivals", markers=True)
            area.update_traces(line_color=BLUE, fillcolor="rgba(15,76,129,0.25)")
            area.update_yaxes(dtick=1, rangemode="tozero")
            show_plot(style_fig(area, "Arrival Timeline (patients per hour)"), key="timeline")

    waiting = fdf[fdf["Status"] == "Waiting"]
    if not waiting.empty and waiting["TS"].notna().any():
        oldest = waiting.sort_values("TS").iloc[0]
        mins = int((datetime.now() - oldest["TS"]).total_seconds() // 60)
        st.caption(f"Longest wait: **{oldest['Name']}** (Severity {oldest['Severity']}) has waited {mins // 60}h {mins % 60}m.")

def page_records():
    if role == "Doctor":
        st.markdown(
            """<div class="secure"><h3>🔐 HIPAA Security Checkpoint</h3>
            <p>Master patient records are protected. Enter your 4-digit authorization PIN to continue.</p></div>""",
            unsafe_allow_html=True,
        )
        pin = st.text_input("Doctor Authorization PIN", type="password", max_chars=4, key="pin_input")
        if pin != DOCTOR_PIN:
            st.error("🔒 Verification Required: enter the Doctor Authorization PIN to view sensitive patient data.")
            return
        st.success("✅ Identity verified. Access granted for this session.")

    with closing(get_conn()) as conn:
        full = pd.read_sql_query("SELECT * FROM patients", conn)
    st.caption(f"{len(full)} records in SmartHospital.db")
    show_table(full)

PAGES = {
    "Live Command Center": page_command_center,
    "Rapid Emergency Intake": page_intake,
    "Rapid Response Team": page_response_team,
    "Active ER Monitor": page_er_monitor,
    "Bottleneck Analytics": page_analytics,
    "Secure Master Records": page_records,
}

if gate():
    PAGES[page]()
