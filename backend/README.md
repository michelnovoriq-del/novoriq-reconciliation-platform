# Novoriq Reconciliation Agent API

Novoriq Reconciliation Agent is a CSV/Excel-first reconciliation tool for accountants, bookkeepers, and finance operators.

The MVP helps users upload two financial files, preview columns, map messy fields into a standard format, normalize records, run deterministic matching, review green/yellow/red reconciliation results, approve or reject matches, and export a clean CSV report.

## Current MVP Status

The current beta MVP supports:

* User registration and login
* JWT authentication
* Organization/workspace creation on registration
* CSV upload and preview
* Column mapping
* CSV normalization into `normalized_records`
* Row-level validation with invalid source rows stored in `rejected_records`
* Reconciliation run creation
* Deterministic matching
* Green/yellow/red result buckets
* Approve/reject match decisions
* Audit logging
* CSV export

### Deterministic matching policy

The matcher is deterministic and intentionally conservative. It is designed to reduce false
positives before beta users review financial data.

* **Green (`matched`)** means high-confidence financial evidence: the amount is exact or differs
  only trivially, the dates are close, and reference or customer/description evidence is strong.
* **Yellow (`possible_match`)** means the pair is plausible but requires human review. Yellow
  candidates must be within five days, have at least two supporting signals, and pass hard amount
  and reference safety gates.
* **Red (`unmatched_file_a` / `unmatched_file_b`)** means no acceptable one-to-one candidate was
  found, or the available evidence was too weak.

Before row matching, the service compares meaningful reference overlap, exact and fee-close amount
overlap, customer overlap, and date ranges. Weakly related files automatically use strict mode and
should produce mostly red results. Customer or description similarity alone never creates a
possible match. Generic references such as payout, settlement, transfer, manual, or unknown values
are treated cautiously, especially when amounts differ.

Possible matches require financial evidence. Large amount differences with weak references are
not suggested, and confidence scores never override the safety gates. Verify column mappings before
trusting results; mapping a generic description column as the reference field reduces match quality.

> **Beta note:** If unrelated files produce many yellow results, check column mapping and file
> compatibility before using the output.

## Stack

* Python 3.11+
* FastAPI
* PostgreSQL
* SQLAlchemy 2.x
* Alembic
* Pydantic v2
* JWT authentication
* bcrypt password hashing
* pandas for CSV parsing and preview
* openpyxl prepared for Excel parsing
* RapidFuzz for text similarity
* Docker Compose

## MVP Flow

1. Register and log in.
2. Upload the first financial file.
3. Preview the file columns and sample rows.
4. Map the file columns to Novoriq standard fields.
5. Normalize the first file.
6. Upload the second financial file.
7. Preview and normalize the second file.
8. Create a reconciliation run using the two different files.
9. Run deterministic matching.
10. Review green, yellow, and red result buckets.
11. Approve or reject suggested matches.
12. Export the reconciliation CSV.

## Standard Normalized Fields

Novoriq maps messy file columns into these standard fields:

* `date`
* `amount`
* `reference`
* `description`
* `customer_name`
* `currency`

Example mapping for a bank file:

```json
{
  "date": "paid_on",
  "amount": "total_received",
  "reference": "transaction_id",
  "description": "description",
  "customer_name": "customer",
  "currency": "currency"
}
```

## Matching Logic

The matcher uses:

* Decimal-based amount comparison
* Date distance
* Reference similarity
* Description/customer similarity
* RapidFuzz text scoring

A File B record is assigned at most once.

Re-running a completed match is rejected to preserve review history.

Result buckets:

* Green: high-confidence matches
* Yellow: possible matches needing review
* Red: unmatched or rejected records

## API Endpoints

### Health

* `GET /health`

### Auth

* `POST /auth/register`
* `POST /auth/login`
* `GET /auth/me`

### Files

* `POST /files/upload`
* `GET /files/{file_id}/preview`
* `POST /files/{file_id}/normalize`
* `GET /files/{file_id}/rejected-records`

### Reconciliation Runs

* `POST /reconciliation-runs`
* `GET /reconciliation-runs`
* `GET /reconciliation-runs/{run_id}`
* `POST /reconciliation-runs/{run_id}/run`
* `GET /reconciliation-runs/{run_id}/results`
* `GET /reconciliation-runs/{run_id}/export`

### Match Review

* `POST /match-results/{match_id}/approve`
* `POST /match-results/{match_id}/reject`

## Setup

```bash
cd novoriq-reconciliation-api
cp .env.example .env
docker compose up --build
```

Open:

* API docs: `http://localhost:8000/docs`
* Health check: `http://localhost:8000/health`

## Environment Variables

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/novoriq
JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
UPLOAD_DIR=uploads
```

For local non-Docker runs, use a host-reachable database URL:

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/novoriq
```

## Migrations

Run migrations inside the API container:

```bash
docker compose exec api alembic upgrade head
```

Create future migrations:

```bash
docker compose exec api alembic revision --autogenerate -m "describe change"
docker compose exec api alembic upgrade head
```

For local non-Docker development:

```bash
alembic upgrade head
```

## Example User Flow

### Register

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@example.com",
    "password": "supersecret123",
    "full_name": "Owner Example",
    "organization_name": "Example Accounting"
  }'
```

### Login

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"supersecret123"}' \
  | python -c "import json,sys; print(json.load(sys.stdin)[\"access_token\"])")
```

### Upload a CSV

```bash
FILE_ID=$(curl -s -X POST http://localhost:8000/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_data/sample_invoices.csv" \
  | python -c "import json,sys; print(json.load(sys.stdin)[\"id\"])")
```

### Preview

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/files/$FILE_ID/preview
```

### Normalize

```bash
curl -X POST http://localhost:8000/files/$FILE_ID/normalize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "date",
    "amount": "amount",
    "reference": "reference",
    "description": "description",
    "customer_name": "customer_name",
    "currency": "currency"
  }'
```

Normalization validates the mapping before processing rows. Valid rows are saved to
`normalized_records`; invalid rows are saved to `rejected_records` without aborting the valid
rows. Files may therefore have a `normalized_with_rejections` status and can still continue to
reconciliation. If every row is invalid, the API stores the rejections, marks the file
`failed_normalization`, and returns a structured HTTP 400 response.

Example partial-success response:

```json
{
  "uploaded_file_id": "FILE_ID",
  "status": "normalized_with_rejections",
  "total_rows": 5,
  "valid_rows": 2,
  "rejected_rows": 3,
  "rejected_examples": [
    {
      "id": "REJECTED_RECORD_ID",
      "uploaded_file_id": "FILE_ID",
      "source_row_number": 2,
      "raw_data": {"date": "bad-date", "amount": "100.00", "reference": "INV-2"},
      "rejection_reason": "invalid_date",
      "field_errors": {"date": "Could not parse date value: bad-date"},
      "created_at": "2026-06-22T12:00:00Z"
    }
  ],
  "message": "Normalized 2 rows. Rejected 3 rows with validation errors."
}
```

Review rejected rows (the endpoint returns up to 100 records per request):

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/files/$FILE_ID/rejected-records?offset=0&limit=100"
```

### Create a Reconciliation Run

After uploading and normalizing a second file:

```bash
curl -X POST http://localhost:8000/reconciliation-runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_a_id":"FIRST_FILE_ID","file_b_id":"SECOND_FILE_ID"}'
```

### Run Matching

```bash
curl -X POST http://localhost:8000/reconciliation-runs/RUN_ID/run \
  -H "Authorization: Bearer $TOKEN"
```

### View Results

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/reconciliation-runs/RUN_ID/results
```

### Approve a Match

```bash
curl -X POST http://localhost:8000/match-results/MATCH_ID/approve \
  -H "Authorization: Bearer $TOKEN"
```

### Reject a Match

```bash
curl -X POST http://localhost:8000/match-results/MATCH_ID/reject \
  -H "Authorization: Bearer $TOKEN"
```

### Export CSV

```bash
curl -L -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/reconciliation-runs/RUN_ID/export \
  -o reconciliation_export.csv
```

## Manual Beta Checklist

Before giving the app to beta users, confirm:

* [ ] Registration works.
* [ ] Login works.
* [ ] Authenticated routes require a valid token.
* [ ] User cannot access another organization’s files, runs, records, or matches.
* [ ] Two CSV files can be uploaded.
* [ ] Both files can be previewed.
* [ ] Both files can be normalized with expected mappings.
* [ ] A run can be created only from two different organization-owned files.
* [ ] Matching produces green, yellow, and red buckets.
* [ ] Suggested matches can be approved.
* [ ] Suggested matches can be rejected.
* [ ] Export downloads all result rows.
* [ ] Bad CSVs return clear errors.
* [ ] Empty or unmapped files return clear errors.
* [ ] Bad rows are rejected without crashing normalization.
* [ ] Rejected rows can be reviewed.
* [ ] Partially valid files can continue into reconciliation.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

## Excluded From This MVP

The current MVP intentionally excludes:

* Payments
* Usage gates
* Stripe integration
* Live QuickBooks/Xero APIs
* AI agents
* LangGraph
* MCP/RAG
* PDF extraction
* Enterprise SSO
* Advanced roles
* Advanced analytics
* Automatic accounting decisions

## Current Product Boundary

This MVP is not a full accounting system.

It is a reconciliation workflow tool that helps users:

1. Bring messy payment files into one system.
2. Normalize inconsistent columns.
3. Match transactions deterministically.
4. Review exceptions.
5. Export a clean reconciliation report.

The next phase is to improve matching accuracy, add better exception explanations, and collect feedback from private beta users.
