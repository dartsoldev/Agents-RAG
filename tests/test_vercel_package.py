"""Verify the frontend-only deployment package never copies private workspace data."""

import json

import pytest

from scripts.prepare_vercel import ASSETS, prepare


def test_package_contains_only_frontend_and_proxy_config(tmp_path):
    prepare("https://backend.example.com/", tmp_path)
    config = json.loads((tmp_path / "vercel.json").read_text())
    assert config["rewrites"] == [
        {"source": "/api/:path*", "destination": "https://backend.example.com/api/:path*"}
    ]
    assert config["outputDirectory"] == "public"
    assert set(p.name for p in (tmp_path / "public" / "static").iterdir()) == set(ASSETS)
    assert (tmp_path / "public" / "index.html").is_file()
    assert {p.name for p in tmp_path.iterdir()} == {"public", "vercel.json"}
    headers = {item["key"]: item["value"] for item in config["headers"][0]["headers"]}
    assert headers["Cache-Control"] == "private, no-store"
    assert headers["x-vercel-enable-rewrite-caching"] == "0"


@pytest.mark.parametrize(
    "url",
    [
        "http://backend.example.com",
        "https://user:secret@backend.example.com",
        "https://backend.example.com/path",
        "https://backend.example.com?key=secret",
    ],
)
def test_reject_unsafe_backend_origins(tmp_path, url):
    with pytest.raises(ValueError):
        prepare(url, tmp_path)
