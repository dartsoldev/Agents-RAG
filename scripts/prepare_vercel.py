"""Build an isolated static Vercel package and proxy API requests to a persistent backend."""

import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ("app.js", "api.js", "ui.js", "views.js", "styles.css")


def prepare(backend_url: str, destination: Path) -> None:
    parsed = urlsplit(backend_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Use an HTTPS backend origin without credentials, path, query or fragment")
    origin = backend_url.rstrip("/")
    public = destination / "public"
    static = public / "static"
    static.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "frontend" / "index.html", public / "index.html")
    for name in ASSETS:
        shutil.copyfile(ROOT / "frontend" / name, static / name)
    config = {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "framework": None,
        "outputDirectory": "public",
        "rewrites": [{"source": "/api/:path*", "destination": origin + "/api/:path*"}],
        "headers": [
            {
                "source": "/api/:path*",
                "headers": [
                    {"key": "Cache-Control", "value": "private, no-store"},
                    {"key": "CDN-Cache-Control", "value": "no-store"},
                    {"key": "Vercel-CDN-Cache-Control", "value": "no-store"},
                    {"key": "x-vercel-enable-rewrite-caching", "value": "0"},
                ],
            },
            {
                "source": "/(.*)",
                "headers": [
                    {"key": "X-Content-Type-Options", "value": "nosniff"},
                    {"key": "X-Frame-Options", "value": "DENY"},
                    {"key": "Referrer-Policy", "value": "same-origin"},
                    {
                        "key": "Content-Security-Policy",
                        "value": "default-src 'self'; script-src 'self'; style-src 'self'; "
                        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
                        "base-uri 'self'; form-action 'self'",
                    },
                ],
            },
        ],
    }
    (destination / "vercel.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", required=True, help="HTTPS origin of your running backend")
    args = parser.parse_args()
    try:
        prepare(args.backend_url, ROOT / "deploy" / "vercel")
    except ValueError as exc:
        parser.error(str(exc))
    print("Prepared deploy/vercel. Only frontend assets and API proxy configuration are included.")
    print("Next: cd deploy/vercel; npx vercel login; npx vercel link; npx vercel --prod")
    print("Set backend APP_URL to your exact Vercel production URL and COOKIE_SECURE=true.")


if __name__ == "__main__":
    main()
