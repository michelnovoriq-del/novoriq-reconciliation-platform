# Current production configuration

Last reviewed: 2026-07-14

## Endpoints

- Frontend: `https://agenticreconcilliation.netlify.app`
- Backend: `https://novoriq-reconciliation-platform.onrender.com`
- Database: Neon PostgreSQL (the connection string must never be committed or logged)

The backend accepts exactly `https://agenticreconcilliation.netlify.app` as its production browser origin. Configured origins are trimmed, deduplicated, validated, and have trailing slashes removed. Browser origins are still matched exactly, so an incoming value with a trailing slash is rejected. JSON arrays are preferred, while safely parsed comma-separated values remain compatible. Empty values, invalid schemes, URL paths, embedded credentials, and production wildcards fail configuration rather than being silently allowed. Local development separately accepts `http://localhost:3000` and `http://127.0.0.1:3000` only when no explicit allow-list is supplied.

Authentication currently uses an `Authorization: Bearer` token. Therefore production CORS does not enable credentialed cookie transport. `Authorization` is explicitly accepted. The browser client currently persists the token in local storage; migrating to short-lived access tokens plus rotated secure HttpOnly refresh cookies is a remaining security task.

## Render environment

Set these exact non-secret values:

```dotenv
APP_ENVIRONMENT=production
DEBUG=false
FRONTEND_URL=https://agenticreconcilliation.netlify.app
BACKEND_PUBLIC_URL=https://novoriq-reconciliation-platform.onrender.com
BACKEND_CORS_ORIGINS=["https://agenticreconcilliation.netlify.app"]
ALLOWED_HOSTS=["novoriq-reconciliation-platform.onrender.com"]
STORAGE_BACKEND=s3
ALLOW_EPHEMERAL_TEST_UPLOADS=false
WHOP_WEBHOOK_ENABLED=false
WHOP_MEMBERSHIP_SYNC_ENABLED=false
WHOP_WEBHOOK_RAW_PAYLOAD_LOGGING=false
```

Also set secret/private values in Render only:

- `DATABASE_URL`: Neon PostgreSQL SQLAlchemy URL; production forces SSL and pool pre-ping.
- `JWT_SECRET_KEY`: random, non-placeholder, at least 32 characters.
- `SUPPORT_EMAIL`: monitored support address.
- For S3-compatible private storage: `S3_BUCKET_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, plus the provider's endpoint/region where required.
- Enable Whop flags only after their API key, webhook secret, company ID and paid-plan IDs are configured.

Production startup rejects missing database/JWT/public URLs, weak JWT keys, debug mode, wildcard or incorrect CORS/hosts, and incomplete S3 settings. Local storage is accepted for controlled synthetic deployment tests only; it is ephemeral on Render and must not receive real customer financial data.

## Netlify environment

```dotenv
NEXT_PUBLIC_API_BASE_URL=https://novoriq-reconciliation-platform.onrender.com
API_PROXY_TARGET=https://novoriq-reconciliation-platform.onrender.com
NEXT_PUBLIC_WHOP_PROFESSIONAL_CHECKOUT_URL=
NEXT_PUBLIC_WHOP_FIRM_CHECKOUT_URL=
NEXT_PUBLIC_WHOP_ENTERPRISE_CHECKOUT_URL=
```

Missing Whop checkout URLs must remain a controlled unavailable state; the backend alone grants paid entitlements from verified membership state.

## Deployment commands

Run migrations from a trusted deployment job with the production `DATABASE_URL`:

```bash
cd backend
./.venv/bin/python -m alembic current
./.venv/bin/python -m alembic heads
./.venv/bin/python -m alembic upgrade head
```

There is one intended migration head: `20260710_0005`. Default plans are seeded idempotently by code using the unique plan code. Expected plans are Free Forever (`$0`, 2 runs/month, 2 files/run, 2,500 rows/file, 1 user, 1 workspace, 7-day detail retention), Professional (`$279/month`), and Firm (`$499/month`).

## Live verification

```bash
curl -i -X OPTIONS 'https://novoriq-reconciliation-platform.onrender.com/auth/register' \
  -H 'Origin: https://agenticreconcilliation.netlify.app' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type,authorization'

curl -i -X OPTIONS 'https://novoriq-reconciliation-platform.onrender.com/auth/register' \
  -H 'Origin: https://malicious.example' \
  -H 'Access-Control-Request-Method: POST'

curl -i 'https://novoriq-reconciliation-platform.onrender.com/health'
curl -i 'https://novoriq-reconciliation-platform.onrender.com/ready'

python scripts/production_smoke_test.py
```

The first preflight must return `Access-Control-Allow-Origin: https://agenticreconcilliation.netlify.app`; the malicious-origin response must not include that header.

After deployment, open `/register`, create a new synthetic account, confirm the success flow reaches onboarding/dashboard with **Free Forever** and **0 of 2** runs, then log out and sign in again at `/login`. Confirm browser developer tools show no raw `NetworkError`, `Failed to fetch`, or CORS exception in page content.

## Final acceptance checklist

- [ ] Frontend production URL opens
- [ ] Backend health returns 200
- [ ] Backend readiness returns 200
- [ ] Exact Netlify origin allowed, without trailing slash
- [ ] Wildcard, malicious origin, trailing-slash origin, and localhost rejected in production
- [ ] CORS preflight succeeds with content-type and authorization
- [x] Automated CORS headers pass on 401, 422, and safe 500 responses
- [ ] Registration, login, logout, and navigation work from Netlify
- [ ] Free Forever unlocks instantly and shows 0 of 2 runs
- [ ] Account state survives logout/login and a backend restart
- [x] Pricing source shows $0, $279, and $499
- [ ] Free plan is marked Current plan in the deployed account
- [x] Paid plans require backend-verified Whop state
- [ ] Neon connection and persistence verified
- [ ] Alembic production migration is current
- [x] One migration head exists and plan seed is idempotent by plan code
- [ ] Organization isolation and file ownership integration tests pass against PostgreSQL
- [x] Upload metadata/type, size/row entitlement, acknowledgement, sensitive-data detection, randomized key, and path containment controls are present
- [ ] Persistent private object storage confirmed before real customer uploads
- [ ] Safe synthetic reconciliation, export, file deletion, and run deletion pass
- [x] Safe production errors and request IDs are covered by tests
- [x] Backend tests pass
- [x] Frontend lint passes (warnings only)
- [x] Frontend production build passes
- [ ] Non-destructive production smoke passes
- [ ] Playwright deployed flow passes with synthetic fixtures

Do not mark production ready until every unchecked critical item above has been verified in the deployed environment.
