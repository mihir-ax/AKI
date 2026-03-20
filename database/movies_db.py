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
            "caption_name": caption_name
        }},
        upsert=True
    )

# 🧠 SMART PARSER: Components ko alag alag dictionary mein todega
def parse_smart_query(query):
    query = query.lower()
    components = {
        'year': None,
        'season': None,
        'episode': None,
        'qualities': [],
        'title': []
    }
    
    # 1. YEAR Extract
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
    if year_match:
        components['year'] = fr'\b{year_match.group(1)}\b'
        query = re.sub(r'\b' + year_match.group(1) + r'\b', '', query)
        
    # 2. SEASON Extract
    season_match = re.search(r'\b(?:s|season)[\s\._\-]*0?(\d+)\b', query)
    if season_match:
        s_num = season_match.group(1)
        components['season'] = fr'\b(?:s|season)[\s\._\-]*0?{s_num}\b'
        query = re.sub(r'\b(?:s|season)[\s\._\-]*0?\d+\b', '', query)
        
    # 3. EPISODE Extract
    ep_match = re.search(r'\b(?:e|ep|episode)[\s\._\-]*0?(\d+)\b', query)
    if ep_match:
        e_num = ep_match.group(1)
        components['episode'] = fr'\b(?:e|ep|episode)[\s\._\-]*0?{e_num}\b'
        query = re.sub(r'\b(?:e|ep|episode)[\s\._\-]*0?\d+\b', '', query)
        
    # 4. QUALITY & FORMAT Extract
    qualities = ['hevc', 'hdtc', 'hdcam', 'hdrip', 'webrip', 'web-dl', 'bluray', '1080p', '720p', '480p', '2160p', '4k', 'hindi', 'english', 'dual']
    for q in qualities:
        if re.search(fr'\b{re.escape(q)}\b', query):
            components['qualities'].append(fr'\b{re.escape(q)}\b')
            query = re.sub(fr'\b{re.escape(q)}\b', '', query)
            
    # 5. TITLE Extract (Bacha hua text)
    for word in query.split():
        if word.strip():
            components['title'].append(re.escape(word.strip()))
            
    return components


async def search_movies(query_str, skip=0, limit=10):
    comps = parse_smart_query(query_str)
    
    # 🔄 DYNAMIC SORTING: 
    # Agar query mein Season ya Episode hai, toh A-Z sort karega (S01E01, S01E02 laane ke liye)
    # Agar Movie hai, toh Newest First (-1)
    is_series = bool(comps['season'] or comps['episode'])
    sort_order = [("file_name", 1)] if is_series else [("_id", -1)]

    # 🛡️ SMART FALLBACK LEVELS (Highest strictness to lowest)
    fallback_levels = [
        ['title', 'year', 'season', 'episode', 'qualities'], # 1. Sab kuch exactly match karo
        ['title', 'year', 'season', 'episode'],              # 2. Quality/Language nahi mili, toh use hatao
        ['title', 'year', 'season'],                         # 3. Exact Episode nahi mila, toh poora Season dikhao
        ['title', 'year'],                                   # 4. Season bhi nahi mila, toh saal + title dekho
        ['title']                                            # 5. Kuch match nahi kiya, toh bas naam se search karo
    ]

    for level in fallback_levels:
        regex_queries = []
        
        for key in level:
            if key == 'qualities' and comps['qualities']:
                for q in comps['qualities']:
                    regex_queries.append({"$or": [{"file_name": {"$regex": q, "$options": "i"}}, {"caption_name": {"$regex": q, "$options": "i"}}]})
            elif key == 'title' and comps['title']:
                for t in comps['title']:
                    regex_queries.append({"$or": [{"file_name": {"$regex": t, "$options": "i"}}, {"caption_name": {"$regex": t, "$options": "i"}}]})
            elif comps.get(key):
                val = comps[key]
                regex_queries.append({"$or": [{"file_name": {"$regex": val, "$options": "i"}}, {"caption_name": {"$regex": val, "$options": "i"}}]})
        
        if not regex_queries:
            continue # Agar sirf empty list hai toh skip kardo
            
        mongo_query = {"$and": regex_queries}
        
        # Check karte hain is level par result mila ya nahi
        total = await movies.count_documents(mongo_query)
        
        if total > 0:
            # Result mil gaya! Data fetch karo aur return kardo
            cursor = movies.find(mongo_query, {
                "caption_name": 1, 
                "file_name": 1, 
                "file_size": 1, 
                "_id": 1, 
                "chat_id": 1, 
                "message_id": 1
            }).sort(sort_order).skip(skip).limit(limit)
            
            results = await cursor.to_list(length=limit)
            return results, total
            
    # Agar 5 levels ke baad bhi kuch na mile, toh 0 return karo
    return [], 0

async def get_total_movies():
    return await movies.count_documents({})
