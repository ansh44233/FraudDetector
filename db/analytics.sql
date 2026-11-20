-- ============================================================
-- FraudDetector  |  Advanced Analytics Queries
-- Every query here uses at least one advanced SQL feature
-- ============================================================


-- 1. VELOCITY CHECK — users with >5 transactions in last 10 minutes
--    Uses: window function COUNT OVER, LATERAL, timestamp arithmetic
SELECT
    u.id,
    u.name,
    u.email,
    recent.txn_count,
    recent.total_amount,
    recent.first_txn,
    recent.last_txn
FROM users u
JOIN LATERAL (
    SELECT
        COUNT(*)                AS txn_count,
        SUM(amount)             AS total_amount,
        MIN(created_at)         AS first_txn,
        MAX(created_at)         AS last_txn
    FROM transactions
    WHERE user_id  = u.id
      AND created_at >= NOW() - INTERVAL '10 minutes'
) recent ON recent.txn_count > 5
ORDER BY recent.txn_count DESC;


-- 2. RAPID REPEAT — same user, same merchant, back-to-back within 60s
--    Uses: LAG window function, timestamp diff
SELECT
    t.id            AS txn_id,
    t.txn_ref,
    u.name          AS user_name,
    m.name          AS merchant_name,
    t.amount,
    t.created_at,
    prev_txn.created_at                             AS prev_txn_at,
    EXTRACT(EPOCH FROM (t.created_at - prev_txn.created_at))
                                                    AS seconds_since_last
FROM transactions t
JOIN users     u ON u.id = t.user_id
JOIN merchants m ON m.id = t.merchant_id
JOIN LATERAL (
    SELECT created_at
    FROM transactions t2
    WHERE t2.user_id     = t.user_id
      AND t2.merchant_id = t.merchant_id
      AND t2.id         <> t.id
      AND t2.created_at  < t.created_at
    ORDER BY t2.created_at DESC
    LIMIT 1
) prev_txn ON EXTRACT(EPOCH FROM (t.created_at - prev_txn.created_at)) < 60
ORDER BY seconds_since_last;


-- 3. MONEY MULE CHAIN — recursive CTE to trace multi-hop money flow
--    Uses: recursive CTE, depth tracking, cycle prevention
WITH RECURSIVE money_chain AS (
    -- base: start from flagged transactions
    SELECT
        tg.from_user_id,
        tg.to_user_id,
        tg.amount,
        tg.txn_id,
        ARRAY[tg.from_user_id]  AS visited,
        1                       AS depth
    FROM transaction_graph tg
    JOIN fraud_flags ff ON ff.txn_id = tg.txn_id
    WHERE ff.resolved = FALSE

    UNION ALL

    SELECT
        tg.from_user_id,
        tg.to_user_id,
        tg.amount,
        tg.txn_id,
        mc.visited || tg.from_user_id,
        mc.depth + 1
    FROM transaction_graph tg
    JOIN money_chain mc ON tg.from_user_id = mc.to_user_id
    WHERE NOT (tg.from_user_id = ANY(mc.visited))   -- cycle guard
      AND mc.depth < 6                               -- max 6 hops
)
SELECT
    from_user_id,
    to_user_id,
    amount,
    depth,
    visited AS chain
FROM money_chain
ORDER BY depth DESC, amount DESC;


-- 4. MERCHANT FRAUD RATE — rolling 7-day fraud rate per merchant
--    Uses: window SUM with RANGE BETWEEN, ratio calculation
SELECT
    m.name                              AS merchant,
    m.category,
    DATE(t.created_at)                  AS day,
    COUNT(t.id)                         AS daily_txns,
    COUNT(ff.id)                        AS daily_flags,
    ROUND(
        100.0 * COUNT(ff.id) / NULLIF(COUNT(t.id), 0),
    2)                                  AS flag_rate_pct,
    ROUND(
        100.0 *
        SUM(COUNT(ff.id)) OVER (
            PARTITION BY m.id
            ORDER BY DATE(t.created_at)
            RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW
        ) /
        NULLIF(
            SUM(COUNT(t.id)) OVER (
                PARTITION BY m.id
                ORDER BY DATE(t.created_at)
                RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW
            ), 0
        ),
    2)                                  AS rolling_7d_flag_rate_pct
FROM merchants m
JOIN transactions  t  ON t.merchant_id = m.id
LEFT JOIN fraud_flags ff ON ff.txn_id  = t.id
GROUP BY m.id, m.name, m.category, DATE(t.created_at)
ORDER BY m.name, day;


-- 5. DEVICE SHARING — devices used by multiple users (mule network signal)
--    Uses: HAVING, COUNT DISTINCT, aggregation
SELECT
    t.device_id,
    COUNT(DISTINCT t.user_id)           AS user_count,
    ARRAY_AGG(DISTINCT u.name)          AS users,
    SUM(t.amount)                       AS total_amount,
    MIN(t.created_at)                   AS first_seen,
    MAX(t.created_at)                   AS last_seen
FROM transactions t
JOIN users u ON u.id = t.user_id
WHERE t.device_id IS NOT NULL
GROUP BY t.device_id
HAVING COUNT(DISTINCT t.user_id) > 1
ORDER BY user_count DESC, total_amount DESC;


-- 6. USER RISK RANKING — percentile rank by flag count
--    Uses: PERCENT_RANK, NTILE, dense_rank
SELECT
    u.id,
    u.name,
    COUNT(ff.id)                        AS flag_count,
    SUM(t.amount)                       AS total_spent,
    ROUND(PERCENT_RANK() OVER (
        ORDER BY COUNT(ff.id) DESC
    ) * 100, 1)                         AS risk_percentile,
    NTILE(10) OVER (
        ORDER BY COUNT(ff.id) DESC
    )                                   AS risk_decile,
    DENSE_RANK() OVER (
        ORDER BY COUNT(ff.id) DESC
    )                                   AS rank
FROM users u
LEFT JOIN transactions t  ON t.user_id = u.id
LEFT JOIN fraud_flags  ff ON ff.txn_id = t.id
GROUP BY u.id, u.name
ORDER BY flag_count DESC;


-- 7. COHORT RETENTION — weekly user activity cohorts
--    Uses: DATE_TRUNC, cohort join, retention matrix
WITH cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC('week', MIN(created_at)) AS cohort_week
    FROM transactions
    GROUP BY user_id
),
activity AS (
    SELECT
        t.user_id,
        c.cohort_week,
        DATE_TRUNC('week', t.created_at) AS activity_week,
        EXTRACT(EPOCH FROM
            DATE_TRUNC('week', t.created_at) - c.cohort_week
        ) / 604800                       AS week_number
    FROM transactions t
    JOIN cohorts c ON c.user_id = t.user_id
)
SELECT
    cohort_week,
    week_number::INT                    AS weeks_since_first,
    COUNT(DISTINCT user_id)             AS active_users
FROM activity
GROUP BY cohort_week, week_number
ORDER BY cohort_week, week_number;
