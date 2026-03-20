from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME
import asyncio
import re

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
movies = db.movies

# --- 1. SEARCH FAST KARNE KE LIYE INDEXES ---
async def create_indexes():
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


# 🧠 SMART PARSER: User ki query ko samajhne ke liye
def generate_smart_patterns(query):
    query = query.lower()
    patterns = []
    
    # 1. YEAR Extract (Jaise 2023, 2024, 1998)
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
    if year_match:
        year = year_match.group(1)
        patterns.append(fr'\b{year}\b') # Year ka pattern banaya
        query = re.sub(r'\b' + year + r'\b', '', query) # Query se saaf kar diya
        
    # 2. SEASON Extract (S1, S01, Season 1, season01)
    season_match = re.search(r'\b(?:s|season)[\s\._\-]*0?(\d+)\b', query)
    if season_match:
        s_num = season_match.group(1) # S01 se sirf '1' nikalega
        # Aisa pattern banayega jo S1, S01, Season 1 sabko pakdega db mein
        patterns.append(fr'\b(?:s|season)[\s\._\-]*0?{s_num}\b')
        query = re.sub(r'\b(?:s|season)[\s\._\-]*0?\d+\b', '', query)
        
    # 3. EPISODE Extract (E1, E01, Ep 1, Episode 01)
    ep_match = re.search(r'\b(?:e|ep|episode)[\s\._\-]*0?(\d+)\b', query)
    if ep_match:
        e_num = ep_match.group(1)
        patterns.append(fr'\b(?:e|ep|episode)[\s\._\-]*0?{e_num}\b')
        query = re.sub(r'\b(?:e|ep|episode)[\s\._\-]*0?\d+\b', '', query)
        
    # 4. QUALITY & FORMAT Extract (HEVC, 1080p, HDTC etc)
    qualities = ['hevc', 'hdtc', 'hdcam', 'hdrip', 'webrip', 'web-dl', 'bluray', '1080p', '720p', '480p', '2160p', '4k']
    for q in qualities:
        if re.search(fr'\b{re.escape(q)}\b', query):
            patterns.append(fr'\b{re.escape(q)}\b')
            query = re.sub(fr'\b{re.escape(q)}\b', '', query)
            
    # 5. Bachi hui chijein (TITLE - jaise 'Animal', 'Loki')
    for word in query.split():
        if word.strip():
            patterns.append(re.escape(word.strip()))
            
    return patterns


async def search_movies(query, skip=0, limit=10):
    # Ab normal split() nahi, humara Smart Parser kaam karega
    patterns = generate_smart_patterns(query)
    
    regex_queries = []
    for pat in patterns:
        regex_queries.append({
            "$or": [
                {"file_name": {"$regex": pat, "$options": "i"}},
                {"caption_name": {"$regex": pat, "$options": "i"}}
            ]
        })
    
    mongo_query = {"$and": regex_queries} if regex_queries else {}
    
    # 🚀 YAHAN MAINE .sort("_id", -1) LAGA DIYA HAI
    # Isse automatically NEWEST files sabse upar aur 1st page pe aayengi
    cursor = movies.find(mongo_query, {
        "caption_name": 1, 
        "file_name": 1, 
        "file_size": 1, 
        "_id": 1, 
        "chat_id": 1, 
        "message_id": 1
    }).sort("_id", -1).skip(skip).limit(limit) 
    
    # Results aur Total Count ek saath mangwao
    results, total = await asyncio.gather(
        cursor.to_list(length=limit),
        movies.count_documents(mongo_query)
    )
    
    return results, total

async def get_total_movies():
    return await movies.count_documents({})
