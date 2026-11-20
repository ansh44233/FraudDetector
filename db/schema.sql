-- ============================================================
-- FraudDetector  |  Schema
-- PostgreSQL 15+  |  Raw SQL  |  No ORM
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- for fast text search on merchant names

-- ── TABLES ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    external_id     UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    email           VARCHAR(200) UNIQUE NOT NULL,
    country         VARCHAR(80)  NOT NULL DEFAULT 'IN',
    risk_score      NUMERIC(5,2) NOT NULL DEFAULT 0.0 CHECK (risk_score BETWEEN 0 AND 100),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS merchants (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(80)  NOT NULL,  -- e.g. GAMING, CRYPTO, ECOMM
    country         VARCHAR(80)  NOT NULL DEFAULT 'IN',
    risk_tier       SMALLINT     NOT NULL DEFAULT 1 CHECK (risk_tier BETWEEN 1 AND 3),
    -- 1=low risk, 2=medium, 3=high (crypto, gambling)
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    txn_ref         UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    user_id         INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    merchant_id     INT  NOT NULL REFERENCES merchants(id),
    amount          NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    currency        CHAR(3)  NOT NULL DEFAULT 'INR',
    channel         VARCHAR(30) NOT NULL DEFAULT 'UPI',
    -- UPI, CARD, NETBANKING, WALLET
    status          VARCHAR(20) NOT NULL DEFAULT 'completed'
                        CHECK (status IN ('completed','failed','reversed','flagged')),
    ip_address      INET,
    device_id       VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_flags (
    id              SERIAL PRIMARY KEY,
    txn_id          INT  NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    rule_name       VARCHAR(100) NOT NULL,
    risk_score      NUMERIC(5,2) NOT NULL,
    details         JSONB,
    resolved        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transaction_graph (
    -- adjacency table: user A sent money → user B
    id              SERIAL PRIMARY KEY,
    from_user_id    INT NOT NULL REFERENCES users(id),
    to_user_id      INT NOT NULL REFERENCES users(id),
    txn_id          INT NOT NULL REFERENCES transactions(id),
    amount          NUMERIC(14,2) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (from_user_id <> to_user_id)
);

-- ── INDEXES ───────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_txn_user        ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_txn_merchant    ON transactions(merchant_id);
CREATE INDEX IF NOT EXISTS idx_txn_created     ON transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_txn_device      ON transactions(device_id);
CREATE INDEX IF NOT EXISTS idx_txn_ip          ON transactions(ip_address);
CREATE INDEX IF NOT EXISTS idx_flags_txn       ON fraud_flags(txn_id);
CREATE INDEX IF NOT EXISTS idx_flags_resolved  ON fraud_flags(resolved) WHERE resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_graph_from      ON transaction_graph(from_user_id);
CREATE INDEX IF NOT EXISTS idx_graph_to        ON transaction_graph(to_user_id);

-- ── MATERIALIZED VIEW: per-user rolling risk stats ────────────
-- Refreshed by the API on demand / scheduled job
CREATE MATERIALIZED VIEW IF NOT EXISTS user_risk_stats AS
SELECT
    u.id                                            AS user_id,
    u.name,
    u.email,
    COUNT(t.id)                                     AS total_txns,
    SUM(t.amount)                                   AS total_amount,
    AVG(t.amount)                                   AS avg_amount,
    MAX(t.amount)                                   AS max_single_txn,
    COUNT(DISTINCT t.merchant_id)                   AS distinct_merchants,
    COUNT(DISTINCT t.device_id)                     AS distinct_devices,
    COUNT(DISTINCT t.ip_address)                    AS distinct_ips,
    COUNT(ff.id)                                    AS total_flags,
    MAX(t.created_at)                               AS last_txn_at,
    u.risk_score
FROM users u
LEFT JOIN transactions t  ON t.user_id = u.id
LEFT JOIN fraud_flags  ff ON ff.txn_id = t.id
GROUP BY u.id, u.name, u.email, u.risk_score;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_user_risk ON user_risk_stats(user_id);

-- ── TRIGGER: auto-flag high-amount transactions ───────────────
CREATE OR REPLACE FUNCTION auto_flag_high_amount()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    avg_amt NUMERIC;
BEGIN
    -- get this user's average transaction amount
    SELECT AVG(amount) INTO avg_amt
    FROM transactions
    WHERE user_id = NEW.user_id
      AND id <> NEW.id;

    -- flag if amount > 5x the user's average OR > 50000
    IF avg_amt IS NOT NULL AND NEW.amount > (avg_amt * 5) THEN
        INSERT INTO fraud_flags (txn_id, rule_name, risk_score, details)
        VALUES (
            NEW.id,
            'HIGH_AMOUNT_ANOMALY',
            75.0,
            jsonb_build_object(
                'amount', NEW.amount,
                'user_avg', ROUND(avg_amt, 2),
                'ratio', ROUND(NEW.amount / avg_amt, 2)
            )
        );
    ELSIF NEW.amount > 50000 THEN
        INSERT INTO fraud_flags (txn_id, rule_name, risk_score, details)
        VALUES (
            NEW.id,
            'LARGE_TRANSACTION',
            50.0,
            jsonb_build_object('amount', NEW.amount)
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_auto_flag ON transactions;
CREATE TRIGGER trg_auto_flag
    AFTER INSERT ON transactions
    FOR EACH ROW EXECUTE FUNCTION auto_flag_high_amount();

-- ── TRIGGER: flag multiple devices in short window ────────────
CREATE OR REPLACE FUNCTION auto_flag_device_switch()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    device_count INT;
BEGIN
    SELECT COUNT(DISTINCT device_id) INTO device_count
    FROM transactions
    WHERE user_id = NEW.user_id
      AND created_at >= NOW() - INTERVAL '1 hour'
      AND device_id IS NOT NULL;

    IF device_count >= 3 THEN
        INSERT INTO fraud_flags (txn_id, rule_name, risk_score, details)
        VALUES (
            NEW.id,
            'MULTI_DEVICE_1H',
            80.0,
            jsonb_build_object('distinct_devices_1h', device_count)
        )
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_device_switch ON transactions;
CREATE TRIGGER trg_device_switch
    AFTER INSERT ON transactions
    FOR EACH ROW EXECUTE FUNCTION auto_flag_device_switch();
