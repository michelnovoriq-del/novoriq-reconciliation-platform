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
```

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
