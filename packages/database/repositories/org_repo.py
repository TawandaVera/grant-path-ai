"""Organization repository."""

from typing import Optional
from packages.database import connection as db
import json


class OrgRepository:

    async def get_by_id(self, org_id: str) -> Optional[dict]:
        row = await db.fetchrow("SELECT * FROM organizations WHERE id = \$1", org_id)
        return dict(row) if row else None

    async def upsert(self, org_id: str, data: dict) -> dict:
        await db.execute("""
            INSERT INTO organizations (id, name, org_type, mission_statement, mission_short,
                location, annual_budget, team_size, focus_areas, target_population,
                capacity_statement, indirect_cost_rate, ein, uei)
            VALUES (\$1,\$2,\$3,\$4,\$5,\$6,\$7,\$8,\$9,\$10,\$11,\$12,\$13,\$14)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name, org_type = EXCLUDED.org_type,
                mission_statement = EXCLUDED.mission_statement,
                mission_short = EXCLUDED.mission_short,
                location = EXCLUDED.location, annual_budget = EXCLUDED.annual_budget,
                team_size = EXCLUDED.team_size, focus_areas = EXCLUDED.focus_areas,
                target_population = EXCLUDED.target_population,
                capacity_statement = EXCLUDED.capacity_statement,
                indirect_cost_rate = EXCLUDED.indirect_cost_rate,
                updated_at = NOW()
        """,
            org_id, data["name"], data["org_type"],
            data.get("mission_statement"), data.get("mission_short"),
            json.dumps(data.get("location", {})),
            data.get("annual_budget"), data.get("team_size"),
            data.get("focus_areas", []), data.get("target_population"),
            data.get("capacity_statement"), data.get("indirect_cost_rate", 10.0),
            data.get("ein"), data.get("uei"),
        )
        return await self.get_by_id(org_id)
