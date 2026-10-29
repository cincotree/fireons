import argparse
import asyncio
import getpass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_utils import get_password_hash
from database.models import User
from database.session import session_context


async def ensure_superadmin(session: AsyncSession, email: str, username: str, password: str | None) -> User:
    user = (
        await session.execute(select(User).where(or_(User.email == email, User.username == username)))
    ).scalar_one_or_none()
    if user is None:
        if not password:
            raise ValueError("A password is required to create a new user")
        user = User(email=email, username=username, hashed_password=get_password_hash(password))
        session.add(user)
    user.is_superadmin = True
    await session.flush()
    return user


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a superadmin user or promote an existing one")
    parser.add_argument("--email", required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()

    password = getpass.getpass("Password (leave empty to promote an existing user): ") or None
    async with session_context() as session:
        user = await ensure_superadmin(session, args.email, args.username, password)
        print(f"{user.username} is now a superadmin")


if __name__ == "__main__":
    asyncio.run(main())
