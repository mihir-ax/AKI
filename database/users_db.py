from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME, VALIDATION_TIME
import time

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
users = db.users
groups = db.groups  # To track groups

async def get_user(user_id):
    """Fetch user data from DB."""
    user = await users.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "last_validated_at": 0,
            "total_searches": 0,
            "is_admin": False,
            "is_banned": False,
            "ban_reason": None
        }
        await users.insert_one(user)
    return user

async def update_validation(user_id):
    """Update the last validation timestamp to now."""
    await users.update_one(
        {"user_id": user_id},
        {"$set": {"last_validated_at": int(time.time())}},
        upsert=True
    )

async def is_validated(user_id):
    """Check if the user has validated in the last 6 hours."""
    user = await get_user(user_id)
    last_val = user.get("last_validated_at", 0)
    current_time = int(time.time())
    return (current_time - last_val) < VALIDATION_TIME

async def increment_searches(user_id):
    """Track search count."""
    await users.update_one(
        {"user_id": user_id},
        {"$inc": {"total_searches": 1}}
    )

async def add_group(chat_id, title):
    await groups.update_one(
        {"chat_id": chat_id},
        {"$set": {"title": title}},
        upsert=True
    )

async def ban_user(user_id, reason):
    await users.update_one(
        {"user_id": user_id},
        {"$set": {"is_banned": True, "ban_reason": reason}}
    )

async def unban_user(user_id):
    await users.update_one(
        {"user_id": user_id},
        {"$set": {"is_banned": False, "ban_reason": None}}
    )

async def get_db_stats():
    # MongoDB stats for storage info
    stats = await db.command("dbStats")
    # Convert bytes to MB
    data_size = stats['dataSize'] / (1024 * 1024)
    storage_size = stats['storageSize'] / (1024 * 1024)
    return {
        "total_users": await users.count_documents({}),
        "total_groups": await groups.count_documents({}),
        "data_mb": round(data_size, 2),
        "storage_mb": round(storage_size, 2)
    }