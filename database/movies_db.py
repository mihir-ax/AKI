from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME
import asyncio
import re

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
movies = db.movies

# --- 1. PROPER INDEXES (DeepSeek Fix #1) ---
async def create_indexes():
    # Yeh Text Index sach me search ko 1000x fast karega (Relevance Score ke saath)
    await movies.create_index([("file_name", "text"), ("caption_name", "text")])
    await movies.create_index([("_id", -1)])
    await movies.create_index([("file_name", 1)])
    print("✅ MongoDB Optimized Indexes Created!")

async def add_movie(file_id, file_name, file_size, chat_id, message_id, caption_name):
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

# 🧠 METADATA EXTRACTOR (DeepSeek Fix #2: Bina title ko tode data nikalna)
def extract_metadata(query):
    query = query.lower()
    meta = {'season': None, 'episode': None, 'qualities': [], 'clean_query': query}
    
    # Extract Season (S01, Season 1)
    s_match = re.search(r'\b(?:s|season)[\s\._\-]*0?(\d+)\b', query)
    if s_match:
        meta['season'] = fr'\b(?:s|season)[\s\._\-]*0?{s_match.group(1)}\b'
        
    # Extract Episode (E05, Ep 5)
    e_match = re.search(r'\b(?:e|ep|episode)[\s\._\-]*0?(\d+)\b', query)
    if e_match:
        meta['episode'] = fr'\b(?:e|ep|episode)[\s\._\-]*0?{e_match.group(1)}\b'
        
    # Extract Qualities
    qs = ['hevc', 'hdtc', 'hdcam', 'hdrip', 'webrip', 'web-dl', 'bluray', '1080p', '720p', '480p', '2160p', '4k', 'hindi', 'dual']
    for q in qs:
        if re.search(fr'\b{q}\b', query):
            meta['qualities'].append(fr'\b{q}\b')

    # DeepSeek Bug Fix: Hum "2001" jaise words ko query se delete nahi kar rahe, 
    # bas special characters hata rahe hain taaki title safe rahe.
    clean_title = re.sub(r'[@_+\-.,:;()\[\]{}!?]', ' ', query)
    meta['clean_query'] = re.sub(r'\s+', ' ', clean_title).strip()
    
    return meta


# 🚀 ULTRA-FAST ONE SHOT SEARCH (DeepSeek Fix #3)
async def search_movies(query_str, skip=0, limit=10):
    meta = extract_metadata(query_str)
    
    # 🔄 DYNAMIC SORTING
    is_series = bool(meta['season'] or meta['episode'])
    # Agar series hai toh A-Z sort, nahi toh Newest First (-1)
    sort_order = [("file_name", 1)] if is_series else [("_id", -1)]

    # ==========================================
    # PHASE 1: MONGODB NATIVE TEXT SEARCH (Super Fast)
    # ==========================================
    # Text search sabse fast hota hai. Pehle hum exactly match dhoondhenge.
    text_query = {"$text": {"$search": f'"{meta["clean_query"]}"'}}
    
    total_text_matches = await movies.count_documents(text_query)
    
    if total_text_matches > 0:
        cursor = movies.find(text_query, {
            "score": {"$meta": "textScore"}, # DeepSeek Fix: Relevance Scoring
            "caption_name": 1, "file_name": 1, "file_size": 1, 
            "_id": 1, "chat_id": 1, "message_id": 1
        }).sort([("score", {"$meta": "textScore"})] + sort_order).skip(skip).limit(limit)
        
        results = await cursor.to_list(length=limit)
        return results, total_text_matches

    # ==========================================
    # PHASE 2: SMART FALLBACK (Weighted Regex)
    # Agar Text Search fail ho jaye, tabhi Regex chalega
    # Aur 5 query ki jagah ab sirf 1 Query me kaam hoga!
    # ==========================================
    
    # Words ko alag karo
    words = meta['clean_query'].split()
    if not words:
        return [], 0

    # Saare words ke liye condition banao
    word_conditions = [{"$or": [
        {"file_name": {"$regex": re.escape(w), "$options": "i"}},
        {"caption_name": {"$regex": re.escape(w), "$options": "i"}}
    ]} for w in words]

    # Combine all logic into ONE SINGLE QUERY using $and
    mongo_query = {"$and": word_conditions}

    total = await movies.count_documents(mongo_query)
    
    if total > 0:
        cursor = movies.find(mongo_query, {
            "caption_name": 1, "file_name": 1, "file_size": 1, 
            "_id": 1, "chat_id": 1, "message_id": 1
        }).sort(sort_order).skip(skip).limit(limit)
        
        results = await cursor.to_list(length=limit)
        return results, total

    # Agar kuch nahi mila toh 0 return karo
    return [], 0

async def get_total_movies():
    return await movies.count_documents({})
