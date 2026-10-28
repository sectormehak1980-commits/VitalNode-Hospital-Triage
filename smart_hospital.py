import sqlite3
import heapq
import time
from datetime import datetime
from collections import deque

# ==============================================================================
# ELITE HOSPITAL TRIAGE ENGINE (DSA MASTERY)
# Features: Max-Heap, Doubly Linked List, Trie (Auto-Complete), Graphs (BFS)
# ==============================================================================

def init_database():
    conn = sqlite3.connect("SmartHospital.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            symptoms TEXT,
            severity INTEGER NOT NULL,
            status TEXT NOT NULL,
            bed_assigned INTEGER,
            bed_type TEXT,
            admission_time TEXT
        )
    """)
    conn.commit()
    return conn

db_conn = init_database()

# --- 1. GRAPH THEORY (BFS for Shortest Path Stretcher Routing) ---
hospital_floorplan = {
    "Waiting_Room": ["Hallway_A"],
    "Hallway_A": ["ICU_Ward", "Hallway_B"],
    "ICU_Ward": ["Bed_1", "Bed_2"],
    "Hallway_B": ["General_Ward"],
    "General_Ward": ["Bed_3", "Bed_4", "Bed_5"]
}

def bfs_shortest_path(start, target):
    # Uses a Double-Ended Queue (Deque) to find the shortest physical path to the bed
    queue = deque([(start, [start])])
    visited = set()
    while queue:
        current, path = queue.popleft()
        if current == target: 
            return " ➔ ".join(path)
        visited.add(current)
        for neighbor in hospital_floorplan.get(current, []):
            if neighbor not in visited:
                queue.append((neighbor, path + [neighbor]))
    return "Path calculated"


# --- 2. TRIE / PREFIX TREE (O(L) Auto-Complete Search) ---
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.patient_data = None

class PatientTrie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, name, severity):
        node = self.root
        for char in name.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.patient_data = severity

    def search_prefix(self, prefix):
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]
        results = []
        self._dfs(node, prefix, results)
        return results

    def _dfs(self, node, current_word, results):
        if node.is_end_of_word:
            results.append(f"{current_word.title()} (Severity: {node.patient_data})")
        for char, child_node in node.children.items():
            self._dfs(child_node, current_word + char, results)


# --- 3. DOUBLY LINKED LIST (ICU & General Wards) ---
class BedNode:
    def __init__(self, bed_number, bed_type):
        self.bed_number = bed_number
        self.bed_type = bed_type
        self.patient_name = None
        self.next = None
        self.prev = None  # UPGRADE: Makes this a Doubly Linked List

class HospitalWard:
    def __init__(self):
        self.head = BedNode(1, "ICU")
        
        node2 = BedNode(2, "ICU")
        self.head.next = node2
        node2.prev = self.head
        
        node3 = BedNode(3, "General")
        node2.next = node3
        node3.prev = node2
        
        node4 = BedNode(4, "General")
        node3.next = node4
        node4.prev = node3
        
        node5 = BedNode(5, "General")
        node4.next = node5
        node5.prev = node4

    def allocate_bed(self, patient_name, severity):
        required_type = "ICU" if severity >= 4 else "General"
        current = self.head
        
        while current:
            if current.patient_name is None and current.bed_type == required_type:
                current.patient_name = patient_name
                return current.bed_number, current.bed_type
            current = current.next
            
        # Overflow logic
        if severity >= 4:
            current = self.head
            while current:
                if current.patient_name is None:
                    current.patient_name = patient_name
                    return current.bed_number, current.bed_type
                current = current.next
        return -1, None

    def release_bed(self, bed_number):
        current = self.head
        while current:
            if current.bed_number == bed_number:
                if current.patient_name is not None:
                    released = current.patient_name
                    current.patient_name = None
                    return released
                return None
            current = current.next
        return None

    def get_ward_status(self):
        status_list = []
        current = self.head
        while current:
            occupant = current.patient_name if current.patient_name else "Empty"
            status_list.append((current.bed_number, current.bed_type, occupant))
            current = current.next
        return status_list


# --- 4. ANTI-STARVATION MAX-HEAP ---
class Patient:
    def __init__(self, name, severity, symptoms):
        self.name = name
        self.severity = severity
        self.symptoms = symptoms
        self.arrival_time = time.time()

    def get_dynamic_priority(self):
        wait_time = time.time() - self.arrival_time
        return self.severity + (wait_time * 0.1)

    def __lt__(self, other):
        return self.get_dynamic_priority() > other.get_dynamic_priority()

triage_heap = []
patient_directory = PatientTrie()
ward_manager = HospitalWard()

# --- 5. AI SYMPTOM ANALYZER (Rule-Based NLP Engine) ---
def analyze_symptoms(text):
    text = text.lower()
    if any(word in text for word in ["heart", "cardiac", "stroke", "breathing", "unconscious", "chest"]): return 5
    elif any(word in text for word in ["bleeding", "fracture", "head", "burn"]): return 4
    elif any(word in text for word in ["pain", "fever", "vomiting", "dizzy"]): return 3
    elif any(word in text for word in ["cough", "sprain", "rash"]): return 2
    else: return 1

# --- CORE OPERATIONS ---
def admit_patient():
    name = input("\nEnter Patient Name: ").strip()
    symptoms = input("Enter Patient Symptoms: ").strip()
    
    severity = analyze_symptoms(symptoms)
    timestamp = datetime.now().strftime("%H:%M:%S")

    patient_record = Patient(name, severity, symptoms)
    heapq.heappush(triage_heap, patient_record)
    
    # Store in Trie for fast lookup
    patient_directory.insert(name, severity)

    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO patients (name, symptoms, severity, status, admission_time) VALUES (?, ?, ?, 'Waiting', ?)", 
        (name, symptoms, severity, timestamp)
    )
    db_conn.commit()
    print(f"\n✅ SUCCESS: {name} triaged at Severity {severity}. Added to Waiting Room.")

def treat_next_patient():
    if not triage_heap:
        print("\n❌ Triage queue is empty.")
        return

    critical_patient = heapq.heappop(triage_heap)
    bed_no, assigned_type = ward_manager.allocate_bed(critical_patient.name, critical_patient.severity)

    if bed_no != -1:
        # Calculate routing using Graph BFS
        target_node = f"Bed_{bed_no}"
        route = bfs_shortest_path("Waiting_Room", target_node)

        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE patients SET status = 'Admitted', bed_assigned = ?, bed_type = ? WHERE name = ? AND status = 'Waiting'", 
            (bed_no, assigned_type, critical_patient.name)
        )
        db_conn.commit()
        print(f"\n✅ SUCCESS: {critical_patient.name} (Severity {critical_patient.severity}) assigned to Bed {bed_no} ({assigned_type}).")
        print(f"🚑 Stretcher Routing: {route}")
    else:
        heapq.heappush(triage_heap, critical_patient)
        print("\n❌ Ward is full! Patient remains in waiting room.")

def discharge_patient():
    try:
        bed_no = int(input("\nEnter Bed Number to discharge: "))
        discharged_name = ward_manager.release_bed(bed_no)
        if discharged_name:
            cursor = db_conn.cursor()
            cursor.execute("UPDATE patients SET status = 'Discharged', bed_assigned = NULL, bed_type = NULL WHERE name = ? AND status = 'Admitted'", (discharged_name,))
            db_conn.commit()
            print(f"\n✅ SUCCESS: {discharged_name} discharged. Bed {bed_no} is now empty.")
        else:
            print(f"\n❌ ACTION FAILED: Bed {bed_no} is already vacant.")
    except ValueError:
        print("\n❌ Error: Invalid bed number.")

def search_patient_trie():
    prefix = input("\nEnter first few letters of patient name: ").strip()
    results = patient_directory.search_prefix(prefix)
    if results:
        print(f"\n🔍 Found {len(results)} matches in Trie (O(L) Time):")
        for r in results:
            print(f" - {r}")
    else:
        print("\n❌ No patients found matching that prefix.")

def view_text_logs():
    print("\n--- 🛏️ Live Ward Bed Status ---")
    for bed_no, b_type, occupant in ward_manager.get_ward_status():
        tag = f"🔴 Occupied by {occupant}" if occupant != "Empty" else "🟢 Vacant"
        print(f"Bed {bed_no} [{b_type}]: {tag}")

def main():
    while True:
        print("\n+" + "-" * 42 + "+")
        print("| 🏥 ADVANCED HOSPITAL TRIAGE MENU         |")
        print("+" + "-" * 42 + "+")
        print("  1. AI Symptom Admit (To Waiting Room)")
        print("  2. Treat Patient (Anti-Starvation & BFS)")
        print("  3. Discharge Patient (Empty Bed)")
        print("  4. Search Patient (Trie Auto-Complete)")
        print("  5. View Local Ward Status")
        print("  6. Terminate Session")
        
        selection = input("\nSelect Option (1-6): ").strip()
        
        if selection == "1": admit_patient()
        elif selection == "2": treat_next_patient()
        elif selection == "3": discharge_patient()
        elif selection == "4": search_patient_trie()
        elif selection == "5": view_text_logs()
        elif selection == "6":
            db_conn.close()
            print("Closing system...")
            break
        else:
            print("Invalid selection.")

if __name__ == "__main__":
    main()