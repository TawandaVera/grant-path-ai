"""
Simple SQL migration runner.
Tracks applied migrations in a _migrations table.
"""

import os
import sys
import logging
from pathlib import Path

from packages.database.connection import SyncDB

logger = logging.getLogger("grantpath.migrations")

MIGRATIONS_DIR = Path(__file__).parent


def run_migrations(reset: bool = False):
    """Run all pending migrations in order."""

    db = SyncDB()
    db.connect()

    try:
        if reset:
            logger.warning("⚠️  RESETTING DATABASE — dropping all tables")
            db.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")

        # Create migrations tracking table
        db.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Find migration files
        migration_files = sorted([
            f for f in MIGRATIONS_DIR.glob("*.sql")
            if f.name[0].isdigit()
        ])

        # Get already applied
        applied = {
            row["filename"]
            for row in db.query("SELECT filename FROM _migrations")
        }

        # Apply pending migrations
        pending = [f for f in migration_files if f.name not in applied]

        if not pending:
            logger.info("✅ No pending migrations")
            return

        for migration_file in pending:
            logger.info(f"  Applying: {migration_file.name}")
            sql = migration_file.read_text()

            try:
                db.execute(sql)
                db.execute(
                    "INSERT INTO _migrations (filename) VALUES (%s)",
                    (migration_file.name,)
                )
                logger.info(f"  ✅ Applied: {migration_file.name}")
            except Exception as e:
                logger.error(f"  ❌ Failed: {migration_file.name} — {e}")
                raise

        logger.info(f"✅ Applied {len(pending)} migrations")

    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reset = "--reset" in sys.argv
    run_migrations(reset=reset)
