import logging
from datetime import date
from typing import Optional

from packages.database import connection as db
from packages.core.config import settings
from packages.core.exceptions import RateLimitError

logger = logging.getLogger("grantpath.token_budget")

# Daily token budgets by role
DAILY_BUDGETS = {
    "free":    5_000,
    "premium": settings.DAILY_PREMIUM_TOKEN_BUDGET,  # 50,000 from config
    "admin":   999_999,
}

TASK_TOKEN_COSTS = {
    "match":       500,
    "draft":      4_000,
    "review":     2_000,
    "eligibility":  800,
    "summarize":    600,
}


class TokenBudgetManager:
    """
    Tracks and enforces daily AI token usage per user.
    Uses DB for persistence; falls back gracefully on DB errors.
    """

    @staticmethod
    async def get_usage(user_id: str) -> dict:
        """Get today's token usage for a user."""
        today = date.today().isoformat()
        row = await db.fetchrow(
            """
            SELECT tokens_used, tasks_run
            FROM ai_token_usage
            WHERE user_id = $1 AND usage_date = $2
            """,
            user_id, today,
        )
        if row:
            return {"tokens_used": row["tokens_used"], "tasks_run": row["tasks_run"]}
        return {"tokens_used": 0, "tasks_run": 0}

    @staticmethod
    async def check_and_reserve(
        user_id: str,
        role: str,
        task: str,
    ) -> int:
        """
        Check if user has budget for this task.
        Returns the token cost if allowed, raises RateLimitError if not.
        """
        cost = TASK_TOKEN_COSTS.get(task, 1000)
        budget = DAILY_BUDGETS.get(role, DAILY_BUDGETS["free"])

        try:
            usage = await TokenBudgetManager.get_usage(user_id)
            used = usage["tokens_used"]

            if used + cost > budget:
                remaining = max(0, budget - used)
                raise RateLimitError(
                    f"Daily AI token budget exceeded. "
                    f"Used {used:,}/{budget:,} tokens. Resets at midnight UTC.",
                    context={
                        "tokens_used": used,
                        "tokens_budget": budget,
                        "tokens_remaining": remaining,
                        "task": task,
                        "task_cost": cost,
                        "role": role,
                    },
                )
            return cost

        except RateLimitError:
            raise
        except Exception as e:
            # Don't block users on budget tracking errors — log and allow
            logger.error(f"Token budget check failed for {user_id}: {e}")
            return cost

    @staticmethod
    async def record_usage(user_id: str, task: str, tokens_used: int):
        """Record actual token usage after a successful AI call."""
        today = date.today().isoformat()
        try:
            await db.execute(
                """
                INSERT INTO ai_token_usage (user_id, usage_date, tokens_used, tasks_run)
                VALUES ($1, $2, $3, 1)
                ON CONFLICT (user_id, usage_date)
                DO UPDATE SET
                    tokens_used = ai_token_usage.tokens_used + EXCLUDED.tokens_used,
                    tasks_run   = ai_token_usage.tasks_run + 1
                """,
                user_id, today, tokens_used,
            )
        except Exception as e:
            logger.error(f"Failed to record token usage for {user_id}: {e}")

    @staticmethod
    async def get_budget_status(user_id: str, role: str) -> dict:
        """Return full budget status for the user (used in API responses)."""
        budget = DAILY_BUDGETS.get(role, DAILY_BUDGETS["free"])
        usage = await TokenBudgetManager.get_usage(user_id)
        used = usage["tokens_used"]

        return {
            "tokens_used": used,
            "tokens_budget": budget,
            "tokens_remaining": max(0, budget - used),
            "tasks_run_today": usage["tasks_run"],
            "percentage_used": round((used / budget) * 100, 1) if budget else 0,
            "resets": "midnight UTC",
        }
