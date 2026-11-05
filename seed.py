"""Insert a small, entirely synthetic dataset. Safe to run more than once."""
from datetime import date, timedelta
import random
from database import init_db, get_connection

random.seed(7)
init_db()
conn = get_connection()
cur = conn.cursor()
departments = ["Cardiology", "Orthopedics", "Pediatrics", "Neurology", "General Medicine", "Dermatology"]
for name in departments:
    cur.execute("INSERT IGNORE INTO departments (department_name) VALUES (%s)", (name,))

cur.execute("SELECT COUNT(*) FROM patients")
if cur.fetchone()[0] == 0:
    age_bands = ["0-17", "18-29", "30-44", "45-59", "60+"]
    genders = ["Female", "Male", None]
    for _ in range(80):
        cur.execute("INSERT INTO patients (age_band, gender) VALUES (%s, %s)",
                    (random.choice(age_bands), random.choice(genders)))

cur.execute("SELECT COUNT(*) FROM visits")
if cur.fetchone()[0] == 0:
    cur.execute("SELECT patient_id FROM patients")
    patient_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT department_id FROM departments")
    department_ids = [r[0] for r in cur.fetchall()]
    types = ["Outpatient", "Inpatient", "Emergency", "Follow-up"]
    for _ in range(250):
        visit_date = date.today() - timedelta(days=random.randint(0, 179))
        cur.execute("""INSERT INTO visits (patient_id, department_id, visit_date, visit_type)
                       VALUES (%s, %s, %s, %s)""",
                    (random.choice(patient_ids), random.choice(department_ids),
                     visit_date, random.choice(types)))
conn.commit()
cur.close()
conn.close()
print("Synthetic sample data is ready.")
