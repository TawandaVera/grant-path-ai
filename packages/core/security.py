"""
Input sanitization and validation utilities.
Prevents SQL injection, XSS, and prompt injection.
"""

import re
import html
import logging

logger = logging.getLogger("grantpath.security")


class InputSanitizer:
    """Sanitize all user inputs before processing."""

    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC)\b)",
        r"(--|;|/\*|\*/)",
        r"('(\s*)(OR|AND)(\s*)('|1|true))",
    ]

    PROMPT_INJECTION_PATTERNS = [
        r"(ignore\s+(previous|above|all)\s+(instructions?|prompts?|rules?))",
        r"(you\s+are\s+now\s+)",
        r"(system\s*:\s*)",
        r"(forget\s+(everything|all|your))",
        r"(new\s+instructions?\s*:)",
        r"(jailbreak|DAN\s+mode)",
    ]

    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 10000) -> str:
        if not text:
            return ""
        text = text[:max_length]
        text = text.replace("\x00", "")
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @classmethod
    def sanitize_search_query(cls, query: str, max_length: int = 500) -> str:
        query = cls.sanitize_text(query, max_length)
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Potential SQL injection: {query[:100]}")
                query = re.sub(pattern, "", query, flags=re.IGNORECASE)
        return query.strip()

    @classmethod
    def sanitize_for_llm(cls, text: str, max_length: int = 5000) -> str:
        text = cls.sanitize_text(text, max_length)
        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential prompt injection: {text[:200]}")
                text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)
        return text

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        return html.escape(text, quote=True)

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        filename = filename.replace("/", "_").replace("\\", "_")
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        filename = filename[:255].lstrip(".")
        return filename or "unnamed_file"

    @classmethod
    def validate_email(cls, email: str) -> bool:
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

    @classmethod
    def validate_id(cls, value: str) -> bool:
        return bool(re.match(r'^[a-zA-Z0-9\-_]{3,50}$', value))
