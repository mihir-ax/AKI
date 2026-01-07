from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME
from datetime import datetime

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
daily_stats = db.daily_stats

async def increment_gen(date_str):
    """Links generate hone ka count badhao"""
    await daily_stats.update_one(
        {"date": date_str},
        {"$inc": {"links_generated": 1}},
        upsert=True
    )

async def increment_verify(date_str):
    """Links verify hone ka count badhao"""
    await daily_stats.update_one(
        {"date": date_str},
        {"$inc": {"links_verified": 1}},
        upsert=True
    )

async def get_stats_by_date(date_str):
    """Kisi specific date ka data uthao"""
    return await daily_stats.find_one({"date": date_str})