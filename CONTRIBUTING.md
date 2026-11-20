# Contributing to FraudDetector

Thanks for your interest. Here's how to get started.

## Setup

```bash
git clone https://github.com/ansh44233/FraudDetector
cd FraudDetector
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Run the tests

```bash
pytest tests/ -m "not integration" -v    # unit tests — no DB needed
```

All tests must pass before you open a PR.

## Branch naming

```
feat/your-feature-name
fix/what-youre-fixing
docs/what-youre-documenting
```

## Pull Request checklist

- [ ] Tests pass (`pytest tests/ -m "not integration"`)
- [ ] New rules have a corresponding test in `tests/test_rules.py`
- [ ] New endpoints have a corresponding test in `tests/test_api.py`
- [ ] Raw SQL only — no ORM queries in new code
- [ ] PR description explains the SQL technique used (if applicable)

## Good first issues

| Issue | File | What to do |
|---|---|---|
| `IP_REPUTATION` rule | `engine/rules.py` | Flag IPs appearing across >3 user accounts |
| `GET /flags/{id}` endpoint | `api/main.py` | Single flag with full transaction detail |
| Integration test suite | `tests/test_integration_db.py` | Hit a real Postgres test DB |
| GIN index on `details` | `db/schema.sql` | `CREATE INDEX ON fraud_flags USING GIN (details)` and benchmark |

## SQL conventions

- Window functions go in `db/analytics.sql` with a comment explaining the frame
- Rules go in `engine/rules.py` — one function per rule, SQL constant at top
- No f-string SQL — always use parameterized queries (`%s`)

## Questions

Open an issue or ping [@ansh44233](https://github.com/ansh44233).
