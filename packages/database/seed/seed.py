"""
Seed database with sample data for development.
Run: python -m packages.database.seed.seed
"""

import random
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from packages.database.connection import SyncDB
from packages.database.migrations.runner import run_migrations

logger = logging.getLogger("grantpath.seed")
logging.basicConfig(level=logging.INFO, format="%(message)s")

SEED_FILE = Path(__file__).parent / "grants_seed.json"


def generate_grants(count: int = 500) -> list[dict]:
    """Generate realistic sample grants."""

    funders = [
        ("National Science Foundation", "federal", "NSF"),
        ("National Institutes of Health", "federal", "NIH"),
        ("Department of Education", "federal", "ED"),
        ("USDA", "federal", "USDA"),
        ("EPA", "federal", "EPA"),
        ("Ford Foundation", "foundation", "FORD"),
        ("Gates Foundation", "foundation", "GATES"),
        ("Robert Wood Johnson Foundation", "foundation", "RWJF"),
        ("Kresge Foundation", "foundation", "KRESGE"),
        ("MacArthur Foundation", "foundation", "MAC"),
        ("W.K. Kellogg Foundation", "foundation", "KELLOGG"),
        ("New York State", "state", "NYS"),
        ("California Arts Council", "state", "CAC"),
        ("Texas Workforce Commission", "state", "TWC"),
    ]

    categories = [
        ("STEM Education",
