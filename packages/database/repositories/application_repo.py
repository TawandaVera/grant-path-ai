"""Application pipeline repository."""

from typing import Optional
from packages.database import connection as db
import json


class ApplicationRepository:

    async def get_by_id(self, app_id: str) -> Optional[dict]:
        row = await db.fetchrow("""
            SELECT a.*, g.title as grant_title, g.funder_name, g.deadline as grant_deadline,
                   g.funding_amount_max
            FROM applications a
            JOIN grants g ON a.grant_id = g.id
            WHERE a.id = \$1
        """, app_id)
        return dict(row) if row else None

    async def list_by_org(self, org_id: str, status: str = None) -> list[dict]:
        if status and status != "all":
            rows = await db.fetch("""
                SELECT a.*, g.title as grant_title, g.funder_name,
                       g.deadline as grant_deadline, g.funding_amount_max,
                       g.deadline - NOW() as time_remaining
                FROM applications a
                JOIN grants g ON a.grant_id = g.id
                WHERE a.org_id = \$1 AND a.status = \$2
                ORDER BY g.deadline ASC
            """, org_id, status)
        else:
            rows = await db.fetch("""
                SELECT a.*, g.title as grant_title, g.funder_name,
                       g.deadline as grant_deadline, g.funding_amount_max,
                       g.deadline - NOW() as time_remaining
                FROM applications a
                JOIN grants g ON a.grant_id = g.id
                WHERE a.org_id = \$1
                ORDER BY g.deadline ASC
            """, org_id)
        return [dict(r) for r in rows]

    async def create(self, data: dict) -> dict:
        row = await db.fetchrow("""
            INSERT INTO applications (org_id, grant_id, user_id, project_title,
                status, funding_requested, internal_deadline, notes)
            VALUES (\$1,\$2,\$3,\$4,\$5,\$6,\$7,\$8)
            RETURNING *
        """,
            data["org_id"], data["grant_id"], data.get("user_id"),
            data["project_title"], data.get("status", "discovered"),
            data.get("funding_requested"), data.get("internal_deadline"),
            data.get("notes"),
        )
        return dict(row)

    async def update_status(self, app_id: str, status: str,
                            notes: str = None, award_amount: float = None):
        await db.execute("""
            UPDATE applications
            SET status = \$2, notes = COALESCE(\$3, notes),
                award_amount = COALESCE(\$4, award_amount),
                updated_at = NOW(),
                submission_date = CASE WHEN \$2 = 'submitted' THEN NOW() ELSE submission_date END,
                outcome = CASE WHEN \$2 IN ('awarded','declined') THEN \$2 ELSE outcome END
            WHERE id = \$1
        """, app_id, status, notes, award_amount)

    async def get_pipeline_stats(self, org_id: str) -> dict:
        row = await db.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status NOT IN ('awarded','declined','withdrawn')) as active,
                COUNT(*) FILTER (WHERE status = 'submitted') as submitted,
                COALESCE(SUM(award_amount) FILTER (WHERE outcome = 'awarded'), 0) as total_secured,
                COALESCE(SUM(funding_requested) FILTER (WHERE status = 'submitted'), 0) as pending_value
            FROM applications WHERE org_id = \$1
        """, org_id)
        return dict(row) if row else {}
