# --- database/movies_db.py ---
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME
import asyncio
import re

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
movies = db.movies

# --- 1. SEARCH FAST KARNE KE LIYE INDEXES ---
async def create_indexes():
    # Yeh line search ko 1000 guna fast bana degi
    await movies.create_index([("file_name", "text")])
    await movies.create_index([("file_name", 1)])
    # print("✅ MongoDB Indexes Created!")

async def add_movie(file_id, file_name, file_size, chat_id, message_id, caption_name):
    """Movie save karte waqt caption_name (clean name) bhi save karenge"""
    await movies.update_one(
        {"file_name": file_name},
        {"$set": {
            "file_id": file_id,
            "file_size": file_size,
            "chat_id": chat_id,
            "message_id": message_id,
            "caption_name": caption_name # Yeh raha hamara 'Secret' field
        }},
        upsert=True
    )

async def search_movies(query, skip=0, limit=10):
    keywords = query.split()
    # Hum keywords ko search karenge (Case-insensitive)
    regex_queries = []
    for kw in keywords:
        clean_kw = re.escape(kw)
        # Search dono fields mein karega (file_name ya caption_name)
        # Isse filters (720p, Hindi) aur fast kaam karenge
        regex_queries.append({
            "$or": [
                {"file_name": {"$regex": clean_kw, "$options": "i"}},
                {"caption_name": {"$regex": clean_kw, "$options": "i"}}
            ]
        })
    
    mongo_query = {"$and": regex_queries} if regex_queries else {}
    
    # Projection: Sirf wahi data mangao jo display karna hai (Speed badhegi)
    cursor = movies.find(mongo_query, {
        "caption_name": 1, 
        "file_name": 1, 
        "file_size": 1, 
        "_id": 1, 
        "chat_id": 1, 
        "message_id": 1
    }).skip(skip).limit(limit)
    
    # Results aur Total Count ek saath mangwao
    results, total = await asyncio.gather(
        cursor.to_list(length=limit),
        movies.count_documents(mongo_query)
    )
    
    return results, total

async def get_total_movies():
    return await movies.count_documents({})