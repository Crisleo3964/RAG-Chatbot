"""CLI for managing users.

Usage:
    python manage_users.py --create --email alice@example.com --role user
    python manage_users.py --list
    python manage_users.py --reset-admin-password
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage RAG chatbot users.")
    parser.add_argument("--create", action="store_true", help="Create a new user")
    parser.add_argument("--email", type=str, default="", help="Email for the new user")
    parser.add_argument("--password", type=str, default="", help="Password (auto-generated if omitted)")
    parser.add_argument("--role", type=str, default="user", choices=["user", "admin"], help="Role for the new user")
    parser.add_argument("--list", action="store_true", help="List all users")
    parser.add_argument("--reset-admin-password", action="store_true", help="Reset admin password")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from auth.auth_service import get_auth_service

    auth = get_auth_service()

    if args.reset_admin_password:
        from auth.auth_service import password_hash
        lock_path = auth._lock_path
        from filelock import FileLock
        lock = FileLock(str(lock_path))
        with lock:
            data = auth._read()
            admin = None
            for uid, entry in data.items():
                if entry.get("role") == "admin":
                    admin = uid
                    break
            if admin is None:
                logger.error("No admin user found.")
                sys.exit(1)
            new_password = str(uuid.uuid4())[:12]
            data[admin]["hashed_password"] = password_hash.hash(new_password)
            auth._write(data)
            print(f"Admin password reset:")
            print(f"  email:    {data[admin]['email']}")
            print(f"  password: {new_password}")
        return

    if args.create:
        if not args.email:
            logger.error("--email is required when --create is specified")
            sys.exit(1)
        if auth.get_user_by_email(args.email):
            logger.error("Email already exists: %s", args.email)
            sys.exit(1)
        password = args.password or str(uuid.uuid4())[:12]
        user = auth.register_user(
            email=args.email,
            password=password,
            role=args.role,
        )
        print(f"Created user:")
        print(f"  user_id:  {user.user_id}")
        print(f"  email:    {user.email}")
        print(f"  role:     {user.role}")
        print(f"  password: {password}")
        print(f"\nLogin at POST /auth/token with email+password.")
        print(f"Then use the returned token as Authorization: Bearer <token>.")

    if args.list:
        users = auth.list_users()
        if not users:
            print("No users found.")
        else:
            print(f"{'user_id':<36} {'email':<30} {'role':<10}")
            print("-" * 76)
            for u in users:
                print(f"{u.user_id:<36} {u.email:<30} {u.role:<10}")


if __name__ == "__main__":
    main()
