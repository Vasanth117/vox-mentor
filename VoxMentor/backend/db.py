from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

_client: AsyncIOMotorClient | None = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client

def get_db():
    return get_client()[DB_NAME]

# Collection shortcuts
def users_col():
    return get_db()["users"]

def sessions_col():
    return get_db()["sessions"]

def progress_col():
    return get_db()["progress"]

def mistakes_col():
    return get_db()["mistakes"]

def skill_tree_col():
    return get_db()["skill_tree"]

def challenges_col():
    return get_db()["challenges"]

def journal_col():
    return get_db()["journal"]


def roadmaps_col():
    return get_db()["roadmaps"]


def projects_col():
    return get_db()["projects"]


def interviews_col():
    return get_db()["interviews"]


def revision_queue_col():
    return get_db()["revision_queue"]
