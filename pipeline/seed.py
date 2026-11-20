"""
FraudDetector — Seed Pipeline
Generates realistic transaction data including embedded fraud patterns.
Run: python pipeline/seed.py
"""

import os
import random
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/frauddetector")

USERS = [
    ("Rahul Sharma",   "rahul@example.com",   "IN"),
    ("Priya Patel",    "priya@example.com",    "IN"),
    ("Arjun Nair",     "arjun@example.com",    "IN"),
    ("Sneha Reddy",    "sneha@example.com",    "IN"),
    ("Vikram Singh",   "vikram@example.com",   "IN"),
    ("Anjali Mehta",   "anjali@example.com",   "IN"),
    ("Rohan Gupta",    "rohan@example.com",    "IN"),
    ("Kavya Iyer",     "kavya@example.com",    "IN"),
    ("Amit Joshi",     "amit@example.com",     "IN"),
    ("Deepa Pillai",   "deepa@example.com",    "IN"),
    # mule accounts
    ("Mule Account A", "mulea@burner.com",     "IN"),
    ("Mule Account B", "muleb@burner.com",     "IN"),
    ("Mule Account C", "mulec@burner.com",     "IN"),
]

MERCHANTS = [
    ("Swiggy",         "FOOD",    "IN", 1),
    ("Zomato",         "FOOD",    "IN", 1),
    ("Amazon IN",      "ECOMM",   "IN", 1),
    ("Flipkart",       "ECOMM",   "IN", 1),
    ("BookMyShow",     "ENTMT",   "IN", 1),
    ("Dream11",        "GAMING",  "IN", 2),
    ("MPL Games",      "GAMING",  "IN", 2),
    ("CoinDCX",        "CRYPTO",  "IN", 3),
    ("WazirX",         "CRYPTO",  "IN", 3),
    ("UnknownShop",    "MISC",    "SG", 3),
]

CHANNELS  = ["UPI", "CARD", "NETBANKING", "WALLET"]
DEVICES   = [f"device_{i}" for i in range(1, 15)]
IPS       = [f"192.168.1.{i}" for i in range(1, 20)] + \
            [f"103.21.{i}.{j}" for i in range(1,5) for j in range(1,5)]


def connect():
    return psycopg2.connect(DSN)


def seed():
    conn = connect()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # users
    user_ids = []
    for name, email, country in USERS:
        cur.execute(
            """INSERT INTO users (name, email, country)
               VALUES (%s, %s, %s)
               ON CONFLICT (email) DO UPDATE SET name=EXCLUDED.name
               RETURNING id""",
            (name, email, country)
        )
        user_ids.append(cur.fetchone()["id"])

    # merchants
    merch_ids = []
    for name, cat, country, tier in MERCHANTS:
        cur.execute(
            """INSERT INTO merchants (name, category, country, risk_tier)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT DO NOTHING
               RETURNING id""",
            (name, cat, country, tier)
        )
        row = cur.fetchone()
        if row:
            merch_ids.append(row["id"])

    conn.commit()

    # re-fetch ids if conflict
    cur.execute("SELECT id FROM merchants ORDER BY id")
    merch_ids = [r["id"] for r in cur.fetchall()]
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r["id"] for r in cur.fetchall()]
    normal_users = user_ids[:10]
    mule_users   = user_ids[10:]

    # ── Normal transactions (last 90 days) ───────────────────
    for _ in range(300):
        uid   = random.choice(normal_users)
        mid   = random.choice(merch_ids)
        amt   = round(random.uniform(50, 2000), 2)
        days  = random.randint(0, 90)
        ts    = datetime.now() - timedelta(days=days, minutes=random.randint(0, 1440))
        chan  = random.choice(CHANNELS)
        dev   = random.choice(DEVICES[:8])   # normal users share fewer devices
        ip    = random.choice(IPS[:10])

        cur.execute(
            """INSERT INTO transactions
               (user_id, merchant_id, amount, channel, device_id, ip_address, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               RETURNING id""",
            (uid, mid, amt, chan, dev, ip, ts)
        )
        txn_id = cur.fetchone()["id"]

        # graph edge (10% of txns are p2p transfers)
        if random.random() < 0.1:
            to_uid = random.choice([u for u in normal_users if u != uid])
            cur.execute(
                """INSERT INTO transaction_graph
                   (from_user_id, to_user_id, txn_id, amount, created_at)
                   VALUES (%s,%s,%s,%s,%s)""",
                (uid, to_uid, txn_id, amt, ts)
            )

    conn.commit()

    # ── Fraud pattern 1: velocity burst (5 txns in 2 min) ────
    fraud_user = normal_users[0]
    base_ts    = datetime.now() - timedelta(hours=2)
    for i in range(7):
        ts = base_ts + timedelta(seconds=i * 20)
        cur.execute(
            """INSERT INTO transactions
               (user_id, merchant_id, amount, channel, device_id, ip_address, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (fraud_user, merch_ids[-1], round(random.uniform(900, 1200), 2),
             "UPI", "device_suspect_1", "103.21.1.1", ts)
        )

    # ── Fraud pattern 2: high amount anomaly ─────────────────
    # user normally spends ~200, then suddenly 25000
    normal_user2 = normal_users[2]
    for _ in range(5):
        ts = datetime.now() - timedelta(days=random.randint(5, 30))
        cur.execute(
            """INSERT INTO transactions
               (user_id, merchant_id, amount, channel, device_id, ip_address, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (normal_user2, merch_ids[0], 200.0, "UPI", "device_3", "192.168.1.3", ts)
        )
    # the anomaly
    cur.execute(
        """INSERT INTO transactions
           (user_id, merchant_id, amount, channel, device_id, ip_address, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (normal_user2, merch_ids[7], 95000.0, "CARD", "device_3", "103.21.3.3",
         datetime.now() - timedelta(hours=1))
    )

    # ── Fraud pattern 3: money mule chain ────────────────────
    # normal_user → mule_a → mule_b → mule_c
    chain_ts = datetime.now() - timedelta(hours=3)
    prev_uid = normal_users[4]
    for muid in mule_users:
        cur.execute(
            """INSERT INTO transactions
               (user_id, merchant_id, amount, channel, device_id, ip_address, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               RETURNING id""",
            (prev_uid, merch_ids[-1], 15000.0, "NETBANKING",
             f"device_mule_{muid}", "103.21.4.4", chain_ts)
        )
        txn_id = cur.fetchone()["id"]
        cur.execute(
            """INSERT INTO transaction_graph
               (from_user_id, to_user_id, txn_id, amount, created_at)
               VALUES (%s,%s,%s,%s,%s)""",
            (prev_uid, muid, txn_id, 15000.0, chain_ts)
        )
        prev_uid  = muid
        chain_ts += timedelta(minutes=15)

    # ── Fraud pattern 4: multi-device ────────────────────────
    fraud_user2 = normal_users[6]
    for i, dev in enumerate(DEVICES[8:12]):
        ts = datetime.now() - timedelta(minutes=20 + i * 5)
        cur.execute(
            """INSERT INTO transactions
               (user_id, merchant_id, amount, channel, device_id, ip_address, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (fraud_user2, random.choice(merch_ids), round(random.uniform(500,3000),2),
             "UPI", dev, f"103.21.2.{i+1}", ts)
        )

    conn.commit()

    # refresh materialized view
    cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY user_risk_stats")
    conn.commit()
    cur.close()
    conn.close()

    print("✅  Seeded: 13 users, 10 merchants, ~320 transactions")
    print("     Patterns: velocity burst, high-amount anomaly, money mule chain, multi-device")


if __name__ == "__main__":
    seed()
