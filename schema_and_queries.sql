-- ============================================================
--  BOM Supply Chain Analytics — SQL Schema & Queries
--  PT Solutions Portfolio Project
-- ============================================================


-- ────────────────────────────────────────────
-- SCHEMA
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS components (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number     TEXT NOT NULL,
    description     TEXT,
    category        TEXT,           -- Microcontroller, Power Mgmt, Memory, etc.
    manufacturer    TEXT,           -- TI, STMicro, NXP, Infineon, etc.
    supplier        TEXT,           -- Arrow, Avnet, Mouser, PT Solutions, etc.
    industry        TEXT,           -- Automotive, Industrial, Medical, etc.
    lifecycle       TEXT,           -- Active / NRND / Obsolete / EOL
    unit_price_usd  REAL,
    quantity        INTEGER,
    total_cost_usd  REAL,           -- unit_price * quantity
    lead_time_wks   INTEGER,        -- supplier lead time in weeks
    last_updated    TEXT            -- YYYY-MM-DD
);

CREATE TABLE IF NOT EXISTS risk_flags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number TEXT NOT NULL,
    risk_type   TEXT,   -- 'Lifecycle' | 'Lead Time' | 'Supplier Concentration'
    severity    TEXT,   -- 'HIGH' | 'MEDIUM' | 'LOW'
    note        TEXT,
    flagged_at  TEXT    -- YYYY-MM-DD
);


-- ────────────────────────────────────────────
-- QUERY 1: KPI SUMMARY (Power BI card visuals)
-- ────────────────────────────────────────────

SELECT
    COUNT(*)                                            AS total_parts,
    ROUND(SUM(total_cost_usd), 2)                       AS total_spend_usd,
    ROUND(AVG(unit_price_usd), 3)                       AS avg_unit_price,
    ROUND(AVG(lead_time_wks), 1)                        AS avg_lead_time_wks,
    SUM(CASE WHEN lifecycle IN ('Obsolete','EOL','NRND')
             THEN 1 ELSE 0 END)                         AS at_risk_parts,
    ROUND(
        SUM(CASE WHEN lifecycle IN ('Obsolete','EOL','NRND')
                 THEN 1.0 ELSE 0 END) / COUNT(*) * 100
    , 1)                                                AS pct_at_risk
FROM components;


-- ────────────────────────────────────────────
-- QUERY 2: SPEND BY CATEGORY
-- (Bar chart in Power BI)
-- ────────────────────────────────────────────

SELECT
    category,
    COUNT(*)                        AS part_count,
    ROUND(SUM(total_cost_usd), 2)   AS total_spend,
    ROUND(AVG(unit_price_usd), 3)   AS avg_unit_price,
    ROUND(AVG(lead_time_wks), 1)    AS avg_lead_time_wks
FROM components
GROUP BY category
ORDER BY total_spend DESC;


-- ────────────────────────────────────────────
-- QUERY 3: SUPPLIER CONCENTRATION RISK
-- (Pie chart — flag if any supplier > 30% spend)
-- ────────────────────────────────────────────

SELECT
    supplier,
    COUNT(*)                                                AS part_count,
    ROUND(SUM(total_cost_usd), 2)                           AS total_spend,
    ROUND(
        SUM(total_cost_usd) * 100.0 /
        (SELECT SUM(total_cost_usd) FROM components)
    , 1)                                                    AS spend_pct,
    CASE
        WHEN SUM(total_cost_usd) * 100.0 /
             (SELECT SUM(total_cost_usd) FROM components) > 30
        THEN 'HIGH RISK'
        WHEN SUM(total_cost_usd) * 100.0 /
             (SELECT SUM(total_cost_usd) FROM components) > 20
        THEN 'MEDIUM RISK'
        ELSE 'OK'
    END AS concentration_risk
FROM components
GROUP BY supplier
ORDER BY total_spend DESC;


-- ────────────────────────────────────────────
-- QUERY 4: LIFECYCLE RISK BREAKDOWN
-- (Donut chart)
-- ────────────────────────────────────────────

SELECT
    lifecycle,
    COUNT(*)                        AS part_count,
    ROUND(SUM(total_cost_usd), 2)   AS total_spend,
    ROUND(AVG(lead_time_wks), 1)    AS avg_lead_time_wks
FROM components
GROUP BY lifecycle
ORDER BY
    CASE lifecycle
        WHEN 'Obsolete' THEN 1
        WHEN 'EOL'      THEN 2
        WHEN 'NRND'     THEN 3
        WHEN 'Active'   THEN 4
    END;


-- ────────────────────────────────────────────
-- QUERY 5: LONG LEAD TIME PARTS (> 20 weeks)
-- (Table visual with conditional formatting)
-- ────────────────────────────────────────────

SELECT
    part_number,
    description,
    manufacturer,
    supplier,
    category,
    lifecycle,
    lead_time_wks,
    unit_price_usd,
    quantity,
    total_cost_usd,
    CASE
        WHEN lead_time_wks > 40 THEN '🔴 Critical'
        WHEN lead_time_wks > 28 THEN '🟡 Warning'
        ELSE '🟢 OK'
    END AS lead_time_status
FROM components
WHERE lead_time_wks > 20
ORDER BY lead_time_wks DESC;


-- ────────────────────────────────────────────
-- QUERY 6: SPEND BY INDUSTRY
-- (Treemap in Tableau)
-- ────────────────────────────────────────────

SELECT
    industry,
    category,
    ROUND(SUM(total_cost_usd), 2)   AS total_spend,
    COUNT(*)                        AS part_count
FROM components
GROUP BY industry, category
ORDER BY total_spend DESC;


-- ────────────────────────────────────────────
-- QUERY 7: MANUFACTURER DEPENDENCY
-- (Identify if too many parts from one mfr)
-- ────────────────────────────────────────────

SELECT
    manufacturer,
    COUNT(*)                        AS part_count,
    ROUND(SUM(total_cost_usd), 2)   AS total_spend,
    COUNT(DISTINCT category)        AS categories_covered,
    ROUND(
        SUM(total_cost_usd) * 100.0 /
        (SELECT SUM(total_cost_usd) FROM components)
    , 1)                            AS spend_pct
FROM components
GROUP BY manufacturer
ORDER BY total_spend DESC;


-- ────────────────────────────────────────────
-- QUERY 8: FULL RISK DASHBOARD VIEW
-- (Join components + risk flags)
-- ────────────────────────────────────────────

SELECT
    c.part_number,
    c.description,
    c.category,
    c.manufacturer,
    c.supplier,
    c.lifecycle,
    c.unit_price_usd,
    c.quantity,
    c.total_cost_usd,
    c.lead_time_wks,
    COUNT(r.id)                     AS total_flags,
    GROUP_CONCAT(r.severity, ', ')  AS severities,
    GROUP_CONCAT(r.risk_type, ', ') AS risk_types
FROM components c
LEFT JOIN risk_flags r ON c.part_number = r.part_number
GROUP BY c.part_number
ORDER BY total_flags DESC, c.total_cost_usd DESC;
