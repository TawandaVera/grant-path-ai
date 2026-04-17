"""
Grant repository — all database operations for grants.
"""

from typing import Optional
from packages.database import connection as db
import logging
import json

logger = logging.getLogger("grantpath.repo.grants")


class GrantRepository:

    async def get_by_id(self, grant_id: str) -> Optional[dict]:
        row = await db.fetchrow(
            "SELECT * FROM grants WHERE id = \$1", grant_id
        )
        return dict(row) if row else None

    async def search(
        self,
        query: str = None,
        org_type: str = None,
        funder_type: str = None,
        state: str = None,
        funding_min: float = None,
        funding_max: float = None,
        deadline_after: str = None,
        categories: list[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Search grants with filters. Returns (results, total_count)."""

        conditions = ["status = 'active'", "deadline > NOW()"]
        params = []
        param_idx = 0

        if org_type:
            param_idx += 1
            conditions.append(f"${param_idx} = ANY(org_type_eligibility)")
            params.append(org_type)

        if funder_type:
            param_idx += 1
            conditions.append(f"funder_type = ${param_idx}")
            params.append(funder_type)

        if state:
            param_idx += 1
            conditions.append(
                f"(geographic_restrictions = '{{}}' OR ${param_idx} = ANY(geographic_restrictions))"
            )
            params.append(state)

        if funding_min is not None:
            param_idx += 1
            conditions.append(f"funding_amount_max >= ${param_idx}")
            params.append(funding_min)

        if funding_max is not None:
            param_idx += 1
            conditions.append(f"funding_amount_min <= ${param_idx}")
            params.append(funding_max)

        if deadline_after:
            param_idx += 1
            conditions.append(f"deadline > ${param_idx}")
            params.append(deadline_after)

        if categories:
            param_idx += 1
            conditions.append(f"category_tags && ${param_idx}")
            params.append(categories)

        if query:
            param_idx += 1
            conditions.append(
                f"(title ILIKE ${param_idx} OR description ILIKE ${param_idx} "
                f"OR funder_name ILIKE ${param_idx})"
            )
            params.append(f"%{query}%")

        where_clause = " AND ".join(conditions)

        # Count total
        count_query = f"SELECT COUNT(*) FROM grants WHERE {where_clause}"
        total = await db.fetchval(count_query, *params)

        # Fetch page
        param_idx += 1
        limit_param = param_idx
        param_idx += 1
        offset_param = param_idx
        params.extend([limit, offset])

        data_query = f"""
            SELECT * FROM grants
            WHERE {where_clause}
            ORDER BY deadline ASC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        rows = await db.fetch(data_query, *params)

        return [dict(r) for r in rows], total

    async def vector_search(
        self, embedding: list[float], limit: int = 20, filters: dict = None
    ) -> list[dict]:
        """Semantic similarity search using pgvector."""

        try:
            # pgvector cosine distance search
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            query = f"""
                SELECT *, 1 - (embedding <=> '{embedding_str}'::vector) as similarity
                FROM grants
                WHERE status = 'active' AND deadline > NOW() AND embedding IS NOT NULL
                ORDER BY embedding <=> '{embedding_str}'::vector
                LIMIT \$1
            """
            rows = await db.fetch(query, limit)
            return [dict(r) for r in rows]

        except Exception as e:
            logger.warning(f"Vector search failed (pgvector not available?): {e}")
            # Fallback to text search
            return []

    async def get_active_count(self) -> int:
        return await db.fetchval(
            "SELECT COUNT(*) FROM grants WHERE status = 'active' AND deadline > NOW()"
        )

    async def insert(self, grant: dict):
        await db.execute("""
            INSERT INTO grants (id, title, funder_name, funder_type, description,
                description_compressed, eligibility_criteria, funding_amount_min,
                funding_amount_max, deadline, application_url, category_tags,
                geographic_restrictions, org_type_eligibility, cost_sharing_required,
                scoring_criteria, status)
            VALUES (\$1,\$2,\$3,\$4,\$5,\$6,\$7,\$8,\$9,\$10,\$11,\$12,\$13,\$14,\$15,\$16,\$17)
            ON CONFLICT (id) DO NOTHING
        """,
            grant["id"], grant["title"], grant["funder_name"],
            grant.get("funder_type"), grant.get("description"),
            grant.get("description_compressed"),
            json.dumps(grant.get("eligibility_criteria", [])),
            grant.get("funding_amount_min"), grant.get("funding_amount_max"),
            grant.get("deadline"), grant.get("application_url"),
            grant.get("category_tags", []),
            grant.get("geographic_restrictions", []),
            grant.get("org_type_eligibility", []),
            grant.get("cost_sharing_required", False),
            json.dumps(grant.get("scoring_criteria", [])),
            grant.get("status", "active"),
        )
