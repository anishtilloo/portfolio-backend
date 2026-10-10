"""Small admin commands.

uv run python -m app.cli create-admin     # create or reset your login
uv run python -m app.cli seed             # add starter posts to an empty blog
"""

import argparse
import asyncio
import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select

from app.db import SessionLocal, engine
from app.models import User
from app.security import hash_password
from app.seed import seed

MIN_PASSWORD_LENGTH = 10


async def create_admin(email: str, password: str) -> str:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if user is None:
            session.add(User(email=email, password_hash=hash_password(password)))
            outcome = "Created"
        else:
            user.password_hash = hash_password(password)
            outcome = "Updated the password for"
        await session.commit()
    return f"{outcome} {email}. Sign in at /admin."


async def run_seed() -> str:
    async with SessionLocal() as session:
        added = await seed(session)
    if not any(added.values()):
        return "Nothing added: the blog already has content."
    return f"Added {added['posts']} posts and {added['links']} saved articles."


def ask_credentials(args: argparse.Namespace) -> tuple[str, str]:
    email = args.email or input("Email: ").strip()
    try:
        email = TypeAdapter(EmailStr).validate_python(email)
    except ValidationError:
        sys.exit(f"'{email}' is not a valid email address.")

    password = args.password
    if password is None:
        password = getpass.getpass("Password: ")
        if getpass.getpass("Password again: ") != password:
            sys.exit("The two passwords are different. Nothing was changed.")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Use a password of at least {MIN_PASSWORD_LENGTH} characters.")
    return email, password


async def main_async(args: argparse.Namespace) -> str:
    try:
        if args.command == "create-admin":
            return await create_admin(*ask_credentials(args))
        return await run_seed()
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    admin = commands.add_parser("create-admin", help="Create your login, or reset its password")
    admin.add_argument("--email")
    admin.add_argument("--password", help="Omit to be asked for it without echoing")

    commands.add_parser("seed", help="Add starter posts and saved articles to an empty blog")

    print(asyncio.run(main_async(parser.parse_args())))


if __name__ == "__main__":
    main()
