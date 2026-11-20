# Changelog

All notable changes to FraudDetector are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.1.0] — 2026-11-20

### Added
- Dashboard v4 — Zinc/Indigo design system, restrained palette, proper header + footer
- Hero banner with fraud illustration and live stats
- Risk activity heatmap (7 days × 24 hours)
- Live detection feed sidebar
- Chain path node visualization in mule chains table

### Changed
- Dashboard now uses Inter font and SVG icons — no emojis
- KPI cards have single-color accent bars instead of rainbow glows

---

## [1.0.1] — 2026-11-20

### Added
- Vercel deployment — dashboard live at [frauddetector-dashboard.vercel.app](https://frauddetector-dashboard.vercel.app)
- `CONTRIBUTING.md`, `LICENSE`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- GitHub topics for discoverability

### Fixed
- Dashboard preview PNG updated to match current design

---

## [1.0.0] — 2026-11-19

### Added
- PostgreSQL schema — 5 tables, 2 PL/pgSQL triggers, materialized view
- 7 detection rules — `VELOCITY_10M`, `RAPID_REPEAT`, `HIGH_AMOUNT_ANOMALY`, `MULTI_DEVICE_1H`, `MULE_CHAIN`, `HIGH_RISK_MERCHANT`, `SHARED_DEVICE`
- FastAPI REST API with 10 endpoints
- Advanced SQL — recursive CTEs, LATERAL joins, `RANGE BETWEEN`, `PERCENT_RANK`, `NTILE`, `DENSE_RANK`
- Python seed pipeline — 20 users, 10 merchants, 60+ transactions
- 38 pytest unit tests (zero DB dependency)
- Docker + docker-compose — `db`, `api`, `seed` services
- GitHub Actions CI — Python 3.11 + 3.12
- Chart.js live dashboard with demo fallback
- README with SQL deep dives, curl examples, star history
