"""
FraudDetector  |  FastAPI REST API
Run:  uvicorn api.main:app --reload
"""

import os
import sys
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

load_dotenv()
DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/frauddetector")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.rules import run_all_rules, run_rules_for_txn


# ── DB helpers ───────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(DSN)


def query(sql: str, params=None) -> list[dict]:
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params or ())
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def execute(sql: str, params=None):
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    cur.close(); conn.close()


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="FraudDetector API",
    description="Real-time fraud detection — advanced PostgreSQL + Python",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ── Pydantic models ──────────────────────────────────────────

class TransactionCreate(BaseModel):
    user_id:     int
    merchant_id: int
    amount:      float = Field(..., gt=0)
    currency:    str   = "INR"
    channel:     str   = "UPI"
    ip_address:  Optional[str] = None
    device_id:   Optional[str] = None


class ResolveFlag(BaseModel):
    resolved: bool = True


# ── TRANSACTIONS ─────────────────────────────────────────────

@app.post("/transactions", status_code=201, tags=["Transactions"])
def create_transaction(body: TransactionCreate, bg: BackgroundTasks):
    """
    Submit a transaction. Fraud rules run asynchronously in background.
    Returns txn_id + any flags already written by DB triggers.
    """
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """INSERT INTO transactions
           (user_id, merchant_id, amount, currency, channel, ip_address, device_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id, txn_ref""",
        (body.user_id, body.merchant_id, body.amount, body.currency,
         body.channel, body.ip_address, body.device_id)
    )
    txn = dict(cur.fetchone())
    conn.commit(); cur.close(); conn.close()

    # run full rules engine in background
    bg.add_task(run_rules_for_txn, txn["id"])

    return {"txn_id": txn["id"], "txn_ref": str(txn["txn_ref"]),
            "message": "Transaction submitted. Rules engine running."}


@app.get("/transactions", tags=["Transactions"])
def list_transactions(
    user_id:   Optional[int] = None,
    flagged:   bool = Query(False),
    limit:     int  = Query(50, le=200),
):
    sql = """
        SELECT t.id, t.txn_ref, u.name AS user_name, m.name AS merchant,
               t.amount, t.currency, t.channel, t.status,
               t.device_id, t.ip_address, t.created_at,
               COUNT(ff.id) AS flag_count
        FROM transactions t
        JOIN users     u ON u.id = t.user_id
        JOIN merchants m ON m.id = t.merchant_id
        LEFT JOIN fraud_flags ff ON ff.txn_id = t.id
        WHERE 1=1
    """
    params = []
    if user_id:
        sql += " AND t.user_id = %s"; params.append(user_id)
    if flagged:
        sql += " HAVING COUNT(ff.id) > 0"
        sql = sql.replace("WHERE 1=1", "WHERE 1=1 GROUP BY t.id,u.name,m.name")
    else:
        sql += " GROUP BY t.id,u.name,m.name"
    sql += " ORDER BY t.created_at DESC LIMIT %s"; params.append(limit)
    return query(sql, params)


# ── FRAUD FLAGS ───────────────────────────────────────────────

@app.get("/flags", tags=["Fraud Flags"])
def list_flags(resolved: Optional[bool] = False, limit: int = Query(100, le=500)):
    sql = """
        SELECT ff.id, ff.rule_name, ff.risk_score, ff.details, ff.resolved,
               ff.created_at, t.txn_ref, t.amount, u.name AS user_name,
               m.name AS merchant
        FROM fraud_flags ff
        JOIN transactions t ON t.id = ff.txn_id
        JOIN users        u ON u.id = t.user_id
        JOIN merchants    m ON m.id = t.merchant_id
        WHERE 1=1
    """
    params = []
    if resolved is not None:
        sql += " AND ff.resolved = %s"; params.append(resolved)
    sql += " ORDER BY ff.created_at DESC LIMIT %s"; params.append(limit)
    return query(sql, params)


@app.patch("/flags/{flag_id}", tags=["Fraud Flags"])
def resolve_flag(flag_id: int, body: ResolveFlag):
    rows = query("SELECT id FROM fraud_flags WHERE id=%s", (flag_id,))
    if not rows:
        raise HTTPException(404, "Flag not found")
    execute("UPDATE fraud_flags SET resolved=%s WHERE id=%s", (body.resolved, flag_id))
    return {"flag_id": flag_id, "resolved": body.resolved}


# ── ANALYTICS ────────────────────────────────────────────────

@app.get("/analytics/velocity", tags=["Analytics"])
def velocity_check():
    """Users with >5 transactions in last 10 minutes — LATERAL + window function."""
    return query("""
        SELECT u.id, u.name, recent.txn_count, recent.total_amount,
               recent.first_txn, recent.last_txn
        FROM users u
        JOIN LATERAL (
            SELECT COUNT(*) AS txn_count, SUM(amount) AS total_amount,
                   MIN(created_at) AS first_txn, MAX(created_at) AS last_txn
            FROM transactions
            WHERE user_id = u.id AND created_at >= NOW() - INTERVAL '10 minutes'
        ) recent ON recent.txn_count > 5
        ORDER BY recent.txn_count DESC
    """)


@app.get("/analytics/merchant-fraud-rate", tags=["Analytics"])
def merchant_fraud_rate():
    """Rolling 7-day fraud rate per merchant — RANGE BETWEEN window."""
    return query("""
        SELECT m.name AS merchant, m.category,
               DATE(t.created_at) AS day,
               COUNT(t.id) AS txns,
               COUNT(ff.id) AS flags,
               ROUND(100.0 * COUNT(ff.id) / NULLIF(COUNT(t.id),0), 2) AS flag_rate_pct,
               ROUND(100.0 *
                   SUM(COUNT(ff.id)) OVER (
                       PARTITION BY m.id
                       ORDER BY DATE(t.created_at)
                       RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW
                   ) / NULLIF(
                       SUM(COUNT(t.id)) OVER (
                           PARTITION BY m.id
                           ORDER BY DATE(t.created_at)
                           RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW
                       ), 0
                   ), 2) AS rolling_7d_rate
        FROM merchants m
        JOIN transactions t ON t.merchant_id = m.id
        LEFT JOIN fraud_flags ff ON ff.txn_id = t.id
        GROUP BY m.id, m.name, m.category, DATE(t.created_at)
        ORDER BY m.name, day
    """)


@app.get("/analytics/mule-chains", tags=["Analytics"])
def mule_chains():
    """Money mule chains via recursive CTE — up to 6 hops."""
    return query("""
        WITH RECURSIVE chain AS (
            SELECT tg.from_user_id, tg.to_user_id, tg.amount, tg.txn_id,
                   ARRAY[tg.from_user_id] AS visited, 1 AS depth
            FROM transaction_graph tg
            JOIN fraud_flags ff ON ff.txn_id = tg.txn_id WHERE ff.resolved=FALSE
            UNION ALL
            SELECT tg.from_user_id, tg.to_user_id, tg.amount, tg.txn_id,
                   c.visited || tg.from_user_id, c.depth + 1
            FROM transaction_graph tg
            JOIN chain c ON tg.from_user_id = c.to_user_id
            WHERE NOT (tg.from_user_id = ANY(c.visited)) AND c.depth < 6
        )
        SELECT from_user_id, to_user_id, amount, depth, visited AS chain
        FROM chain ORDER BY depth DESC, amount DESC LIMIT 50
    """)


@app.get("/analytics/device-sharing", tags=["Analytics"])
def device_sharing():
    """Devices used by multiple users — potential mule network."""
    return query("""
        SELECT t.device_id,
               COUNT(DISTINCT t.user_id) AS user_count,
               ARRAY_AGG(DISTINCT u.name) AS users,
               SUM(t.amount) AS total_amount
        FROM transactions t JOIN users u ON u.id=t.user_id
        WHERE t.device_id IS NOT NULL
        GROUP BY t.device_id
        HAVING COUNT(DISTINCT t.user_id) > 1
        ORDER BY user_count DESC
    """)


@app.get("/analytics/user-risk-ranking", tags=["Analytics"])
def user_risk_ranking():
    """PERCENT_RANK + NTILE + DENSE_RANK on user flag counts."""
    return query("""
        SELECT u.id, u.name,
               COUNT(ff.id) AS flag_count,
               ROUND(PERCENT_RANK() OVER (ORDER BY COUNT(ff.id) DESC)*100,1) AS risk_percentile,
               NTILE(10) OVER (ORDER BY COUNT(ff.id) DESC) AS risk_decile,
               DENSE_RANK() OVER (ORDER BY COUNT(ff.id) DESC) AS rank
        FROM users u
        LEFT JOIN transactions t ON t.user_id = u.id
        LEFT JOIN fraud_flags ff ON ff.txn_id = t.id
        GROUP BY u.id, u.name
        ORDER BY flag_count DESC
    """)


@app.get("/analytics/summary", tags=["Analytics"])
def summary():
    """Dashboard KPIs."""
    return query("""
        SELECT
            (SELECT COUNT(*) FROM transactions) AS total_txns,
            (SELECT COUNT(*) FROM fraud_flags WHERE resolved=FALSE) AS open_flags,
            (SELECT COUNT(DISTINCT user_id) FROM transactions
             WHERE created_at >= NOW() - INTERVAL '24 hours') AS active_users_24h,
            (SELECT ROUND(AVG(risk_score),1) FROM fraud_flags WHERE resolved=FALSE) AS avg_risk_score,
            (SELECT COUNT(*) FROM transactions
             WHERE created_at >= NOW() - INTERVAL '1 hour') AS txns_last_hour,
            (SELECT SUM(amount) FROM transactions
             WHERE created_at >= NOW() - INTERVAL '24 hours') AS volume_24h
    """)


@app.post("/engine/run", tags=["Engine"])
def run_engine():
    """Manually trigger the fraud rules engine."""
    n = run_all_rules()
    execute("REFRESH MATERIALIZED VIEW CONCURRENTLY user_risk_stats")
    return {"new_flags": n, "message": f"Rules engine ran. {n} new flags."}


@app.get("/users/risk-stats", tags=["Users"])
def user_risk_stats():
    """From materialized view — pre-computed risk stats per user."""
    return query("SELECT * FROM user_risk_stats ORDER BY total_flags DESC, risk_score DESC")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    p = os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")
    with open(p, encoding="utf-8") as f:
        return f.read()
