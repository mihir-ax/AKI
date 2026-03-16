from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME, SHORTENER_API_URL, SHORTENER_API_KEY

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
settings_col = db.settings

async def get_settings():
    settings = await settings_col.find_one({"_id": "bot_settings"})
    if not settings:
        settings = {
            "_id": "bot_settings",
            "shortener_url": SHORTENER_API_URL,
            "shortener_api": SHORTENER_API_KEY,
            "pm_search": True,
            "auto_delete": True,
            "delete_banned": True
        }
        await settings_col.insert_one(settings)
    return settings

async def update_setting(key, value):
    await settings_col.update_one(
        {"_id": "bot_settings"},
        {"$set": {key: value}},
        upsert=True
    )
