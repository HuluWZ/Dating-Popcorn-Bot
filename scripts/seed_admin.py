"""Seed the first admin. Usage: python -m scripts.seed_admin [email] (password is generated and printed once)."""

import asyncio
import secrets
import string
import sys

from src.api.password_validator import validate_password_strength
from src.database.services import AdminService


def generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(20))
        if validate_password_strength(password)[0]:
            return password


async def main(email: str) -> None:
    if await AdminService.get_admin_by_email(email):
        print(f"Admin {email} already exists, nothing done")
        return
    password = generate_password()
    await AdminService.create_admin(full_name="Admin", email=email, password=password)
    print(f"Created admin {email}\nPassword: {password}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "admin@gmail.com"))
