"""
User Router — registration, login, profile management
POST /api/users/register
POST /api/users/login
GET  /api/users/profile/{user_id}
PUT  /api/users/profile/{user_id}
"""
import uuid
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from models.user import UserCreate, UserLogin
from db import users_col
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/users", tags=["users"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register")
async def register(data: UserCreate):
    existing = await users_col().find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    doc = {
        "user_id": user_id,
        "name": data.name,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "preferred_language": data.preferred_language,
        "career_goal": data.career_goal,
        "skill_level": data.skill_level,
        "xp": 0,
        "streak": 0,
        "badges": [],
        "teaching_style": "balanced",
        "last_active": datetime.utcnow(),
        "created_at": datetime.utcnow(),
    }
    await users_col().insert_one(doc)
    token = create_token(user_id)
    return {"user_id": user_id, "name": data.name, "token": token}


@router.post("/login")
async def login(data: UserLogin):
    user = await users_col().find_one({"email": data.email})
    if not user or not verify_password(data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await users_col().update_one({"user_id": user["user_id"]},
                                  {"$set": {"last_active": datetime.utcnow()}})
    token = create_token(user["user_id"])
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"],
        "skill_level": user.get("skill_level", "beginner"),
        "preferred_language": user.get("preferred_language", "english"),
        "career_goal": user.get("career_goal"),
        "xp": user.get("xp", 0),
        "streak": user.get("streak", 0),
        "badges": user.get("badges", []),
        "token": token,
    }


@router.get("/profile/{user_id}")
async def get_profile(user_id: str):
    user = await users_col().find_one({"user_id": user_id}, {"password_hash": 0, "_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/profile/{user_id}")
async def update_profile(user_id: str, updates: dict):
    # Whitelist updatable fields
    allowed = {"name", "preferred_language", "career_goal", "skill_level", "teaching_style"}
    safe = {k: v for k, v in updates.items() if k in allowed}
    if not safe:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    await users_col().update_one({"user_id": user_id}, {"$set": safe})
    return {"success": True, "updated": safe}
