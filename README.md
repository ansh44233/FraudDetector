<div align="center">

# 🛡️ FraudDetector

**Real-time fraud detection engine — Python · PostgreSQL · FastAPI**

</div>

<div align="center">

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen?style=flat&logo=vercel)](https://frauddetector-dashboard.vercel.app)
[![CI](https://github.com/ansh44233/FraudDetector/actions/workflows/ci.yml/badge.svg)](https://github.com/ansh44233/FraudDetector/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-30%20passing-brightgreen?style=flat)](tests/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat)](LICENSE)

</div>

---

<div align="center">

![FraudDetector Dashboard](assets/dashboard-preview.png)

</div>

---

Fraud detection backend built entirely on advanced PostgreSQL — no ML black boxes, no external services. Detects velocity bursts, money mule chains, device sharing, high-risk merchant patterns, and high-amount anomalies in real time. Everything runs through a rules engine backed by raw SQL: recursive CTEs, `LATERAL` joins, `LAG`/`LEAD` window functions, `RANGE BETWEEN` rolling windows, `PERCENT_RANK`, `NTILE`, and materialized views.

**[Live demo →](https://frauddetector-dashboard.vercel.app)**

```
transaction insert → DB triggers → rules engine → fraud_flags → live dashboard
```

---

## Advanced SQL used

| Technique | Where |
|---|---|
| Recursive CTE | Money mule chain tracing (up to 6 hops) |
| `LATERAL` join | Per-user velocity window, rapid-repeat detection |
| `LAG` / `LEAD` | Time gap between consecutive transactions |
| `RANGE BETWEEN` | Rolling 7-day merchant fraud rate |
| `PERCENT_RANK` + `NTILE` | User risk percentile ranking |
| `DENSE_RANK` | Global fraud leaderboard |
| Materialized view | Pre-computed user risk stats (refresh on demand) |
| PL/pgSQL triggers | Auto-flag high-amount anomalies + multi-device switches |
| `JSONB` | Structured flag details (ratio, device count, chain depth) |
| `LATERAL` + `ARRAY_AGG` | Device sharing detection |

---

## Fraud patterns detected

| Pattern | Rule | Risk score |
|---|---|---|
| >5 transactions in 10 minutes | `VELOCITY_10M` | 85 |
| Same user+merchant repeat < 60s | `RAPID_REPEAT` | 70 |
| Amount > 5× user average | `HIGH_AMOUNT_ANOMALY` | 75 |
| Multi-device login within 1 hour | `MULTI_DEVICE_1H` | 80 |
| Money mule chain (depth ≥ 2) | `MULE_CHAIN` | 90 |
| High-risk merchant + large amount | `HIGH_RISK_MERCHANT` | 65 |
| Shared device across users | `SHARED_DEVICE` | 60 |

---

## Quickstart

```bash
git clone https://github.com/ansh44233/FraudDetector
cd FraudDetector

# Docker (recommended)
docker compose up -d db api
docker compose run --rm seed

# open http://localhost:8000
```

### Manual setup

```bash
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

psql -U postgres -c "CREATE DATABASE frauddetector;"
psql -U postgres -d frauddetector -f db/schema.sql

copy .env.example .env   # add your password

python pipeline/seed.py
uvicorn api.main:app --reload
```

---

## API

```
POST /transactions                       submit a transaction (rules run async)

GET  /flags                              open fraud flags
GET  /flags?resolved=true               resolved flags
PATCH /flags/{id}                        resolve / unresolve a flag

GET  /analytics/velocity                 users with >5 txns in 10 min
GET  /analytics/merchant-fraud-rate      rolling 7-day rate per merchant
GET  /analytics/mule-chains              recursive CTE chain results
GET  /analytics/device-sharing           shared device detection
GET  /analytics/user-risk-ranking        PERCENT_RANK + NTILE ranking
GET  /analytics/summary                  dashboard KPIs

POST /engine/run                         manually trigger rules engine
GET  /users/risk-stats                   materialized view — user risk stats
```

---

## SQL Highlights

<details>
<summary><strong>Recursive CTE — money mule chain tracing</strong></summary>

```sql
WITH RECURSIVE chain AS (
    SELECT from_user_id, to_user_id, txn_id,
           ARRAY[from_user_id] AS visited, 1 AS depth
    FROM transaction_graph
    JOIN fraud_flags ff ON ff.txn_id = transaction_graph.txn_id
    WHERE ff.resolved = FALSE

    UNION ALL

    SELECT tg.from_user_id, tg.to_user_id, tg.txn_id,
           c.visited || tg.from_user_id, c.depth + 1
    FROM transaction_graph tg
    JOIN chain c ON tg.from_user_id = c.to_user_id
    WHERE NOT (tg.from_user_id = ANY(c.visited))  -- cycle guard
      AND c.depth < 6
)
SELECT * FROM chain ORDER BY depth DESC;
```
</details>

<details>
<summary><strong>LATERAL join — per-user velocity window</strong></summary>

```sql
SELECT u.id, u.name, recent.txn_count
FROM users u
JOIN LATERAL (
    SELECT COUNT(*) AS txn_count, SUM(amount) AS total_amount
    FROM transactions
    WHERE user_id = u.id
      AND created_at >= NOW() - INTERVAL '10 minutes'
) recent ON recent.txn_count > 5;
```
</details>

<details>
<summary><strong>RANGE BETWEEN — rolling 7-day merchant fraud rate</strong></summary>

```sql
SUM(COUNT(ff.id)) OVER (
    PARTITION BY m.id
    ORDER BY DATE(t.created_at)
    RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW
) AS rolling_7d_flags
```
</details>

<details>
<summary><strong>PL/pgSQL trigger — auto-flag on high-amount anomaly</strong></summary>

```sql
CREATE OR REPLACE FUNCTION auto_flag_high_amount()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE avg_amt NUMERIC;
BEGIN
    SELECT AVG(amount) INTO avg_amt
    FROM transactions WHERE user_id = NEW.user_id AND id <> NEW.id;

    IF avg_amt IS NOT NULL AND NEW.amount > (avg_amt * 5) THEN
        INSERT INTO fraud_flags (txn_id, rule_name, risk_score, details)
        VALUES (NEW.id, 'HIGH_AMOUNT_ANOMALY', 75.0,
            jsonb_build_object('amount', NEW.amount, 'ratio',
                               ROUND(NEW.amount / avg_amt, 2)));
    END IF;
    RETURN NEW;
END;
$$;
```
</details>

---

## Tests

```bash
# unit tests (no DB needed)
pytest tests/ -m "not integration" -v

# all tests (needs Postgres)
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/frauddetector_test \
pytest tests/ -v
```

| File | Tests | Type | Coverage |
|---|---|---|---|
| `test_rules.py` | 18 | unit | All 5 rules + `_flag` helper + `run_all_rules` |
| `test_api.py` | 20 | unit | Flags, transactions, analytics, engine endpoints |

Both test files mock the DB — no live Postgres needed for `pytest tests/ -m "not integration"`.

---

## Roadmap

- [x] Velocity burst detection (`VELOCITY_10M`)
- [x] Rapid-repeat same merchant (`RAPID_REPEAT`)
- [x] High-amount anomaly via PL/pgSQL trigger
- [x] Multi-device switch trigger (`MULTI_DEVICE_1H`)
- [x] Money mule chain tracing — recursive CTE, 6 hops
- [x] Shared device detection
- [x] Materialized view — per-user rolling risk stats
- [x] Docker + docker-compose
- [x] GitHub Actions CI (Python 3.11 + 3.12)
- [ ] WebSocket feed — push new flags to dashboard in real time
- [ ] ML layer — anomaly score using Isolation Forest on top of rule scores
- [ ] Graph visualisation — D3.js mule chain network diagram
- [ ] Auth — API key middleware, per-key rate limiting
- [ ] Scheduled materialized view refresh via pg_cron
- [ ] Slack / webhook alert on flag risk_score > 80

---

## Contributing

Fork the repo, make a branch, open a PR against `initial-release`.

```bash
git clone https://github.com/ansh44233/FraudDetector
cd FraudDetector
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
pytest tests/ -m "not integration"   # all green before you push
```

Good first issues:

- **Add `IP_REPUTATION` rule** — flag transactions from IPs that appear in >3 user accounts
- **Add `/flags/{id}` GET endpoint** — return a single flag with full transaction detail
- **Write integration tests** — `tests/test_integration_db.py` hitting a real Postgres test DB
- **Add `JSONB` index** — `CREATE INDEX ON fraud_flags USING GIN (details)` and benchmark

---

## Star History

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=ansh44233/FraudDetector&type=Date)](https://star-history.com/#ansh44233/FraudDetector&Date)

</div>

---

## License

MIT © [Ansh](https://github.com/ansh44233)
