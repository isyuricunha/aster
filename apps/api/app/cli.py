import argparse
import asyncio
import getpass
from collections.abc import Sequence

from sqlalchemy import select, update

from app.auth_dependencies import get_password_service
from app.auth_service import utc_now
from app.db import AsyncSessionFactory
from app.models import AuthSession, User


async def reset_password() -> int:
    password = getpass.getpass("New password: ")
    confirmation = getpass.getpass("Confirm new password: ")
    if password != confirmation:
        print("Passwords do not match.")
        return 1
    if len(password) < 12 or len(password) > 256 or not password.strip():
        print("Password must contain between 12 and 256 characters.")
        return 1

    async with AsyncSessionFactory() as database:
        user = await database.scalar(select(User).where(User.id == 1))
        if user is None:
            print("Initial setup has not been completed.")
            return 1

        now = utc_now()
        user.password_hash = get_password_service().hash(password)
        user.password_changed_at = now
        await database.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await database.commit()

    print("Password updated. Every existing session was revoked.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "reset-password",
        help="Reset the single owner password and revoke every session.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "reset-password":
        return asyncio.run(reset_password())
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
