<!-- Purpose: record what was actually tested and which integrations still need external verification. -->
# Verification record

Build date: September 22, 2026. Host: Windows, Python 3.11. Dependency versions are pinned in `requirements.lock.txt`.

## Automated checks

Final result: **14 tests passed** (`python -m pytest -q`).

The isolated pytest suite covers:

- Intake through document indexing, monitoring, demand approval, settlement and closure.
- Session authentication/revocation, CSRF checks and paralegal approval restrictions.
- Duplicate intake/document rejection and repeat-monitor idempotency.
- Case-scoped retrieval and foreign-case source rejection.
- Missing evidence, arbitrary client-name matches and fabricated citation rejection.
- Mocked OpenAI semantic verification success/failure (no paid calls).
- Visible corrupt-document failure and local job retry.
- Approval-before-email and one-time simulated delivery.
- Invalid transitions, negative money, unsupported uploads and calendar output.
- Login rate limiting and safe configuration output.
- Fresh Alembic migration and repeat upgrade.
- Chunked oversized request rejection before the application parses the body.

Ruff lint and formatting checks pass. Frontend ES modules pass Node syntax checks. Docker Compose configuration validates.

## Browser verification

Signed in to the real local API through the rendered frontend. Verified dashboard case counts and document counts, case workspace, research answer rendering, original-source dialog and new-case form. Research returned the actual seeded medical record quote with its source. Checked the dashboard at a narrow mobile breakpoint: the page had no horizontal overflow. Restored the default viewport. No browser error/warning logs were reported during research verification.

The local app was restarted using `scripts/start.ps1`, proving the documented startup entry point works. Original database records and sessions remained available after restart.

## Not verified or not implemented

- Docker Desktop's Linux engine was not running. Container build, live PostgreSQL execution and production hosting were not tested. Compose syntax validation is not runtime validation.
- No OpenAI key, SMTP credentials or Filevine tenant was provided. Those live adapters were not exercised. Mock tests do not prove provider credentials or tenant compatibility.
- Full Filevine two-way sync, automatic OCR, live legal research providers, external messaging/phone channels and client portal are not implemented; see `INTEGRATIONS.md`.
- No security certification, legal/clinical accuracy certification, production load test, disaster-recovery drill, or enterprise readiness claim is made.

One dependency deprecation warning from Starlette/AnyIO was observed in tests; it did not fail the test suite.
