import argparse
import asyncio
import getpass
import os
import sys

from auth_utils import get_password_hash
from database.repository import AdminRepository
from database.session import session_context

MIN_PASSWORD_LENGTH = 12


async def create_admin(username: str, password: str) -> None:
    username = username.strip()
    if not username:
        raise ValueError("Username is required")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    async with session_context() as session:
        repository = AdminRepository(session)
        if await repository.get_by_username(username):
            raise ValueError(f"Admin {username!r} already exists")
        await repository.create(username, get_password_hash(password))


def read_password() -> str:
    password = os.environ.get("ADMIN_PASSWORD")
    if password:
        return password
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Repeat password: "):
        raise ValueError("Passwords do not match")
    return password


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an admin account")
    parser.add_argument("username")
    arguments = parser.parse_args()
    try:
        asyncio.run(create_admin(arguments.username, read_password()))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"Created admin {arguments.username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
