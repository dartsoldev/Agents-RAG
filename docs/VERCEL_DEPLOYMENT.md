<!-- Purpose: provide executable Git/Vercel commands and explain persistent backend requirements. -->
# Deploy the frontend to Vercel

This release supports **Vercel frontend + separately hosted persistent backend**. It is not configured as an all-in-one Vercel serverless application. The current FastAPI service starts a polling worker, stores uploaded documents on disk and uses a relational database. Moving the entire app to serverless would require changing those components.

The frontend continues using relative `/api` URLs. Vercel forwards these requests to the backend using an [external rewrite](https://vercel.com/docs/routing/rewrites). This preserves the browser's same-origin login flow. API caching is explicitly disabled; do not enable edge caching for authenticated case data.

## 1. Host the backend first

Use the included Dockerfile on a persistent container host/VPS, with a mounted document volume and PostgreSQL. Do not store documents on an ephemeral container filesystem. Set these backend environment variables through that host's private environment settings:

```dotenv
APP_ENV=production
APP_URL=https://YOUR-PRODUCTION-FRONTEND.vercel.app
DEMO_MODE=false
SEED_DEMO=false
COOKIE_SECURE=true
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@DATABASE-HOST:5432/DATABASE
STORAGE_PATH=/app/data/documents
ADMIN_EMAIL=your-admin@example.com
ADMIN_PASSWORD=your-private-password-at-least-16-characters
WORKER_ENABLED=true
AI_PROVIDER=openai
OPENAI_API_KEY=your-private-api-key
OPENAI_MODEL=gpt-6-astra
```

Keep one application replica with one embedded worker for this release. The Docker startup command runs migrations and then Uvicorn. Mount the document volume at `/app/data`, writable by the container's `appuser`. External PostgreSQL should use your provider's required TLS settings. SMTP and Filevine settings, if used, also belong on the backend only. Alternatively use `AI_PROVIDER=demo` for local extractive research without OpenAI calls; real-mode seeding and email behavior still follow `DEMO_MODE=false`.

Verify `https://YOUR-BACKEND-HOST/api/health` returns `{"status":"ok"}`. Configure the backend reverse proxy and upload limits for the app's 20 MB uploads. Restrict and monitor access according to your firm's requirements.

## 2. Prepare and deploy from Windows PowerShell

Use Python 3.11+ and a current Node/npm installation. These commands do not deploy the backend:

```powershell
cd 'D:\Agents-Arav Law Firm'
git pull --ff-only origin main
python scripts/prepare_vercel.py --backend-url https://YOUR-BACKEND-HOST
cd deploy/vercel
npx vercel login
npx vercel link
npx vercel --prod
```

When linking, select your Vercel account/team and create or select a frontend project. Use framework **Other**, no install/build command, and output directory **public** if prompted. The generated configuration supplies the output directory. Deploy only from `deploy/vercel`, so the Vercel upload contains no Python backend, `.env`, notebooks or case database.

The [Vercel deploy CLI](https://vercel.com/docs/cli/deploy) prints the deployed URL. Set backend `APP_URL` to the exact stable production URL (or your final custom domain), without a trailing slash, and restart the backend. The frontend URL and backend origin are different settings. Do not point the API rewrite back at the frontend URL; that creates a proxy loop.

Before using real cases, verify login/logout, case retrieval, original-document download, a test upload and an actual completed worker job through the Vercel URL. Preview deployments have different origins and are intentionally rejected unless the backend is configured for that exact origin. Use a separate staging backend/database for previews rather than weakening the origin check.

## 3. Push future changes and redeploy

From the repository root:

```powershell
git status
git add .
git diff --cached --stat
git commit -m "Describe your change"
git push origin main
python scripts/prepare_vercel.py --backend-url https://YOUR-BACKEND-HOST
cd deploy/vercel
npx vercel --prod
```

The generated Vercel package is rebuilt explicitly after frontend changes. A GitHub push alone does not deploy this CLI package. `.env`, case files, local notebooks and `.vercel` account metadata remain ignored. Do not override the ignore rules with `git add -f` for those files.

## What has been verified

The package generator is tested for correct asset layout, API proxy target, disabled API caching, and rejection of URLs containing credentials. Actual Vercel deployment, remote backend provisioning and real provider connections require your accounts and have not been performed by these preparation commands.

Vercel's [FastAPI documentation](https://vercel.com/docs/frameworks/backend/fastapi) describes its function deployment model. This guide deliberately retains the existing persistent backend architecture instead of treating an ephemeral serverless filesystem as durable case storage.
