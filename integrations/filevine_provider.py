"""Verify an existing Filevine project through the v2 gateway; no remote writes are implicit."""

import re

import httpx

from backend.config import settings


def get_project(project_id):
    if not re.fullmatch(r"[0-9]{1,20}", project_id):
        raise ValueError("Filevine project ID must be numeric")
    if settings.demo_mode:
        raise ValueError("Filevine calls are disabled in demo mode")
    if not all(
        [
            settings.filevine_access_token,
            settings.filevine_org_id,
            settings.filevine_user_id,
        ]
    ):
        raise ValueError("Configure Filevine access token, organization ID and user ID")
    if not settings.filevine_base_url.startswith("https://"):
        raise ValueError("Filevine requires an HTTPS gateway URL")
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        response = client.get(
            f"{settings.filevine_base_url.rstrip('/')}/fv-app/v2/Projects/{project_id}",
            headers={
                "Authorization": f"Bearer {settings.filevine_access_token}",
                "x-fv-orgid": settings.filevine_org_id,
                "x-fv-userid": settings.filevine_user_id,
            },
        )
        response.raise_for_status()
        return response.json()
