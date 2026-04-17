"""User repository."""

from typing import Optional
from packages.database import connection as db
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRepository:

    async def get_by_id(self, user_id: str) -> Optional[dict]:
        row = await db.fetchrow("SELECT * FROM users WHERE id = \$1", user_id)
        return dict(row) if row else None

    async def get_by_email(self, email: str) -> Optional[dict]:
        row = await db.fetchrow("SELECT * FROM users WHERE email = \$1", email)
        return dict(row) if row else None

    async def get_by_api_key_hash(self, key_hash: str) -> Optional[dict]:
        row = await db.fetchrow(
            "SELECT * FROM users WHERE api_key_hash = \$1 AND is_active = true",
            key_hash,
        )
        return dict(row) if row else None

    async def create(self, email: str, password: str, full_name: str = None) -> dict:
        password_hash = pwd_context.hash(password)
        row = await db.fetchrow("""
            INSERT INTO users (email, password_hash, full_name)
            VALUES (\$1, \$2, \$3)
            RETURNING id, email, full_name, tier, created_at
        """, email, password_hash, full_name)
        return dict(row)

    async def verify_password(self, email: str, password: str) -> Optional[dict]:
        user = await self.get_by_email(email)
        if user and pwd_context.verify(password, user["password_hash"]):
            return user
        return None

    async def update_api_key_hash(self, user_id: str, key_hash: str):
        await db.execute(
            "UPDATE users SET api_key_hash = \$2, updated_at = NOW() WHERE id = \$1",
            user_id, key_hash,
        )
