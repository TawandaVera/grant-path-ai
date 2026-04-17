import logging
import asyncio
from typing import Optional
from datetime import datetime

import google.generativeai as genai

from packages.core.config import settings
from packages.core.security import InputSanitizer
from packages.core.exceptions import AIError, RateLimitError

logger = logging.getLogger("grantpath.ai_engine")

# Configure Gemini on import
genai.configure(api_key=settings.GEMINI_API_KEY)


# ─── Model Registry ───────────────────────────────────────────────────────────

MODELS = {
    "fast":     "gemini-1.5-flash",   # Low-cost, fast responses
    "balanced": "gemini-1.5-pro",     # Default for most tasks
    "advanced": "gemini-1.5-pro",     # Reserved for complex drafting
}

GENERATION_CONFIG = {
    "fast":     {"temperature": 0.3, "max_output_tokens": 1024},
    "balanced": {"temperature": 0.4, "max_output_tokens": 4096},
    "advanced": {"temperature": 0.5, "max_output_tokens": 8192},
}

# Token costs per task (approximate — used for budget tracking)
TOKEN_COSTS = {
    "match":      500,
    "draft":      4000,
    "review":     2000,
    "eligibility": 800,
    "summarize":  600,
}


class AIEngine:
    """
    Manages all Gemini API interactions.
    Handles prompt building, sanitization, token budgeting, and error recovery.
    """

    def __init__(self):
        self._models = {}

    def _get_model(self, tier: str = "balanced") -> genai.GenerativeModel:
        if tier not in self._models:
            model_name = MODELS.get(tier, MODELS["balanced"])
            config = GENERATION_CONFIG.get(tier, GENERATION_CONFIG["balanced"])
            self._models[tier] = genai.GenerativeModel(
                model_name=model_name,
                generation_config=config,
            )
        return self._models[tier]

    async def _call(
        self,
        prompt: str,
        tier: str = "balanced",
        retries: int = 2,
    ) -> str:
        """
        Make a Gemini API call with retry logic and error wrapping.
        """
        model = self._get_model(tier)

        for attempt in range(retries + 1):
            try:
                # Run blocking SDK call in thread pool
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: model.generate_content(prompt),
                )

                if not response.text:
                    raise AIError("AI returned an empty response")

                return response.text.strip()

            except AIError:
                raise

            except Exception as e:
                error_str = str(e).lower()

                if "quota" in error_str or "rate" in error_str:
                    raise RateLimitError(
                        "AI service rate limit reached. Please try again shortly.",
                        context={"provider": "gemini"},
                    )

                if attempt < retries:
                    wait = 2 ** attempt  # Exponential backoff: 1s, 2s
                    logger.warning(f"Gemini call failed (attempt {attempt + 1}), retrying in {wait}s: {e}")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Gemini call failed after {retries + 1} attempts: {e}")
                    raise AIError(
                        "AI service is temporarily unavailable. Please try again.",
                        cause=e,
                    )

    # ─── Task Methods ─────────────────────────────────────────────────────────

    async def match_grants(
        self,
        org_profile: dict,
        grants: list[dict],
        top_n: int = 10,
    ) -> list[dict]:
        """
        Use AI to rank and explain grant matches for an organization profile.
        Returns grants with added 'ai_score' and 'ai_reason' fields.
        """
        # Build concise grant summaries (avoid sending full descriptions)
        grant_summaries = "\n".join([
            f"[{i+1}] ID:{g['id']} | {g['title']} | {g['funder_name']} "
            f"| ${g.get('funding_amount_min', 0):,}–${g.get('funding_amount_max', 0):,} "
            f"| Deadline: {g.get('deadline', 'N/A')} "
            f"| Tags: {', '.join(g.get('category_tags', []))}"
            for i, g in enumerate(grants[:50])  # Cap at 50 to control tokens
        ])

        prompt = f"""You are a grant matching expert. Analyze these grants for the organization below.

ORGANIZATION PROFILE:
- Name: {org_profile.get('name', 'Unknown')}
- Mission: {org_profile.get('mission', 'Not provided')}
- Type: {org_profile.get('org_type', 'Not specified')}
- Location: {org_profile.get('location', 'Not specified')}
- Focus areas: {', '.join(org_profile.get('focus_areas', []))}
- Budget range: ${org_profile.get('annual_budget_min', 0):,}–${org_profile.get('annual_budget_max', 0):,}

AVAILABLE GRANTS:
{grant_summaries}

TASK: Rank the top {top_n} most relevant grants. For each, provide:
- grant_number (the [N] from above)
- score (0.0–1.0 match confidence)
- reason (1 sentence explaining the match)

Respond ONLY as a JSON array:
[{{"grant_number": 1, "score": 0.92, "reason": "..."}}]"""

        raw = await self._call(prompt, tier="fast")

        # Parse JSON response safely
        import json
        import re
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not json_match:
            raise AIError("AI returned malformed match results")

        rankings = json.loads(json_match.group())

        # Merge AI scores back onto grant objects
        grant_map = {i + 1: g for i, g in enumerate(grants[:50])}
        results = []
        for item in rankings[:top_n]:
            grant = grant_map.get(item.get("grant_number"))
            if grant:
                results.append({
                    **grant,
                    "ai_score": item.get("score", 0.0),
                    "ai_reason": item.get("reason", ""),
                })

        return sorted(results, key=lambda x: x["ai_score"], reverse=True)

    async def draft_section(
        self,
        grant: dict,
        section: str,
        org_profile: dict,
        existing_content: str = "",
        word_limit: int = 500,
    ) -> dict:
        """
        Draft or improve a single grant application section.
        """
        sanitized_existing, was_modified = InputSanitizer.sanitize_for_llm(existing_content)

        prompt = f"""You are an expert grant writer helping draft a grant application.

GRANT: {grant['title']}
FUNDER: {grant['funder_name']}
SECTION: {section}
WORD LIMIT: 
