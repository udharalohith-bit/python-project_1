import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from database import get_connection

CHART_DIR = Path("static/charts")
CHART_DIR.mkdir(parents=True, exist_ok=True)

def load_visits():
    conn = get_connection()
    query = """
        SELECT v.visit_id, v.patient_id, v.visit_date, v.visit_type, p.age_band,
               COALESCE(p.gender, 'Not specified') AS gender, d.department_name
        FROM visits v
        JOIN patients p ON p.patient_id = v.patient_id
        JOIN departments d ON d.department_id = v.department_id
    """
    df = pd.read_sql(query, conn)
    conn.close()
    if not df.empty:
        df["visit_date"] = pd.to_datetime(df["visit_date"])
    return df

def get_dashboard_data():
    df = load_visits()
    if df.empty:
        return {"total_visits": 0, "departments": 0, "patients": 0,
                "this_month": 0, "avg_daily_visits": 0,
                "department_labels": [], "department_values": [],
                "monthly_labels": [], "monthly_values": [],
                "type_labels": [], "type_values": []}
    today = pd.Timestamp.today().normalize()
    month_start = today.replace(day=1)
    monthly = df.set_index("visit_date").resample("MS").size()
    dept = df.groupby("department_name").size().sort_values(ascending=False)
    visit_types = df.groupby("visit_type").size().sort_values(ascending=False)
    daily = df.groupby(df["visit_date"].dt.date).size()
    fig, ax = plt.subplots(figsize=(8, 4))
    dept.plot(kind="bar", ax=ax)
    ax.set_title("Visits by Department")
    ax.set_xlabel("Department")
    ax.set_ylabel("Number of visits")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    fig.savefig(CHART_DIR / "departments.png")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    monthly.plot(marker="o", ax=ax)
    ax.set_title("Monthly Visit Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Number of visits")
    plt.tight_layout()
    fig.savefig(CHART_DIR / "monthly.png")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4))
    visit_types.plot(kind="pie", autopct="%1.1f%%", ax=ax, ylabel="")
    ax.set_title("Visit Type Distribution")
    plt.tight_layout()
    fig.savefig(CHART_DIR / "visit_types.png")
    plt.close(fig)
    return {
        "total_visits": int(len(df)),
        "departments": int(df["department_name"].nunique()),
        "patients": int(df["patient_id"].nunique()),
        "this_month": int((df["visit_date"] >= month_start).sum()),
        "avg_daily_visits": round(float(daily.mean()), 1),
        "department_labels": dept.index.tolist(),
        "department_values": dept.astype(int).tolist(),
        "monthly_labels": [d.strftime("%b %Y") for d in monthly.index],
        "monthly_values": monthly.astype(int).tolist(),
        "type_labels": visit_types.index.tolist(),
        "type_values": visit_types.astype(int).tolist()
    }

def get_department_report():
    df = load_visits()
    if df.empty: return []
    result = df.groupby("department_name").agg(
        total_visits=("visit_id", "count"),
        unique_age_bands=("age_band", "nunique")
    ).reset_index().sort_values("total_visits", ascending=False)
    return result.to_dict("records")

def get_age_band_report():
    df = load_visits()
    if df.empty: return []
    result = df.groupby("age_band").size().rename("total_visits").reset_index()
    return result.to_dict("records")

def get_monthly_report():
    df = load_visits()
    if df.empty: return []
    result = df.groupby(df["visit_date"].dt.to_period("M")).size().rename("total_visits").reset_index()
    result["month"] = result["visit_date"].astype(str)
    result = result[["month", "total_visits"]]
    return result.to_dict("records")

def summary_statistics():
    df = load_visits()
    if df.empty: return {"mean": 0, "median": 0, "std": 0}
    values = df.groupby("visit_date").size().to_numpy()
    return {"mean": float(np.mean(values)), "median": float(np.median(values)),
            "std": float(np.std(values))}


def get_aggregated_export():
    """Return aggregate-only report rows; never exports individual patient records."""
    df = load_visits()
    if df.empty:
        return pd.DataFrame(columns=["department", "age_band", "visit_type", "month", "total_visits"])
    df["month"] = df["visit_date"].dt.to_period("M").astype(str)
    result = (df.groupby(["department_name", "age_band", "visit_type", "month"])
                .size().reset_index(name="total_visits"))
    return result.rename(columns={"department_name": "department"})
