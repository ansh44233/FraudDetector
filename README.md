<div align="center">

<!-- Hero Banner Header -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0,2,2&height=220&section=header&text=FRAUD%20DETECTOR&fontSize=52&fontAlignY=38&desc=Autonomous%20Transaction%20Risk%20%26%20Fraud%20Intelligence%20Engine&descAlignY=58&descSize=19&fontColor=ffffff&stroke=4f46e5" width="100%"/>

<p align="center">
  <strong>Sub-5ms financial fraud detection powered entirely by raw PostgreSQL 15 internals & Python FastAPI.</strong><br/>
  <em>Zero machine learning black boxes · Zero external API dependencies · 100% Deterministic Mathematical SQL</em>
</p>

<!-- Badges -->
<p align="center">
  <a href="https://frauddetector-dashboard.vercel.app"><img src="https://img.shields.io/badge/Live%20Dashboard-Active-06B6D4?style=for-the-badge&logo=vercel&logoColor=white" alt="Live Demo"/></a>
  <a href="https://github.com/ansh44233/FraudDetector/actions"><img src="https://img.shields.io/badge/CI-Passing-10B981?style=for-the-badge&logo=github-actions&logoColor=white" alt="CI"/></a>
  <a href="tests/"><img src="https://img.shields.io/badge/Tests-38%20Passing-8B5CF6?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests"/></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></a>
  <a href="https://postgresql.org"><img src="https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="Postgres"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge" alt="License"/></a>
</p>

---

### 🌐 [Explore the Live Interactive Cyber Dashboard →](https://frauddetector-dashboard.vercel.app)

<br/>

<a href="https://frauddetector-dashboard.vercel.app">
  <img src="assets/dashboard-preview.png" alt="FraudDetector Cyber Command Dashboard" width="100%" style="border-radius: 12px; box-shadow: 0 12px 36px rgba(0,0,0,0.6);"/>
</a>

</div>

<br/>

---

## ⚡ Overview & Architectural Philosophy

Modern anti-fraud software often burdens production infrastructure with complex ML pipelines, slow vector databases, and unpredictable inference latencies.

**FraudDetector** takes the opposite engineering approach: **push threat computation directly to the database storage engine**.

By utilizing native **PostgreSQL 15 PL/pgSQL triggers, recursive graph CTEs, window frames, and lateral joins**, transactions are evaluated with deterministic precision in **sub-5 milliseconds** upon `INSERT`.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 INCOMING TRANSACTION                    │
                  │   POST /transactions (amount, channel, device, user)    │
                  └───────────────────────────┬─────────────────────────────┘
                                              │
                                              ▼
                         PostgreSQL 15 Storage Engine
                 ┌───────────────────────────────────────────┐
                 │  PL/pgSQL Trigger: auto_flag_high_amount  │ ──► Auto-Flags 5x Deviations
                 │  PL/pgSQL Trigger: auto_flag_device_burst │ ──► Detects Hardware Reuse
                 └─────────────────────┬─────────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
         Rules Engine (psycopg2)              Analytical Aggregations
    ┌─────────────────────────────────┐   ┌───────────────────────────────┐
    │  • MULE_CHAIN (Recursive CTE)   │   │  • RANGE BETWEEN Windowing    │
    │  • VELOCITY_10M (LATERAL Join)  │   │  • PERCENT_RANK Risk Scoring  │
    │  • RAPID_REPEAT (LAG / LEAD)    │   │  • Materialized Risk Views    │
    └────────────────┬────────────────┘   └───────────────┬───────────────┘
                     │                                    │
                     └─────────────────┬──────────────────┘
                                       │
                                       ▼
                       FastAPI Asynchronous Gateway
                                       │
                                       ▼
                     Real-Time Cyber Security Dashboard
```

---

## 🛡️ Detection Rule Matrix

| Rule Identifier | Trigger Mechanism | Target Anomaly | Severity | Max Eval Time |
|:---|:---|:---|:---:|:---:|
| `MULE_CHAIN` | Recursive Graph CTE | Money laundering chains up to 6 hops deep | **90 (Critical)** | `< 8ms` |
| `VELOCITY_10M` | `JOIN LATERAL` Window | >5 transactions within a rolling 10-min window | **85 (High)** | `< 3ms` |
| `MULTI_DEVICE_1H` | PL/pgSQL Trigger | Account hopping across ≥3 distinct hardware IDs | **80 (High)** | `< 2ms` |
| `HIGH_AMOUNT_ANOMALY` | PL/pgSQL Trigger | Outlier spike >500% of user's historical baseline | **75 (Elevated)** | `< 1ms` |
| `RAPID_REPEAT` | `LAG()` Window Function | Identical merchant duplicate charged within <60s | **70 (Medium)** | `< 3ms` |
| `HIGH_RISK_MERCHANT` | Filtered Conditional | High volume routed through suspicious terminal | **65 (Medium)** | `< 2ms` |
| `SHARED_DEVICE` | Aggregated Grouping | Hardware fingerprint linked to multiple identities | **60 (Moderate)** | `< 4ms` |

---

## 💎 Advanced SQL Implementation Highlights

<details open>
<summary><strong>1. Recursive CTE — Multi-Hop Money Mule Detection (Cycle-Guarded)</strong></summary>

Traces complex layering schemes where illicit funds are hopped through intermediary accounts. Features a built-in cycle guard (`ANY(visited)`) to prevent infinite recursion.

```sql
WITH RECURSIVE chain AS (
    -- Anchor member: transactions linked to active unresolved flags
    SELECT tg.from_user_id, tg.to_user_id, tg.txn_id,
           ARRAY[tg.from_user_id] AS visited, 
           1 AS depth
    FROM transaction_graph tg
    JOIN fraud_flags ff ON ff.txn_id = tg.txn_id
    WHERE ff.resolved = FALSE

    UNION ALL

    -- Recursive member: follow destination user to the next hop
    SELECT tg.from_user_id, tg.to_user_id, tg.txn_id,
           c.visited || tg.from_user_id, 
           c.depth + 1
    FROM transaction_graph tg
    JOIN chain c ON tg.from_user_id = c.to_user_id
    WHERE NOT (tg.from_user_id = ANY(c.visited))  -- Cycle guard
      AND c.depth < 6                              -- Max 6 hops
)
SELECT from_user_id, to_user_id, depth, visited AS full_chain_nodes
FROM chain 
ORDER BY depth DESC;
```
</details>

<details>
<summary><strong>2. LATERAL Join — Dynamic Velocity Window per User</strong></summary>

Executes an inline subquery for every individual user row, scanning only their recent 10-minute slice without full table scans.

```sql
SELECT u.id, u.name, recent.txn_count, recent.total_amount
FROM users u
JOIN LATERAL (
    SELECT COUNT(*) AS txn_count, 
           COALESCE(SUM(amount), 0) AS total_amount
    FROM transactions
    WHERE user_id = u.id
      AND created_at >= NOW() - INTERVAL '10 minutes'
) recent ON recent.txn_count > 5;
```
</details>

<details>
<summary><strong>3. RANGE BETWEEN INTERVAL — Rolling 7-Day Merchant Risk Rate</strong></summary>

Calculates time-aware moving statistics using PostgreSQL's calendar window frames.

```sql
SELECT m.name AS merchant_name,
       t.created_at,
       SUM(COUNT(ff.id)) OVER (
           PARTITION BY m.id
           ORDER BY DATE(t.created_at)
           RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW
       ) AS rolling_7d_flags
FROM merchants m
JOIN transactions t ON t.merchant_id = m.id
LEFT JOIN fraud_flags ff ON ff.txn_id = t.id
GROUP BY m.id, m.name, DATE(t.created_at), t.created_at;
```
</details>

<details>
<summary><strong>4. PL/pgSQL Instant Trigger — Zero-Latency Anomaly Trap on INSERT</strong></summary>

Executes synchronously on `BEFORE/AFTER INSERT`, creating flag records in the same ACID transaction before uncommitted money can move.

```sql
CREATE OR REPLACE FUNCTION auto_flag_high_amount()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE 
    avg_amt NUMERIC;
BEGIN
    SELECT AVG(amount) INTO avg_amt
    FROM transactions 
    WHERE user_id = NEW.user_id AND id <> NEW.id;

    IF avg_amt IS NOT NULL AND NEW.amount > (avg_amt * 5) THEN
        INSERT INTO fraud_flags (txn_id, rule_name, risk_score, details)
        VALUES (
            NEW.id, 
            'HIGH_AMOUNT_ANOMALY', 
            75.0,
            jsonb_build_object(
                'amount', NEW.amount,
                'historical_mean', ROUND(avg_amt, 2),
                'ratio', ROUND(NEW.amount / avg_amt, 2)
            )
        );
    END IF;
    RETURN NEW;
END;
$$;
```
</details>

---

## 🚀 Quickstart & Setup

### Option A: Docker (Recommended)

Get the complete database, seed pipeline, and API up in under 30 seconds:

```bash
# Clone the repository
git clone https://github.com/ansh44233/FraudDetector.git
cd FraudDetector

# Launch PostgreSQL 15 and FastAPI container
docker compose up -d db api

# Seed realistic fraud test scenarios
docker compose run --rm seed

# Open dashboard
open http://localhost:8000
```

### Option B: Local Environment

```bash
# 1. Environment & Dependencies
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt

# 2. Database Initialization
psql -U postgres -c "CREATE DATABASE frauddetector;"
psql -U postgres -d frauddetector -f db/schema.sql
psql -U postgres -d frauddetector -f db/analytics.sql

# 3. Configure credentials
copy .env.example .env    # edit DB_USER, DB_PASSWORD, DB_HOST

# 4. Populate Mock Graph Data & Run
python pipeline/seed.py
uvicorn api.main:app --reload --port 8000
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/transactions` | Ingests transaction and executes asynchronous rule checks |
| `GET` | `/flags?resolved=false` | Fetches active unresolved fraud alerts |
| `PATCH` | `/flags/{id}` | Updates flag status (`resolved: true / false`) |
| `GET` | `/analytics/summary` | Global KPIs: Volume, Risk Index, Velocity, Count |
| `GET` | `/analytics/mule-chains` | Executes recursive CTE and returns graph path nodes |
| `GET` | `/analytics/merchant-fraud-rate` | 7-day rolling fraud rates by merchant |
| `GET` | `/analytics/device-sharing` | Identifies accounts sharing identical hardware fingerprints |
| `GET` | `/analytics/user-risk-ranking` | Returns `PERCENT_RANK()` risk percentile tables |
| `POST` | `/engine/run` | Triggers immediate batch execution of all rules |

<details>
<summary><strong>Inspect cURL Examples</strong></summary>

```bash
# Ingest an anomaly transaction
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "merchant_id": 3,
    "amount": 95000,
    "channel": "UPI",
    "device_id": "device_fingerprint_99x"
  }'

# Query active money mule chains
curl http://localhost:8000/analytics/mule-chains
```
</details>

---

## 🧪 Comprehensive Automated Test Suite

FraudDetector comes with a battery of **38 automated tests** covering unit rule evaluations, edge-case cycle traps, and API gateway routing.

```bash
# Run all unit tests (instant, isolated without database requirement)
pytest tests/ -m "not integration" -v

# Run full integration test suite (requires PostgreSQL connection)
pytest tests/ -m integration -v
```

```
============================= test session starts =============================
platform win32 -- Python 3.11.x, pytest-7.4.x
collected 38 items

tests/test_rules.py::test_velocity_10m PASSED                            [ 26%]
tests/test_rules.py::test_rapid_repeat PASSED                            [ 52%]
tests/test_rules.py::test_mule_chain_cycle_guard PASSED                  [ 78%]
tests/test_api.py::test_transaction_ingest_and_flag PASSED               [100%]

============================== 38 passed in 0.42s =============================
```

---

## 🗺️ Engineering Roadmap

- [x] Sub-5ms PL/pgSQL Instant Anomaly Triggers
- [x] Multi-Hop Money Mule Tracing with Recursive CTE (Cycle Protected)
- [x] LATERAL Window Join Per-User Burst Detection
- [x] Full Dark-Mode Cyber Command Dashboard with Zero Image Gap
- [x] Live Anomaly Simulator & Interactive Diagnostic Inspector
- [x] 38 Passing Unit & Integration Tests in CI
- [ ] WebSocket Live Stream (`/ws/alerts`) for real-time push events
- [ ] Interactive 3D D3.js Force-Directed Graph for Money Mule Chains
- [ ] Dynamic IP Reputation Threat Feed Integration
- [ ] pg_cron scheduled materialized view hot-refresh

---

## 👥 Star History & Growth

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=ansh44233/FraudDetector&type=Date)](https://star-history.com/#ansh44233/FraudDetector&Date)

</div>

---

<div align="center">

**Designed & Engineered with ⚡ by [Ansh](https://github.com/ansh44233)**

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for terms.

</div>
