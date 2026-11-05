from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from functools import wraps
from config import Config
from database import get_connection, init_db
from analytics import get_dashboard_data, get_department_report, get_age_band_report, get_monthly_report, get_aggregated_export

app = Flask(__name__)
app.config.from_object(Config)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form.get("username") == app.config["ADMIN_USERNAME"] and
                request.form.get("password") == app.config["ADMIN_PASSWORD"]):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    data = get_dashboard_data()
    return render_template("dashboard.html", data=data)

@app.route("/reports")
@login_required
def reports():
    return render_template(
        "reports.html",
        departments=get_department_report(),
        age_bands=get_age_band_report(),
        monthly=get_monthly_report()
    )

@app.route("/reports/export.csv")
@login_required
def export_reports():
    # Export only grouped operational statistics, never row-level patient data.
    csv_data = get_aggregated_export().to_csv(index=False)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=hospital_aggregate_report.csv"}
    )

@app.route("/visits")
@login_required
def visits():
    # Individual rows are visible only to authenticated administrators.
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT v.visit_id, v.visit_date, v.visit_type, d.department_name,
               p.age_band, COALESCE(p.gender, 'Not specified') AS gender
        FROM visits v
        JOIN patients p ON p.patient_id = v.patient_id
        JOIN departments d ON d.department_id = v.department_id
        ORDER BY v.visit_date DESC, v.visit_id DESC
        LIMIT 200
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("visits.html", visits=rows)

@app.route("/patients/add", methods=["GET", "POST"])
@login_required
def add_patient():
    if request.method == "POST":
        age_band = request.form.get("age_band")
        gender = request.form.get("gender") or None
        if age_band not in ["0-17", "18-29", "30-44", "45-59", "60+"]:
            flash("Choose a valid age band.", "danger")
            return redirect(url_for("add_patient"))
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO patients (age_band, gender) VALUES (%s, %s)", (age_band, gender))
        conn.commit()
        cur.close()
        conn.close()
        flash("Synthetic patient record added.", "success")
        return redirect(url_for("visits"))
    return render_template("add_patient.html")

@app.route("/visits/add", methods=["GET", "POST"])
@login_required
def add_visit():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT department_id, department_name FROM departments ORDER BY department_name")
    departments = cur.fetchall()
    cur.execute("SELECT patient_id, age_band FROM patients ORDER BY patient_id DESC LIMIT 500")
    patients = cur.fetchall()
    cur.close()
    conn.close()

    if request.method == "POST":
        patient_id = request.form.get("patient_id", type=int)
        department_id = request.form.get("department_id", type=int)
        visit_date = request.form.get("visit_date")
        visit_type = request.form.get("visit_type")
        if not all([patient_id, department_id, visit_date]) or visit_type not in ["Outpatient", "Inpatient", "Emergency", "Follow-up"]:
            flash("Please complete all fields correctly.", "danger")
            return redirect(url_for("add_visit"))
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT INTO visits (patient_id, department_id, visit_date, visit_type)
                       VALUES (%s, %s, %s, %s)""",
                    (patient_id, department_id, visit_date, visit_type))
        conn.commit()
        cur.close()
        conn.close()
        flash("Visit record added.", "success")
        return redirect(url_for("visits"))
    return render_template("add_visit.html", departments=departments, patients=patients)

@app.errorhandler(500)
def server_error(error):
    return render_template("error.html"), 500

if __name__ == "__main__":
    init_db()
    app.run(debug=app.config["DEBUG"])
