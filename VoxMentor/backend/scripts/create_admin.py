from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path
from uuid import uuid4

from passlib.context import CryptContext
from pymongo import MongoClient
from jose import jwt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import MONGO_URI, DB_NAME, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update an admin user")
    parser.add_argument("--mongo-uri", default=MONGO_URI)
    parser.add_argument("--db-name", default=DB_NAME)
    parser.add_argument("--name", default="Administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--preferred-language", default="english")
    parser.add_argument("--career-goal", default="Platform Administration")
    parser.add_argument("--skill-level", default="advanced")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    now = datetime.now(UTC)

    try:
        client = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except Exception as exc:
        raise RuntimeError(
            "Unable to connect to MongoDB. Provide a valid URI with --mongo-uri or set MONGO_URI in backend/.env"
        ) from exc

    db = client[args.db_name]
    users = db["users"]

    existing = users.find_one({"email": args.email})
    user_id = existing.get("user_id") if existing else str(uuid4())

    doc = {
        "user_id": user_id,
        "name": args.name,
        "email": args.email,
        "password_hash": pwd_ctx.hash(args.password),
        "preferred_language": args.preferred_language,
        "career_goal": args.career_goal,
        "skill_level": args.skill_level,
        "xp": 999999,
        "streak": 999,
        "badges": ["admin", "all-access"],
        "teaching_style": "balanced",
        "role": "admin",
        "is_admin": True,
        "permissions": ["*"],
        "last_active": now,
        "updated_at": now,
    }

    if existing:
        users.update_one({"email": args.email}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
        action = "updated"
    else:
        doc["created_at"] = now
        users.insert_one(doc)
        action = "created"

    token = create_token(user_id)
    print(f"Admin user {action}: {args.email}")
    print(f"user_id: {user_id}")
    print(f"token: {token}")


if __name__ == "__main__":
    main()
 