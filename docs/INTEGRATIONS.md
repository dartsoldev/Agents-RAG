<!-- Purpose: show exactly where keys belong and distinguish working adapters from unimplemented integrations. -->
# Credentials and integrations

All settings live in the project-root `.env`, loaded by the backend. Restart the server after changes. Never paste keys into `frontend/`, source control, browser storage or case documents. The Integrations page shows status only, never credentials.

## OpenAI research

Start with a **new real-mode database** (see README). Set:

```dotenv
DEMO_MODE=false
SEED_DEMO=false
ADMIN_PASSWORD=your-new-long-private-password
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-6-astra
EMBEDDINGS_ENABLED=false
```

`OPENAI_MODEL` is configurable; select a model available to your API project that supports Responses structured outputs. The integration uses `responses.parse`, typed schemas and `store=False`, based on the [official structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs). No paid call was made during the build.

For semantic retrieval set `EMBEDDINGS_ENABLED=true` and `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` **before uploading documents**. Vectors are persisted in the relational database. Uploaded document passages are sent to OpenAI for embedding and relevant excerpts are sent for research. Provider retention and contractual requirements must be configured for the firm's confidential data. `store=False` does not itself establish a zero-retention agreement.

No live web/case-law search is connected. Upload authoritative research as category `legal` if you want it included in a case's evidence search. The app will not invent precedents from model memory.

## Email

```dotenv
SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=your-approved-sender@example.com
```

Use a test SMTP inbox first. STARTTLS is required. An attorney/admin reviews and optionally edits a welcome or follow-up draft, approves it, then separately clicks **Send approved email**. Demo mode marks delivery `simulated`. Demand packets are never sent through this button. `delivery_unknown` or `sending` must be reconciled against provider records; avoid duplicate resends.

This is SMTP support, not Gmail/Outlook OAuth mailbox synchronization. Incoming email ingestion, WhatsApp, SMS, RingCentral calls and DocuPost delivery are not implemented in this release.

## Filevine

Implemented: verify and link an **existing** project using the v2 gateway, bearer token, organization ID and user ID. This release does not create Filevine contacts/projects, synchronize custom sections/phases, or ingest Filevine webhooks. Local case creation works independently of Filevine.

```dotenv
FILEVINE_BASE_URL=https://api.filevineapp.com
FILEVINE_ACCESS_TOKEN=short-lived-bearer-token
FILEVINE_ORG_ID=your-org-id
FILEVINE_USER_ID=your-user-id
```

Obtain the client registration and PAT from your Filevine account, then exchange them according to [Filevine's official gateway authentication instructions](https://support.filevine.com/hc/en-us/articles/27944810461851-Authenticate-Requests-to-the-API-Gateway). A PAT is not the same as the resulting bearer token. The adapter does not refresh expired tokens automatically: update the token in `.env` and restart. Set the correct regional gateway for your tenant.

In a case's Overview, choose **Link Filevine project**, enter its numeric ID and verify. Credentials and real tenant behavior were not tested during this build. Full two-way automation needs the firm's actual project type, section field mappings, phase IDs, webhook contract and sandbox verification; `FILEVINE_PROJECT_TYPE_ID` is reserved for that extension and currently unused.

## Calendar and documents

Tasks → Calendar downloads `.ics` deadlines for calendar import. Google/Outlook live calendar sync is not connected. Deadlines are entered by staff; the app does not calculate statutes of limitation.

Searchable PDF, DOCX, UTF-8 TXT and MD are supported. Scanned PDFs, photos and image OCR need an OCR step outside this release. The app rejects unreadable PDFs with a visible failure and retry workflow. There is no silent OCR simulation.
