"""Back up a stopped local SQLite installation and document store to a new archive."""

import argparse
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from backend.config import settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", help="New ZIP path; will not overwrite an existing backup")
    parser.add_argument(
        "--server-stopped",
        action="store_true",
        help="Confirm API and worker are stopped for a consistent document snapshot",
    )
    args = parser.parse_args()
    if not args.server_stopped:
        raise SystemExit("Stop the server/worker and pass --server-stopped before taking a backup.")
    if not settings.database_url.startswith("sqlite:///"):
        raise SystemExit("Use pg_dump plus a matching document-volume snapshot for PostgreSQL.")
    source = Path(settings.database_url.removeprefix("sqlite:///")).resolve()
    if not source.is_file():
        raise SystemExit("Database not found")
    destination = Path(args.destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        copy = Path(work) / "arav.db"
        with sqlite3.connect(source) as src, sqlite3.connect(copy) as dst:
            src.backup(dst)
        with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
            archive.write(copy, "arav.db")
            for file in Path(settings.storage_path).iterdir():
                if file.is_file():
                    archive.write(file, f"documents/{file.name}")
    print("Backup created. Store it in an encrypted, access-controlled location.")


if __name__ == "__main__":
    main()
