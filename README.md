# Semiconductor BOM Supply Chain Analytics

---

## Project Overview

An end-to-end data analysis pipeline that ingests a Bill of Materials (BOM),
stores it in a relational database, runs supply chain risk analysis, and
exports clean datasets for Power BI and Tableau dashboards.

---

## Tech Stack

| Layer       | Tool                  |
|-------------|----------------------|
| Ingestion   | Python 3 + Pandas     |
| Storage     | SQLite (swap for PostgreSQL in production) |
| Analysis    | SQL + Pandas          |
| Dashboard   | Power BI / Tableau    |

---

## How to Run

```bash
# 1. Install dependencies
pip install pandas

# 2. Run the pipeline
python bom_analysis.py

---

## Power BI Dashboard


| Visual         | Fields                              |
|----------------|--------------------------------------|
| KPI Cards      | total_parts, total_spend, at_risk %  |
| Bar Chart      | total_spend by category              |
| Pie/Donut      | part_count by lifecycle              |
| Table          | High-risk parts with conditional fmt |
| Treemap        | spend by industry + category         |
| Supplier Risk  | spend_pct by supplier (flag >30%)    |

---

## Key Findings using sample data
![My Image](https://github.com/Padole05/semiconductor-BOM-supply-chain-analytics/blob/main/image.png)
- 398 total components across 8 categories
- $71.95M total BOM spend
- 60% of components are at risk (EOL: 22.9%, NRND: 22.4%, Obsolete: 14.8%)
- Analog IC and Sensor are the highest spend categories
- Average lead time of 33.3 weeks across all parts
- 313 risk flags generated across lifecycle and lead time issues
- No single supplier dominates — concentration fairly distributed (~12–20% each)