"""
BOM Supply Chain Analytics
PT Solutions - Semiconductor Component Dashboard
"""

import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta


#1 generate synthetic BOM dataset

random.seed(42)

MANUFACTURERS = ["Texas Instruments", "STMicroelectronics", "NXP", "Infineon",
                 "Renesas", "Microchip", "ON Semiconductor", "ROHM", "Vishay"]

CATEGORIES = ["Microcontroller", "Power Management", "Memory", "Connectivity",
              "Analog IC", "Passive Component", "Sensor", "Logic IC"]

LIFECYCLE = ["Active", "Active", "Active", "NRND", "Obsolete", "EOL"]  # weighted toward Active

SUPPLIERS = ["Arrow Electronics", "Avnet", "Mouser", "Digi-Key",
             "Future Electronics", "PT Solutions"]

INDUSTRIES = ["Automotive", "Industrial Automation", "Consumer Electronics",
              "Financial Services", "Renewable Energy", "Medical"]

def random_part_number():
    prefix = random.choice(["TI", "ST", "NXP", "IFX", "REN", "MCH"])
    return f"{prefix}-{random.randint(1000,9999)}-{'ABCDE'[random.randint(0,4)]}"

def generate_bom(n=300):
    rows = []
    for i in range(n):
        mfr = random.choice(MANUFACTURERS)
        category = random.choice(CATEGORIES)
        lifecycle = random.choice(LIFECYCLE)
        unit_price = round(random.uniform(0.05, 85.0), 3)
        quantity = random.randint(10, 5000)
        lead_time = random.randint(4, 52)  # weeks
        last_updated = datetime.now() - timedelta(days=random.randint(0, 365))

        # Obsolete parts tend to have higher prices and longer lead times
        if lifecycle in ["Obsolete", "EOL"]:
            unit_price *= random.uniform(1.5, 4.0)
            lead_time += random.randint(8, 24)

        rows.append({
            "part_number":    random_part_number(),
            "description":    f"{category} - {mfr[:3]} series",
            "category":       category,
            "manufacturer":   mfr,
            "supplier":       random.choice(SUPPLIERS),
            "industry":       random.choice(INDUSTRIES),
            "lifecycle":      lifecycle,
            "unit_price_usd": round(unit_price, 3),
            "quantity":       quantity,
            "total_cost_usd": round(unit_price * quantity, 2),
            "lead_time_wks":  lead_time,
            "last_updated":   last_updated.strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(rows)


#2 database setup and data loading

def init_db(db_path="bom_supply_chain.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS components (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number     TEXT NOT NULL,
            description     TEXT,
            category        TEXT,
            manufacturer    TEXT,
            supplier        TEXT,
            industry        TEXT,
            lifecycle       TEXT,
            unit_price_usd  REAL,
            quantity        INTEGER,
            total_cost_usd  REAL,
            lead_time_wks   INTEGER,
            last_updated    TEXT
        );

        CREATE TABLE IF NOT EXISTS risk_flags (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number     TEXT NOT NULL,
            risk_type       TEXT,
            severity        TEXT,
            note            TEXT,
            flagged_at      TEXT
        );
    """)
    conn.commit()
    return conn


def load_data(conn, df):
    df.to_sql("components", conn, if_exists="replace", index=False)
    print(f"Loaded {len(df)} components into database")


#3 analysis and risk flagging

def run_analysis(conn):
    print("\n" + "="*55)
    print(" BOM SUPPLY CHAIN ANALYSIS REPORT")
    print("="*55)

    #  KPI Summary 
    kpis = pd.read_sql("""
        SELECT
            COUNT(*)                                        AS total_parts,
            ROUND(SUM(total_cost_usd), 2)                  AS total_spend_usd,
            ROUND(AVG(unit_price_usd), 3)                  AS avg_unit_price,
            ROUND(AVG(lead_time_wks), 1)                   AS avg_lead_time_wks,
            SUM(CASE WHEN lifecycle IN ('Obsolete','EOL','NRND') THEN 1 ELSE 0 END) AS at_risk_parts
        FROM components
    """, conn)
    print("\nKPIs")
    print(kpis.to_string(index=False))

    #  Spend by Category 
    by_cat = pd.read_sql("""
        SELECT category,
               COUNT(*)                       AS parts,
               ROUND(SUM(total_cost_usd), 2)  AS total_spend,
               ROUND(AVG(lead_time_wks), 1)   AS avg_lead_wks
        FROM components
        GROUP BY category
        ORDER BY total_spend DESC
    """, conn)
    print("\nSpend by Category")
    print(by_cat.to_string(index=False))

    #  Supplier Concentration Risk 
    supplier_risk = pd.read_sql("""
        SELECT supplier,
               COUNT(*)                                         AS parts,
               ROUND(SUM(total_cost_usd), 2)                   AS total_spend,
               ROUND(SUM(total_cost_usd)*100.0 /
                   (SELECT SUM(total_cost_usd) FROM components), 1) AS spend_pct
        FROM components
        GROUP BY supplier
        ORDER BY total_spend DESC
    """, conn)
    print("\nSupplier Concentration")
    print(supplier_risk.to_string(index=False))

    #Lifecycle Risk
    lifecycle = pd.read_sql("""
        SELECT lifecycle,
               COUNT(*)                        AS parts,
               ROUND(SUM(total_cost_usd), 2)   AS total_spend,
               ROUND(AVG(lead_time_wks), 1)    AS avg_lead_wks
        FROM components
        GROUP BY lifecycle
        ORDER BY parts DESC
    """, conn)
    print("\nLifecycle Risk Breakdown")
    print(lifecycle.to_string(index=False))

    #top 10 Obsolete/EOL + high spend
    risky = pd.read_sql("""
        SELECT part_number, manufacturer, category,
               lifecycle, unit_price_usd, quantity,
               total_cost_usd, lead_time_wks
        FROM components
        WHERE lifecycle IN ('Obsolete', 'EOL')
        ORDER BY total_cost_usd DESC
        LIMIT 10
    """, conn)
    print("\ntop 10 Obsolete/EOL by spend")
    print(risky.to_string(index=False))

    
    risky_all = pd.read_sql("""
        SELECT part_number, lifecycle, lead_time_wks
        FROM components
        WHERE lifecycle IN ('Obsolete','EOL','NRND') OR lead_time_wks > 30
    """, conn)

    flags = []
    for _, row in risky_all.iterrows():
        if row["lifecycle"] in ["Obsolete", "EOL"]:
            flags.append((row["part_number"], "Lifecycle", "HIGH",
                          f"Part is {row['lifecycle']} — source alternative now",
                          datetime.now().strftime("%Y-%m-%d")))
        elif row["lifecycle"] == "NRND":
            flags.append((row["part_number"], "Lifecycle", "MEDIUM",
                          "Not Recommended for New Designs — plan replacement",
                          datetime.now().strftime("%Y-%m-%d")))
        if row["lead_time_wks"] > 30:
            flags.append((row["part_number"], "Lead Time", "HIGH",
                          f"{row['lead_time_wks']} week lead time — consider safety stock",
                          datetime.now().strftime("%Y-%m-%d")))

    cur = conn.cursor()
    cur.execute("DELETE FROM risk_flags")
    cur.executemany(
        "INSERT INTO risk_flags (part_number, risk_type, severity, note, flagged_at) VALUES (?,?,?,?,?)",
        flags
    )
    conn.commit()
    print(f"\n{len(flags)} risk flags written to risk_flags table")

    return by_cat, supplier_risk, lifecycle


#4 export CSVs for Power BI
def export_csvs(conn):
    tables = ["components", "risk_flags"]
    for t in tables:
        df = pd.read_sql(f"SELECT * FROM {t}", conn)
        path = f"{t}.csv"
        df.to_csv(path, index=False)
        print(f"Exported {path} ({len(df)} rows)")

    # Aggregated view for dashboard
    agg = pd.read_sql("""
        SELECT
            c.category,
            c.manufacturer,
            c.supplier,
            c.industry,
            c.lifecycle,
            COUNT(*)                       AS part_count,
            ROUND(SUM(c.total_cost_usd),2) AS total_spend,
            ROUND(AVG(c.lead_time_wks),1)  AS avg_lead_wks,
            COUNT(r.id)                    AS risk_flag_count
        FROM components c
        LEFT JOIN risk_flags r ON c.part_number = r.part_number
        GROUP BY c.category, c.manufacturer, c.supplier, c.industry, c.lifecycle
    """, conn)
    agg.to_csv("bom_aggregated.csv", index=False)
    print(f"Exported bom_aggregated.csv ({len(agg)} rows) — use this in Power BI")


#main
if __name__ == "__main__":
    print(" Generating BOM dataset")
    df = generate_bom(300)

    print("initializing database")
    conn = init_db()
    load_data(conn, df)

    print("running analysis")
    run_analysis(conn)

    print("\nExporting CSVs for Power BI")
    export_csvs(conn)

    conn.close()
    print("\nDone")
