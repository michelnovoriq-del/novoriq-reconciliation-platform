# Novoriq Reconciliation Agent Web

Next.js frontend for the beta-ready reconciliation workflow: authentication, upload, preview, normalization, run creation, deterministic matching, traffic-light review, approve/reject, and CSV export.

## Development

```bash
npm install
npm run dev
```

The frontend expects:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

Netlify production must use exactly:

```bash
NEXT_PUBLIC_API_BASE_URL=https://novoriq-reconciliation-platform.onrender.com
NEXT_PUBLIC_SITE_URL=https://agenticreconcilliation.netlify.app
API_PROXY_TARGET=https://novoriq-reconciliation-platform.onrender.com
```

The browser client centralizes API requests in `lib/api/client.ts`. Authentication failures are mapped to user-safe messages; raw fetch/browser exceptions are never rendered by the login or registration forms.

## Public product SEO

Indexable routes are `/`, `/pricing`, `/features`, `/how-it-works`, three `/use-cases/*` pages, `/security`, `/data-retention`, `/privacy`, `/terms`, and `/support`.

`lib/site-config.ts` is the single source of truth for canonical, Open Graph, sitemap, and robots origins. It removes a trailing slash and requires an explicit HTTPS `NEXT_PUBLIC_SITE_URL` in production. Public pages have unique server-rendered metadata and contextual links. `/sitemap.xml` contains only the public routes; `/robots.txt` references it and restricts private crawl paths. Auth, onboarding, billing-return, and authenticated layouts set `noindex, nofollow`; authentication remains the security boundary.

Pricing retains authenticated plan-state hydration and the existing Whop flow. Static marketing pages do not fetch account data.

Run `npm run lint`, `npm test`, `npm run build`, then start the build and run `SEO_BASE_URL=http://localhost:3000 npm run verify:seo`. Search Console and custom-domain instructions are in `../docs/`.

## E2E

```bash
npm run test:e2e
```

## Manual MVP flow

1. Register or log in.
2. Upload and normalize `../novoriq-reconciliation-api/sample_data/sample_invoices.csv`.
3. Upload and normalize `../novoriq-reconciliation-api/sample_data/sample_bank_statement.csv` using its bank-specific headers.
4. Create a run from the two normalized files.
5. Select **Run Matching**, then **Review results**.
6. Review green, yellow, and red buckets, approve/reject suggestions, and select **Export CSV**.

The frontend intentionally excludes billing, payments, live accounting integrations, AI agents, and enterprise permission features.
