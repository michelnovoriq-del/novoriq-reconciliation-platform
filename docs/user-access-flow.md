# Novoriq user access flow

The backend is the sole authority for plans and entitlements. Browser query strings,
checkout clicks, local storage, and the Whop return page never activate paid access.

## Free Forever

```text
Landing → Register → Organization + owner + Free subscription + usage period
        → authenticated session → Onboarding/Dashboard → Reconcile immediately
```

Registration commits these records atomically. `ensure_default_free_subscription()`
is idempotent and repairs an organization with no subscription without replacing an
existing paid subscription. Free access does not depend on Whop.

## Professional and Firm

```text
Pricing → safe Login returnTo → explicit upgrade modal → Whop checkout
        → signed webhook → membership link → paid plan → account refresh → email
```

The modal displays the authenticated Novoriq email and requires acknowledgement.
`/billing/return` checks status at most six times, ten seconds apart. It only reports
backend state. A verified webhook (or authenticated authoritative synchronization)
is required to activate Professional or Firm.

## Account bootstrap

Authenticated clients initialize with `GET /account/bootstrap`. It returns user,
organization, subscription, current UTC-month usage, entitlements, and billing-link
state. The frontend fetches this snapshot once and exposes `refreshAccount()` after
login or billing changes.

## Safe redirects

Protected pages send logged-out users to `/login?returnTo=...`. Only same-application
relative paths beginning with one `/` are accepted. Absolute URLs, protocol-relative
URLs, malformed values, and backslash-based paths fall back to `/dashboard`.

## Commands

```bash
cd backend && ./.venv/bin/alembic upgrade head
cd backend && ./.venv/bin/python -m pytest
cd frontend && npm run build
cd frontend && npm run test:e2e
```

Whop tests must use test plan IDs and a test signing secret; never live credentials.
