"""
Shared constants and enums.
"""

from enum import Enum


class OrgType(str, Enum):
    NONPROFIT = "nonprofit"
    EDUCATION = "education"
    GOVERNMENT = "government"
    TRIBAL = "tribal"
    SMALL_BUSINESS = "small_business"
    INDIVIDUAL = "individual"


class FunderType(str, Enum):
    FEDERAL = "federal"
    STATE = "state"
    FOUNDATION = "foundation"
    CORPORATE = "corporate"


class ApplicationStatus(str, Enum):
    DISCOVERED = "discovered"
    EVALUATING = "evaluating"
    PREPARING = "preparing"
    DRAFTING = "drafting"
    INTERNAL_REVIEW = "internal_review"
    FINAL_REVIEW = "final_review"
    SUBMITTED = "submitted"
    AWAITING_DECISION = "awaiting_decision"
    AWARDED = "awarded"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class ProposalSection(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    STATEMENT_OF_NEED = "statement_of_need"
    PROJECT_DESCRIPTION = "project_description"
    GOALS_OBJECTIVES = "goals_objectives"
    METHODS_APPROACH = "methods_approach"
    EVALUATION_PLAN = "evaluation_plan"
    ORGANIZATIONAL_CAPACITY = "organizational_capacity"
    SUSTAINABILITY_PLAN = "sustainability_plan"
    BUDGET_NARRATIVE = "budget_narrative"


class ModelTier(str, Enum):
    NONE = "none"         # Pure code
    LOCAL = "local"       # Local OS models
    FREE_API = "free_api" # Gemini/Groq free
    PREMIUM = "premium"   # GPT-4o/Claude


class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ADMIN = "admin"


# ─── Section importance for model routing ───
SECTION_TIER_MAP = {
    ProposalSection.EXECUTIVE_SUMMARY: ModelTier.FREE_API,
    ProposalSection.STATEMENT_OF_NEED: ModelTier.FREE_API,
    ProposalSection.PROJECT_DESCRIPTION: ModelTier.FREE_API,
    ProposalSection.GOALS_OBJECTIVES: ModelTier.FREE_API,
    ProposalSection.METHODS_APPROACH: ModelTier.FREE_API,
    ProposalSection.EVALUATION_PLAN: ModelTier.FREE_API,
    ProposalSection.ORGANIZATIONAL_CAPACITY: ModelTier.FREE_API,
    ProposalSection.SUSTAINABILITY_PLAN: ModelTier.FREE_API,
    ProposalSection.BUDGET_NARRATIVE: ModelTier.FREE_API,
}

# Sections eligible for premium upgrade when user requests "best quality"
PREMIUM_ELIGIBLE_SECTIONS = {
    ProposalSection.EXECUTIVE_SUMMARY,
    ProposalSection.STATEMENT_OF_NEED,
    ProposalSection.PROJECT_DESCRIPTION,
}
