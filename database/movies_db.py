from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME
import asyncio
import re

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
movies = db.movies

# --- 1. OPTIMIZED INDEXES ---
async def create_indexes():
    try:
        # Puraane conflicting indexes ko delete karega
        await movies.drop_indexes()
    except Exception as e:
        pass # Koi error aaye toh ignore karo
        
    # Ab naya SuperFast Text Index properly create hoga
    await movies.create_index([("file_name", "text"), ("caption_name", "text")])
    print("✅ MongoDB Indexes Initialized Successfully!")

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

# 🧠 TELEGRAM-STYLE METADATA EXTRACTOR
def extract_smart_metadata(query):
    query = query.lower()
    
    clean_query = re.sub(r'[\.\_\-\[\]\(\)\@\{\}\:\,\!]', ' ', query)
    clean_query = re.sub(r'\s+', ' ', clean_query).strip()

    meta = {'season': None, 'episode': None, 'qualities': [], 'title_words': []}
    
    s_match = re.search(r'\b(?:s|season)\s*0?(\d+)\b', clean_query)
    if s_match:
        meta['season'] = s_match.group(1)
        clean_query = re.sub(r'\b(?:s|season)\s*0?\d+\b', '', clean_query)
        
    e_match = re.search(r'\b(?:e|ep|episode)\s*0?(\d+)\b', clean_query)
    if e_match:
        meta['episode'] = e_match.group(1)
        clean_query = re.sub(r'\b(?:e|ep|episode)\s*0?\d+\b', '', clean_query)
        
    qs = ['hevc', 'hdtc', 'hdcam', 'hdrip', 'webrip', 'web-dl', 'bluray', '1080p', '720p', '480p', '2160p', '4k', 'hindi', 'dual']
    for q in qs:
        if re.search(fr'\b{q}\b', clean_query):
            meta['qualities'].append(q)
            clean_query = re.sub(fr'\b{q}\b', '', clean_query)

    meta['title_words'] = [w for w in clean_query.split() if w.strip()]
    
    return meta

# 🚀 HYBRID SEARCH ENGINE (Text + Regex Fallback)
async def search_movies(query_str, skip=0, limit=10):
    meta = extract_smart_metadata(query_str)
    
    is_series = bool(meta['season'] or meta['episode'])
    sort_order = [("file_name", 1)] if is_series else [("_id", -1)]

    # PHASE 1: MONGODB TEXT SEARCH
    all_words = meta['title_words'] + meta['qualities']
    if meta['season']: all_words.append(f"s{meta['season']:0>2}")
    if meta['episode']: all_words.append(f"e{meta['episode']:0>2}")

    if all_words:
        text_search_str = " ".join([f'"{w}"' for w in all_words])
        text_query = {"$text": {"$search": text_search_str}}
        
        total_text = await movies.count_documents(text_query)
        if total_text > 0:
            cursor = movies.find(text_query, {
                "score": {"$meta": "textScore"}, 
                "caption_name": 1, "file_name": 1, "file_size": 1, 
                "_id": 1, "chat_id": 1, "message_id": 1
            }).sort([("score", {"$meta": "textScore"})] + sort_order).skip(skip).limit(limit)
            return await cursor.to_list(length=limit), total_text

    # PHASE 2: TELEGRAM REALITY FALLBACK (Regex)
    fallback_levels = [
        {'q': meta['qualities'], 's': meta['season'], 'e': meta['episode']}, 
        {'q': [], 's': meta['season'], 'e': meta['episode']},                
        {'q': [], 's': meta['season'], 'e': None},                           
        {'q': [], 's': None, 'e': None}                                      
    ]

    for level in fallback_levels:
        regex_conditions = []
        
        for w in meta['title_words']:
            regex_conditions.append({
                "$or": [
                    {"file_name": {"$regex": re.escape(w), "$options": "i"}},
                    {"caption_name": {"$regex": re.escape(w), "$options": "i"}}
                ]
            })
            
        if level['s']:
            s_pat = fr"(s|season)[\s\.\_\-\[\]]*0?{level['s']}"
            regex_conditions.append({"$or": [{"file_name": {"$regex": s_pat, "$options": "i"}}, {"caption_name": {"$regex": s_pat, "$options": "i"}}]})
        if level['e']:
            e_pat = fr"(e|ep|episode)[\s\.\_\-\[\]]*0?{level['e']}"
            regex_conditions.append({"$or": [{"file_name": {"$regex": e_pat, "$options": "i"}}, {"caption_name": {"$regex": e_pat, "$options": "i"}}]})
            
        for q in level['q']:
            regex_conditions.append({"$or": [{"file_name": {"$regex": re.escape(q), "$options": "i"}}, {"caption_name": {"$regex": re.escape(q), "$options": "i"}}]})
            
        if not regex_conditions:
            continue
            
        mongo_query = {"$and": regex_conditions}
        total = await movies.count_documents(mongo_query)
        
        if total > 0:
            cursor = movies.find(mongo_query, {
                "caption_name": 1, "file_name": 1, "file_size": 1, 
                "_id": 1, "chat_id": 1, "message_id": 1
            }).sort(sort_order).skip(skip).limit(limit)
            return await cursor.to_list(length=limit), total

    return [], 0

async def get_total_movies():
    return await movies.count_documents({})
