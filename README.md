# KYC Format Validator API

![CI](https://github.com/YOUR_USERNAME/kyc-validator/actions/workflows/ci.yml/badge.svg)

A REST API that checks whether Indian ID numbers are well-formed: **PAN, Aadhaar, GSTIN and IFSC**.

Built with FastAPI, PostgreSQL, SQLAlchemy, pytest and Docker.

> **What this is not:** it checks format and checksum only. It does not contact any government
> database, so it cannot tell you whether an ID was actually issued or who it belongs to.
> It is a first-line check that catches typos and junk input before a paid verification call.

## Features

- **Four validators** behind one interface: PAN, Aadhaar (Verhoeff checksum), GSTIN (mod-36 check character, state code, embedded PAN), IFSC.
- **Batch endpoint:** up to 100 IDs of mixed types in one request.
- **GSTIN-PAN match:** confirms a GSTIN and a PAN belong together.
- **API-key authentication:** keys are stored as SHA-256 hashes, never in plain text.
- **Sliding-window rate limiting** per API key, with a `Retry-After` header.
- **Privacy-safe audit log:** only masked IDs (`XXXXXXXX0124`) are stored or returned. Full numbers never touch the database.
- **Usage stats** per key, using `GROUP BY` and a SQL window function.
- **76 tests**, run on PostgreSQL in CI.

## Run it

You need Docker.

```bash
git clone https://github.com/YOUR_USERNAME/kyc-validator.git
cd kyc-validator
docker compose up --build
```

The API is at http://localhost:8000 and the interactive docs are at http://localhost:8000/docs.

### Without Docker

Uses a local SQLite file, so no database setup is needed.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
ADMIN_TOKEN=local-admin-token uvicorn app.main:app --reload
```

## Try it

**1. Create an API key** (the admin token comes from `docker-compose.yml`):

```bash
curl -X POST http://localhost:8000/api-keys \
  -H "X-Admin-Token: local-admin-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "demo"}'
```

```json
{"id": 1, "name": "demo", "api_key": "kyc_..."}
```

The key is shown once. Save it:

```bash
export KEY="kyc_..."
```

**2. Validate a PAN:**

```bash
curl -X POST http://localhost:8000/validate/pan \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"value": "AAAPA1234A"}'
```

```json
{
  "id_type": "pan",
  "is_valid": true,
  "masked_value": "XXXXXX234A",
  "errors": [],
  "details": {"holder_type": "Individual"}
}
```

**3. An invalid GSTIN explains what is wrong:**

```bash
curl -X POST http://localhost:8000/validate/gstin \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"value": "27AAAPA1234A1ZA"}'
```

```json
{
  "id_type": "gstin",
  "is_valid": false,
  "masked_value": "XXXXXXXXXXXA1ZA",
  "errors": ["Check character does not match"],
  "details": {}
}
```

**4. Validate a batch:**

```bash
curl -X POST http://localhost:8000/validate/batch \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"items": [
        {"id_type": "aadhaar", "value": "2345 6789 0124"},
        {"id_type": "ifsc", "value": "ABCD0123456"},
        {"id_type": "pan", "value": "12345"}
      ]}'
```

**5. See your usage:**

```bash
curl http://localhost:8000/stats -H "X-API-Key: $KEY"
```

```json
{
  "total_validations": 5,
  "by_type": [
    {"id_type": "aadhaar", "total": 1, "valid": 1, "invalid": 0},
    {"id_type": "gstin", "total": 1, "valid": 0, "invalid": 1},
    {"id_type": "ifsc", "total": 1, "valid": 1, "invalid": 0},
    {"id_type": "pan", "total": 2, "valid": 1, "invalid": 1}
  ],
  "daily": [{"day": "2026-11-24", "requests": 5, "running_total": 5}]
}
```

All ID numbers in this README and in the tests are made up.

## Endpoints

| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `/health` | none | Health check |
| GET | `/id-types` | none | List supported ID types |
| POST | `/validate/{id_type}` | API key | Validate one ID (`pan`, `aadhaar`, `gstin`, `ifsc`) |
| POST | `/validate/batch` | API key | Validate up to 100 IDs |
| POST | `/validate/gstin-pan-match` | API key | Check a GSTIN and PAN belong together |
| GET | `/stats` | API key | Usage counts for the calling key |
| POST | `/api-keys` | admin token | Create an API key |

## Validation rules

| ID | Rule |
|---|---|
| PAN | 5 letters, 4 digits, 1 letter. The 4th letter must be a known holder type (P = individual, C = company, ...). |
| Aadhaar | 12 digits, not starting with 0 or 1. The last digit is a Verhoeff checksum. |
| GSTIN | 15 characters: state code, the holder's PAN, entity number, `Z`, and a mod-36 check character. |
| IFSC | 4 letters, then `0`, then 6 letters or digits. |

## Design decisions

**One base class, one subclass per ID type.** `Validator` in `app/validators/base.py` owns the shared
steps (normalize, check, mask). Each subclass only writes its own `check`. Validators sit in a
registry keyed by name, so adding a new ID type means one new class and one registry entry.
The route code does not change.

**Full IDs are never stored.** The audit log keeps the last 4 characters and masks the rest.
Responses return the masked value too, so IDs do not end up in client logs.

**API keys are hashed.** The database holds SHA-256 hashes. A plain hash is enough because keys
are long and random. A leaked database does not give anyone a usable key.

**Invalid input returns 200, not 400.** "This PAN is malformed" is a successful answer to the
question the client asked. 4xx codes are kept for real request problems: no key (401),
unknown ID type (404), rate limit (429).

**Sliding-window rate limiter.** Each key has a deque of recent request times. Old times are
dropped from the front, and a request is rejected if the deque is full. A fixed window would
allow a double burst at the window boundary. A sliding window does not.

**Index on `(api_key_id, created_at)`.** The stats queries filter by key and group by day,
so this composite index covers them.

## Tests

```bash
pytest
```

Tests run on SQLite by default. To run them on PostgreSQL, as CI does:

```bash
TEST_DATABASE_URL=postgresql+psycopg2://kyc:kyc@localhost:5432/kyc_test pytest
```

The Verhoeff implementation is tested against published examples of the algorithm.
The rate limiter is tested with a fake clock, so no test sleeps.

## Project layout

```
app/
  main.py            app setup
  config.py          settings from environment variables
  database.py        engine and session
  models.py          ApiKey and ValidationLog tables
  schemas.py         request and response shapes
  auth.py            API-key check, admin check
  rate_limiter.py    sliding-window limiter
  validators/        one file per ID type, plus the base class and registry
  routers/           validate, stats, api-keys endpoints
tests/               unit tests and API tests
```

## Known limits and next steps

- The rate limiter is in memory, so it only works for a single process. Running several
  instances would need a shared store such as Redis.
- Tables are created on startup. A real deployment would use migrations (Alembic).
- IFSC is checked by format only. It could be checked against the RBI's published branch list.
- There is no endpoint yet to deactivate or rotate an API key.
