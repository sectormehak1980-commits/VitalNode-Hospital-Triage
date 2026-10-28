# 🏥 VitalNode | Smart ER Triage & Hospital Intelligence System

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-red.svg)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)](https://www.sqlite.org/)
[![Data Structures](https://img.shields.io/badge/Algorithms-DSA-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*An enterprise-grade, full-stack hospital emergency room workflow system bridging high-performance backend Data Structures & Algorithms (DSA) with a modern, responsive SaaS web interface.*

</div>

---

## 📌 Project Overview

**VitalNode** is a comprehensive software solution engineered to resolve critical operational bottlenecks in emergency medical departments. By replacing manual patient intake with an automated, algorithm-driven system, VitalNode dynamically prioritizes patients, allocates hospital beds, tracks staff workloads, and generates live analytics. 

Developed as an academic capstone for a B.Tech Computer Science and Engineering (AI & ML) curriculum, this system demonstrates rigorous software engineering, modular architecture, and the practical application of advanced Data Structures and Algorithms in a real-world healthcare scenario.

---

## 🧠 Core Technical Implementation & DSA Engine

At the heart of VitalNode is a custom-built, high-performance algorithmic backend designed to handle patient flow with maximum efficiency. 

### 1. Max-Heap Priority Queue (Anti-Starvation)
* **Concept:** Patients are not simply treated on a "First-Come, First-Serve" basis. The system utilizes a Max-Heap (`heapq`) to dynamically sort the active patient queue.
* **Implementation:** Priority is calculated using a dynamic formula: `Severity Score + (Waiting Time * 0.1)`. This ensures that highly critical patients (e.g., Level 5 - Resuscitation) immediately jump to the top of the queue, while lower-severity patients gradually gain priority over time to prevent treatment starvation.

### 2. Doubly Linked List (DLL) Ward Allocation
* **Concept:** Physical hospital beds are modeled using a custom `BedNode` class organized into a Doubly Linked List within the `HospitalWard` manager.
* **Implementation:** The DLL structure allows for $O(1)$ pointer traversal when navigating between adjacent beds. It manages distinct "ICU" and "General" wards, supporting rapid bed allocation, occupancy tracking, and bed release operations. It also includes automated overflow logic, routing ICU patients to General beds if the ICU is at maximum capacity.

### 3. Graph Theory & BFS Stretcher Routing
* **Concept:** The hospital's physical floorplan is mapped as a Graph (adjacency list) connecting the `Waiting_Room`, `Hallway_A`, `Hallway_B`, `ICU_Ward`, and individual beds.
* **Implementation:** A Breadth-First Search (BFS) algorithm utilizing a Double-Ended Queue (`collections.deque`) calculates the absolute shortest physical routing path for emergency stretchers from the intake desk to the newly allocated bed.

### 4. Trie (Prefix Tree) Auto-Complete Indexing
* **Concept:** To handle rapid patient lookups in emergency situations, the system utilizes a custom `PatientTrie`.
* **Implementation:** Patient names and severity data are inserted into Trie nodes, allowing for blazing-fast $O(L)$ time-complexity searches (where $L$ is the length of the prefix). This ensures that searching for a patient's record is instantaneous, regardless of the total database size.

### 5. Rule-Based NLP Symptom Analyzer
* **Concept:** Automated clinical triage routing.
* **Implementation:** A custom Python Natural Language Processing (NLP) function scans raw text input from the patient's presenting symptoms. By matching clinical keywords (e.g., *"chest", "cardiac", "stroke", "fracture", "breath"*), the system automatically categorizes and routes the patient to the correct medical department (Cardiology, Neurology, Trauma, Pulmonology, General Medicine) without requiring manual staff intervention.

---

## 🖥️ Streamlit SaaS Dashboard (`dashboard.py`)

The frontend of VitalNode is a powerful, responsive web application built with Streamlit, completely integrated with the Python backend.

### User Interface & Design
* **Custom Medical SaaS Theme:** Injects raw CSS into Streamlit to override default styles, providing a clean, modern medical aesthetic with high-contrast accent palettes, professional typography, and custom medical watermarks.
* **Single-Page Application (SPA) Feel:** Utilizes Streamlit's sidebar radio buttons to create seamless, multi-page navigation within a single Python execution environment.

### Core Dashboard Modules
1. **🟢 Live Command Center:** The central hub for ER administrators. Displays real-time ER capacity gauges, active critical queues, and total patient volume. Features dynamic updates directly from the SQLite database.
2. **📝 Rapid Emergency Intake:** An optimized web form allowing triage nurses to log patient names, exact symptoms, and visual severity scores (1-5 slider). Submitting this form instantly triggers the NLP routing and DSA heap sorting.
3. **🩺 Active ER Monitor:** Provides interactive patient ID cards. Allows response teams to track deployed medical staff, log patient vitals, and update treatment statuses in real-time.
4. **📊 Bottleneck Analytics:** Powered by `pandas` and `plotly.express`. 
   * Generates interactive *Severity vs. Status Heatmaps*.
   * Features a live *Arrival Timeline Area Chart* (configured with `markers=True` for robust empty-state rendering), plotting hourly patient intake volume to predict staffing bottlenecks.
5. **🔒 Secure Master Records:** Implements strict Role-Based Access Control (RBAC). Standard users are locked out, requiring clinical staff to select the "Doctor" role and input an encrypted 4-digit PIN to unlock raw, HIPAA-compliant tabular database records.

---

## 💾 Persistent Storage Architecture

* **SQLite Relational Database (`SmartHospital.db`):** 
  * The system utilizes a serverless, file-based SQLite database for robust data persistence.
  * **Auto-Initialization:** The script uses `CREATE TABLE IF NOT EXISTS`, ensuring the database and required schemas (id, name, symptoms, severity, status, timestamp, ward) are automatically generated upon the first run.
  * **Multi-Interface Synchronization:** The database acts as a centralized source of truth, allowing seamless data flow whether input comes from the Streamlit web app or a terminal-based CLI script.

---

## 📂 Project Structure

```text
VitalNode-Hospital-Triage/
│
├── dashboard.py          # Main Streamlit web dashboard & frontend interface
├── smart_hospital.py     # Core DSA backend engine, CLI triage, and data structures
├── SmartHospital.db      # Persistent SQLite relational database (Auto-generates)
├── requirements.txt      # Project dependencies configuration (streamlit, pandas, plotly)
└── README.md             # Project documentation
