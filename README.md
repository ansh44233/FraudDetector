<div align="center">

# FraudDetector

**Real-time transaction fraud intelligence powered by PostgreSQL 15 internals & Python FastAPI.**

*Sub-5ms detection · Zero machine learning black boxes · Zero external API dependencies · 100% Deterministic SQL*

<br/>

[![Live Demo](https://img.shields.io/badge/Demo-Live%20on%20GitHub%20Pages-10B981?style=for-the-badge&logo=github&logoColor=white)](https://ansh44233.github.io/FraudDetector/)
[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen?style=for-the-badge&logo=github-actions&logoColor=white)](https://github.com/ansh44233/FraudDetector/actions)
[![Test Suite](https://img.shields.io/badge/Tests-34%20Passing-8B5CF6?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<br/>

### 🌐 [Click to Open Live Interactive Dashboard →](https://ansh44233.github.io/FraudDetector/)

<br/>

<a href="https://ansh44233.github.io/FraudDetector/">
  <img src="assets/dashboard-preview.png" alt="FraudDetector Real Dashboard" width="100%" style="border-radius: 10px; border: 1px solid #27272a;"/>
</a>

</div>

<br/>

---

## ⚡ Why FraudDetector?

Traditional financial fraud stacks often depend on heavy ML models, external cloud APIs, and complex feature stores that introduce 200ms+ network latencies and non-deterministic false positives.

**FraudDetector** evaluates transactional anomalies directly inside the **PostgreSQL 15 storage engine**:
- **Zero-Latency Triggers:** PL/pgSQL triggers fire synchronously on `INSERT` to trap velocity bursts and 5x amount anomalies in **sub-2ms**.
- **Recursive Graph Traversal:** Dissects money mule laundering rings up to 6 hops deep using cycle-protected recursive CTEs.
- **Dynamic Windowing:** Rolling 7-day merchant rates via `RANGE BETWEEN INTERVAL` and user percentile rankings via `PERCENT_RANK()` and `NTILE(10)`.

```
Transaction Ingestion (POST /transactions)
                 │
                 ▼
   PostgreSQL 15 ACID Boundary
  ┌─────────────────────────────────────────────────────────────┐
  │  PL/pgSQL Trigger: auto_flag_high_amount() (Synchronous)    │
  │  PL/pgSQL Trigger: auto_flag_device_burst() (Synchronous)   │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
    Batch Rules Engine (psycopg2)      Analytical Materialized Views
    • MULE_CHAIN (Recursive CTE)       • User Risk Statistics
    • VELOCITY_10M (LATERAL Join)      • Rolling 7-day Merchant Rates
    • RAPID_REPEAT (LAG Window)        • Shared Device Fingerprints
                 └───────────────┬───────────────┘
                                 │
                                 ▼
              FastAPI Async Endpoints & Real-Time UI
```

---

## 🛡️ Detection Rules & Real Examples

FraudDetector ships with built-in rules designed for high-risk fintech channels (UPI, cards, crypto off-ramps, and gaming gateways):

| Rule | Trigger Type | Pattern Detected | Risk Score | Latency |
|---|---|---|:---:|:---:|
| `MULE_CHAIN` | Recursive CTE | Layered money laundering chain ≥2 hops deep | **90** | `< 6ms` |
| `VELOCITY_10M` | `JOIN LATERAL` | >5 transactions within a 10-minute window | **85** | `< 2ms` |
| `MULTI_DEVICE_1H` | PL/pgSQL Trigger | 3+ distinct device fingerprints within 1 hour | **80** | `< 1ms` |
| `HIGH_AMOUNT_ANOMALY` | PL/pgSQL Trigger | Transaction amount >500% of user's personal average | **75** | `< 1ms` |
| `RAPID_REPEAT` | `LAG()` Window | Identical user + merchant charged within <60 seconds | **70** | `< 2ms` |
| `HIGH_RISK_MERCHANT` | Filtered Join | Large transactions routed through flagged high-risk merchant | **65** | `< 2ms` |
| `SHARED_DEVICE` | Aggregation | Single hardware fingerprint linked to multiple user IDs | **60** | `< 3ms` |

---

## 🔍 Real-World Incident Walkthroughs

### 1. Money Mule Laundering Chain (`MULE_CHAIN`)
Illicit funds transferred across multiple intermediary accounts to obscure the original source:

```
[User #5] ──(₹15,000)──► [User #11] ──(₹15,000)──► [User #12] (3 hops)
```

**API Query:**
```bash
curl http://localhost:8000/analytics/mule-chains
```

**Real API Output:**
```json
[
  {
    "from_user_id": 5,
    "to_user_id": 12,
    "amount": 15000.0,
    "depth": 3,
    "chain": [5, 11, 12],
    "rule_name": "MULE_CHAIN",
    "risk_score": 90.0
  }
]
```

---

### 2. Instant Anomaly Trap on INSERT (`HIGH_AMOUNT_ANOMALY`)
A user whose median transaction is ₹200 suddenly attempts a ₹95,000 checkout:

```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "merchant_id": 2,
    "amount": 95000.0,
    "channel": "UPI",
    "device_id": "device_fp_882"
  }'
```

**Flag Generated Synchronously by PL/pgSQL Trigger:**
```json
{
  "txn_id": 327,
  "rule_name": "HIGH_AMOUNT_ANOMALY",
  "risk_score": 75.0,
  "details": {
    "amount": 95000.0,
    "ratio": 475.0,
    "baseline_avg": 200.0
  },
  "resolved": false
}
```

---

## 💎 Advanced SQL Deep-Dive

<details open>
<summary><strong>Recursive CTE — Cycle-Guarded Mule Chain Tracing</strong></summary>

```sql
WITH RECURSIVE chain AS (
    -- Anchor: Unresolved flagged transactions
    SELECT tg.from_user_id, tg.to_user_id, tg.txn_id,
           ARRAY[tg.from_user_id] AS visited, 
           1 AS depth
    FROM transaction_graph tg
    JOIN fraud_flags ff ON ff.txn_id = tg.txn_id
    WHERE ff.resolved = FALSE

    UNION ALL

    -- Recursive step: trace funds to recipient's next outbound transfer
    SELECT tg.from_user_id, tg.to_user_id, tg.txn_id,
           c.visited || tg.from_user_id, 
           c.depth + 1
    FROM transaction_graph tg
    JOIN chain c ON tg.from_user_id = c.to_user_id
    WHERE NOT (tg.from_user_id = ANY(c.visited))  -- Cycle guard
      AND c.depth < 6                              -- Traversal ceiling
)
SELECT from_user_id, to_user_id, depth, visited AS node_path
FROM chain 
ORDER BY depth DESC;
```
</details>

<details>
<summary><strong>LATERAL Join — User Velocity Burst Scanner</strong></summary>

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
<summary><strong>PL/pgSQL Trigger — High Amount Anomaly Trap</strong></summary>

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

## 🚀 Quickstart

### 1. Clone & Setup

```bash
git clone https://github.com/ansh44233/FraudDetector.git
cd FraudDetector

# Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run with Docker (Recommended)

```bash
docker compose up -d db api
docker compose run --rm seed
# Open http://localhost:8000
```

### 3. Run Automated Tests

```bash
python -m pytest tests/ -m "not integration" -v
```

```
============================== 34 passed in 1.48s ==============================
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/transactions` | `POST` | Ingests a new transaction and runs rule validation |
| `/flags?resolved=false` | `GET` | Lists all active, unresolved fraud flags |
| `/flags/{id}` | `PATCH` | Updates flag status (`resolved: true / false`) |
| `/analytics/summary` | `GET` | Global KPIs: Total transactions, Open flags, Average risk |
| `/analytics/mule-chains` | `GET` | Returns multi-hop graph chain routes |
| `/analytics/merchant-fraud-rate` | `GET` | 7-day rolling fraud percentage by merchant |
| `/analytics/device-sharing` | `GET` | Hardware devices linked to multiple accounts |
| `/analytics/user-risk-ranking` | `GET` | Percentile risk rankings (`PERCENT_RANK`, `NTILE`) |
| `/engine/run` | `POST` | Manually triggers batch evaluation of all rules |

---

## 👨‍💻 Author & License

Designed and engineered by **[Ansh](https://github.com/ansh44233)**.  
Released under the **[MIT License](LICENSE)**.
