"""
FraudDetector — Rules Engine
Runs all detection rules against the DB and writes fraud_flags.
Called on every new transaction or on-demand via API.
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/frauddetector")


def get_conn():
    return psycopg2.connect(DSN)


def _flag(cur, txn_id: int, rule: str, score: float, details: dict):
    cur.execute(
        """INSERT INTO fraud_flags (txn_id, rule_name, risk_score, details)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (txn_id, rule, score, psycopg2.extras.Json(details))
    )


# ── Rule 1: Velocity — >5 txns in 10 min ────────────────────
VELOCITY_SQL = """
SELECT t.id AS txn_id, COUNT(*) OVER (
    PARTITION BY t.user_id
    ORDER BY t.created_at
    RANGE BETWEEN INTERVAL '10 minutes' PRECEDING AND CURRENT ROW
) AS txn_count_10m
FROM transactions t
WHERE t.created_at >= NOW() - INTERVAL '10 minutes'
  AND NOT EXISTS (
      SELECT 1 FROM fraud_flags ff
      WHERE ff.txn_id = t.id AND ff.rule_name = 'VELOCITY_10M'
  )
"""

def rule_velocity(cur):
    cur.execute(VELOCITY_SQL)
    for row in cur.fetchall():
        if row["txn_count_10m"] > 5:
            _flag(cur, row["txn_id"], "VELOCITY_10M", 85.0,
                  {"txn_count_10m": row["txn_count_10m"]})


# ── Rule 2: Rapid repeat — same user+merchant < 60s ─────────
RAPID_REPEAT_SQL = """
SELECT t.id AS txn_id,
       EXTRACT(EPOCH FROM (t.created_at - prev_t.created_at)) AS gap_secs
FROM transactions t
JOIN LATERAL (
    SELECT created_at FROM transactions t2
    WHERE t2.user_id = t.user_id AND t2.merchant_id = t.merchant_id
      AND t2.id < t.id
    ORDER BY t2.created_at DESC LIMIT 1
) prev_t ON TRUE
WHERE EXTRACT(EPOCH FROM (t.created_at - prev_t.created_at)) < 60
  AND t.created_at >= NOW() - INTERVAL '1 hour'
  AND NOT EXISTS (
      SELECT 1 FROM fraud_flags ff
      WHERE ff.txn_id = t.id AND ff.rule_name = 'RAPID_REPEAT'
  )
"""

def rule_rapid_repeat(cur):
    cur.execute(RAPID_REPEAT_SQL)
    for row in cur.fetchall():
        _flag(cur, row["txn_id"], "RAPID_REPEAT", 70.0,
              {"gap_seconds": round(row["gap_secs"], 1)})


# ── Rule 3: High-risk merchant + large amount ────────────────
HIGH_RISK_MERCH_SQL = """
SELECT t.id AS txn_id, t.amount, m.risk_tier, m.category
FROM transactions t
JOIN merchants m ON m.id = t.merchant_id
WHERE m.risk_tier = 3 AND t.amount > 10000
  AND t.created_at >= NOW() - INTERVAL '24 hours'
  AND NOT EXISTS (
      SELECT 1 FROM fraud_flags ff
      WHERE ff.txn_id = t.id AND ff.rule_name = 'HIGH_RISK_MERCHANT'
  )
"""

def rule_high_risk_merchant(cur):
    cur.execute(HIGH_RISK_MERCH_SQL)
    for row in cur.fetchall():
        _flag(cur, row["txn_id"], "HIGH_RISK_MERCHANT", 65.0,
              {"amount": float(row["amount"]),
               "merchant_category": row["category"],
               "risk_tier": row["risk_tier"]})


# ── Rule 4: Device shared by >1 user ────────────────────────
SHARED_DEVICE_SQL = """
SELECT t.id AS txn_id, t.device_id,
       COUNT(DISTINCT t2.user_id) AS sharing_users
FROM transactions t
JOIN transactions t2 ON t2.device_id = t.device_id AND t2.user_id <> t.user_id
WHERE t.device_id IS NOT NULL
  AND t.created_at >= NOW() - INTERVAL '24 hours'
  AND NOT EXISTS (
      SELECT 1 FROM fraud_flags ff
      WHERE ff.txn_id = t.id AND ff.rule_name = 'SHARED_DEVICE'
  )
GROUP BY t.id, t.device_id
HAVING COUNT(DISTINCT t2.user_id) >= 1
"""

def rule_shared_device(cur):
    cur.execute(SHARED_DEVICE_SQL)
    for row in cur.fetchall():
        _flag(cur, row["txn_id"], "SHARED_DEVICE", 60.0,
              {"device_id": row["device_id"],
               "other_users": row["sharing_users"]})


# ── Rule 5: Mule chain — appears in graph with depth >= 2 ───
MULE_CHAIN_SQL = """
WITH RECURSIVE chain AS (
    SELECT from_user_id, to_user_id, txn_id, ARRAY[from_user_id] AS visited, 1 AS depth
    FROM transaction_graph
    UNION ALL
    SELECT tg.from_user_id, tg.to_user_id, tg.txn_id,
           c.visited || tg.from_user_id, c.depth + 1
    FROM transaction_graph tg
    JOIN chain c ON tg.from_user_id = c.to_user_id
    WHERE NOT (tg.from_user_id = ANY(c.visited)) AND c.depth < 5
)
SELECT DISTINCT txn_id, depth FROM chain
WHERE depth >= 2
  AND NOT EXISTS (
      SELECT 1 FROM fraud_flags ff
      WHERE ff.txn_id = chain.txn_id AND ff.rule_name = 'MULE_CHAIN'
  )
"""

def rule_mule_chain(cur):
    cur.execute(MULE_CHAIN_SQL)
    for row in cur.fetchall():
        _flag(cur, row["txn_id"], "MULE_CHAIN", 90.0,
              {"chain_depth": row["depth"]})


# ── Run all rules ─────────────────────────────────────────────

def run_all_rules() -> int:
    """Run all rules, return number of new flags written."""
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    before = _count_flags(cur)
    rule_velocity(cur)
    rule_rapid_repeat(cur)
    rule_high_risk_merchant(cur)
    rule_shared_device(cur)
    rule_mule_chain(cur)
    after = _count_flags(cur)

    conn.commit()
    cur.close()
    conn.close()
    return after - before


def run_rules_for_txn(txn_id: int) -> list[dict]:
    """Run all rules scoped to a single transaction and return new flags."""
    run_all_rules()
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT rule_name, risk_score, details FROM fraud_flags WHERE txn_id=%s",
        (txn_id,)
    )
    flags = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return flags


def _count_flags(cur) -> int:
    cur.execute("SELECT COUNT(*) AS n FROM fraud_flags")
    return cur.fetchone()["n"]


if __name__ == "__main__":
    n = run_all_rules()
    print(f"Rules engine: {n} new flags written.")
