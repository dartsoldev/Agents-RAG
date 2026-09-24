<!-- Purpose: identify the isolated Vercel CLI deployment directory. -->
# Vercel frontend package

From the repository root, run:

```powershell
python scripts/prepare_vercel.py --backend-url https://YOUR-BACKEND-HOST
cd deploy/vercel
npx vercel login
npx vercel link
npx vercel --prod
```

Replace the backend placeholder with your deployed HTTPS API origin. Do not run Vercel from the repository root: this application uses a persistent Python worker and document filesystem. The generator copies only frontend assets into `public/` and creates a same-origin `/api` proxy in `vercel.json`. Generated files and Vercel account metadata are ignored by Git. No API keys belong here.

See [the full deployment guide](../../docs/VERCEL_DEPLOYMENT.md) for backend environment variables and verification.
