<!-- Purpose: primary setup, operating instructions, release scope and documentation entry point. -->
# Arav · AI Case Operations

A runnable, single-firm case operations system inspired by your research: intake, evidence collection, medical/insurance tracking, source-linked research, attorney review, demand preparation and settlement/closure. Separate backend, frontend, database, orchestrator, sub-agent, prompt and integration folders.

**Start here:** [Roman Urdu run guide](docs/RUN_GUIDE_ROMAN_URDU.md) · [Architecture](docs/ARCHITECTURE.md) · [Keys and integrations](docs/INTEGRATIONS.md)

**Deployment:** [Vercel frontend + persistent backend commands](docs/VERCEL_DEPLOYMENT.md). Do not deploy the repository root to Vercel as-is; use the isolated frontend package generator described in that guide.

## Run on Windows

Requires Python 3.11+ and internet for the initial dependency install. Node is not required.

```powershell
cd 'D:\Agents-Arav Law Firm'
.\scripts\setup.ps1
.\scripts\start.ps1
```

Open [the application](http://127.0.0.1:8000). Demo login:

| Email | Password |
| --- | --- |
| `admin@arav.local` | `ChangeMe-Demo-2026!` |

The setup script creates `.env`, a `.venv`, and migrates SQLite. Four explicitly fictional cases are seeded on first startup. The embedded worker indexes the sample records within seconds. No keys or external services are needed for demo. Keep the terminal running; Ctrl+C stops it. Cases survive restarts.

If PowerShell script execution is disabled, run `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1`, then the same command with `start.ps1`. This applies to that process, not a machine-wide policy change.

## What's implemented

- Responsive staff dashboard, searchable case list, case workspace and attorney queue.
- Revocable cookie sessions, hashed passwords, admin/attorney/paralegal roles and account tools.
- Duplicate-safe intake with document checklist, initial tasks and welcome draft.
- Private PDF/DOCX/TXT/MD uploads, checksum checks, document jobs and page/section citations.
- Offline keyword retrieval; optional OpenAI embeddings and structured research with a second verifier.
- Medical and insurance forms, gap monitoring, follow-up tasks and recorded offers.
- Durable local agent jobs, retries, periodic monitoring and audit history.
- Editable approval drafts; explicitly approved SMTP email delivery or demo simulation.
- Demand review packet, gated stage transitions, settlement amount and closure.
- Existing Filevine project verification/linking, case JSON export and calendar `.ics` export.
- SQLite local mode, PostgreSQL Docker setup, schema migration, backup utility and CI tests.

## Scope you should know before real clients

This is a working application release, **not a claim of enterprise production readiness**. Full Filevine contact/project creation and two-way sync, provider-specific webhooks, live case-law search, automatic OCR, client-facing portal, RingCentral/WhatsApp/SMS, e-signatures, incoming email and cloud deployment are not implemented. Medical extraction is indexed text; medical/insurance structured facts are confirmed by staff. The demand output is a factual review packet, not a completed legal demand letter. No real provider credentials were used to test live integrations.

The firm owns legal decisions. Research answers can still be wrong; inspect cited records. No legal deadline, eligibility, coverage, liability, or settlement amount is decided by an agent. This version grants active firm staff access to all matters; it is not multi-tenant or per-case restricted. It has not been load-tested for 1,000-case enterprise workloads.

## Configure real mode

Stop the demo server. Use a **new database and document directory**, a new admin password and no demo seeding:

```dotenv
DEMO_MODE=false
SEED_DEMO=false
DATABASE_URL=sqlite:///./data/real-cases.db
STORAGE_PATH=./data/real-documents
ADMIN_EMAIL=your-admin@example.com
ADMIN_PASSWORD=replace-with-a-private-16-plus-character-password
AI_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-6-astra
```

This starts a local real-mode evaluation; use PostgreSQL and proper hosting for deployment. Production additionally requires `APP_ENV=production`, `APP_URL=https://your-host`, `COOKIE_SECURE=true`, PostgreSQL and a strong bootstrap password. The server fails startup on unsafe production defaults. `.env` changes need a restart; changing the bootstrap password does not reset existing accounts.

API keys are entered **only in root `.env`**. See [integrations](docs/INTEGRATIONS.md) for each provider's actual supported scope and key fields. Do not commit `.env`, database files, uploads or backups.

## PostgreSQL with Docker

Docker Desktop must be running. Copy `.env.example` to `.env`, add a strong `POSTGRES_PASSWORD` (use URL-safe characters), configure the other settings, then:

```powershell
docker compose up --build -d
docker compose logs -f app
```

Open the same local URL. Stop with `docker compose down` (without `-v`, so data volumes remain). The database has no published host port. Both volumes persist. Production needs an HTTPS reverse proxy, encrypted storage, backups, monitoring and your firm's provider agreements/access review. The included compose file is a local deployment configuration; Docker/PostgreSQL runtime verification is recorded in `docs/VERIFICATION.md`.

## Test and maintain

```powershell
.\scripts\test.ps1
.\.venv\Scripts\python.exe -m scripts.manage_user create attorney@example.com --name 'Sarah Mitchell' --role attorney
.\.venv\Scripts\python.exe -m scripts.manage_user reset-password admin@arav.local
.\.venv\Scripts\python.exe -m scripts.manage_user deactivate former-staff@example.com
```

Password commands use hidden terminal prompts. Session access is revoked on account maintenance. Keep at least one active admin account.

For a local SQLite backup, stop server and worker first:

```powershell
.\.venv\Scripts\python.exe -m scripts.backup backups/arav-backup.zip --server-stopped
```

Backups contain private case information. Store them on an encrypted restricted volume; never publish them. Restore into a new location, point `.env` at the restored database and document folder, then verify login, case data and original-file downloads before replacing an active installation. PostgreSQL uses `pg_dump` with a matching stopped document-volume snapshot.

API documentation: [local Swagger](http://127.0.0.1:8000/api/docs) (development only). API mutations require cookie authentication plus `X-Arav-Request: 1`; browser UI adds this header. Documentation's built-in mutation console does not automatically add it. Current API tests demonstrate the request contract.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Port 8000 already in use | Stop the previous server before starting another instance |
| Request origin denied | Use `http://127.0.0.1:8000`, matching `APP_URL` |
| No such table | Run `python -m alembic upgrade head` using the project virtual environment |
| Jobs stay queued | Enable the embedded worker, or run one standalone worker |
| Scanned PDF fails | OCR it to a searchable PDF, then upload it |
| Research returns insufficient evidence | Upload relevant documents and wait for status `ready` |
| OpenAI error | Check API key, model access and API billing; no fallback answer is fabricated |
| Filevine verification fails | Check bearer expiry, regional gateway, org/user IDs and project permissions |
| Email delivery uncertain | Check SMTP provider records before manual reconciliation; do not blindly resend |
