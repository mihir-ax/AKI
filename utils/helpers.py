import asyncio
import re
from config import AUTO_DELETE_TIME, FSUB_CHANNEL, FSUB_LINK, GROQ_API_KEY
from pyrogram.errors import UserNotParticipant
from groq import Groq

groq_client = Groq(api_key=GROQ_API_KEY)

def get_readable_size(size_bytes):
    """Convert bytes to a human-readable string."""
    if size_bytes < 1024: return f"{size_bytes} B"
    elif size_bytes < 1048576: return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1073741824: return f"{size_bytes/1048576:.2f} MB"
    else: return f"{size_bytes/1073741824:.2f} GB"

async def auto_delete_message(message, delay=AUTO_DELETE_TIME):
    """Wait for a delay and then delete the given message."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        # Message might already be deleted by user
        print(f"Auto-delete failed: {e}")

async def is_subscribed(client, user_id):
    from config import ADMINS, FSUB_CHANNEL
    
    # 1. Admin hai toh skip karo (Bhai ko toh allow hai!)
    if user_id in ADMINS: return True
    
    # 2. Agar F-Sub band hai toh allow karo
    if not FSUB_CHANNEL: return True
    
    try:
        # Check user status in channel
        member = await client.get_chat_member(FSUB_CHANNEL, user_id)
        # Status "kicked" ya "left" nahi hona chahiye
        if member.status in ["member", "administrator", "creator"]:
            return True
        else:
            return False
    except Exception as e:
        # Agar bot channel mein admin nahi hai ya channel ID galat hai
        print(f"F-Sub Error: {e}")
        return False # Error aaye toh access block karo, allow nahi!

async def check_fsub_on_demand(client, user_id):
    """
    Sirf file bhejte time check karne ke liye
    """
    from config import ADMINS, FSUB_CHANNEL, FSUB_ENABLED
    
    # 1. Admin hai toh allow
    if user_id in ADMINS:
        return True, None, None
    
    # 2. Agar F-Sub DISABLED hai toh allow
    if not FSUB_ENABLED:
        return True, None, None
    
    # 3. Agar channel set nahi hai toh allow
    if not FSUB_CHANNEL:
        return True, None, None
    
    try:
        # Check user status in channel
        member = await client.get_chat_member(FSUB_CHANNEL, user_id)
        # Status "kicked" ya "left" nahi hona chahiye
        if member.status in ["member", "administrator", "creator"]:
            return True, None, None
        else:
            # Not joined, error message with DYNAMIC join button
            fsub_link = generate_fsub_link(FSUB_CHANNEL)
            error_msg = "❌ **Channel Join Required!**\n\n📢 **Join the channel first to download the file.**"
            return False, error_msg, fsub_link
    except Exception as e:
        print(f"F-Sub Check Error: {e}")
        return False, "❌ **Error while checking channel access!**", None

async def get_ai_correction(query):
    from config import GROQ_MODEL, GROQ_SYSTEM_PROMPT
    
    try:
        # System Message: Isme instructions hain
        # User Message: Isme sirf query hai
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system", 
                    "content": GROQ_SYSTEM_PROMPT
                },
                {
                    "role": "user", 
                    "content": f"Correct this movie title: '{query}'"
                }
            ],
            temperature=0.2, # Kam temperature matlab AI zyada "Focused" rahega
            max_tokens=50    # Hume sirf 1-2 words chahiye, toh tokens bacha lo
        )
        
        corrected_name = completion.choices[0].message.content.strip()
        
        # Check karo ki kya AI ne sach mein kuch change kiya hai?
        if corrected_name.lower() != query.lower():
            return corrected_name
        return None
        
    except Exception as e:
        print(f"Groq AI Error: {e}")
        return None

def clean_file_name(file_name):
    # 1. [ ] ke andar ka sab kuch hatao
    file_name = re.sub(r"\[.*?\]", "", file_name)
    
    # 2. @ usernames hatao
    file_name = re.sub(r"@[^\s_]+", "", file_name)
    
    # 3. Underscore (_) ko space mein badlo
    file_name = file_name.replace("_", " ")
    
    # 4. DOT LOGIC: Agar dot ke baad alphabet hai toh dot hata ke space do
    # Agar dot ke baad number hai (e.g. 1.2, .5) toh usko mat chhedo
    file_name = re.sub(r"\.([a-zA-Z])", r" \1", file_name)
    
    # 5. Double spaces saaf karo
    file_name = re.sub(r"\s+", " ", file_name).strip()
    
    return file_name

def is_valid_text(text):
    # 1. Check for Links or Usernames
    if re.search(r"(https?://|t\.me|telegram\.me|@)", text):
        return False
    
    # 2. [NEW] Bot ke apne phrases block karo taaki loop na bane
    bot_phrases = ["No results found", "Search Results", "Show results for", "Try different keywords"]
    if any(phrase.lower() in text.lower() for phrase in bot_phrases):
        return False
    
    # 2. Hindi, English, Numbers aur Emojis allow karne ke liye
    # Hindi Range: \u0900-\u097F
    # Emoji Range: \U00010000-\U0010ffff
    allowed_pattern = r'^[a-zA-Z0-9\s\u0900-\u097F\U00010000-\U0010ffff.,!?-]+$'
    if not re.match(allowed_pattern, text):
        return False
        
    return True

async def auto_delete_messages(messages, delay):
    """Multiple messages ko ek saath delete karne ke liye"""
    await asyncio.sleep(delay)
    for msg in messages:
        try:
            await msg.delete()
        except:
            pass

def generate_fsub_link(channel_username):
    """
    Dynamic channel join link generate karta hai
    """
    if channel_username.startswith("@"):
        # Public channel hai
        return f"https://t.me/{channel_username[1:]}"
    elif str(channel_username).startswith("-100"):
        # Private channel hai
        return f"https://t.me/c/{channel_username[4:]}"
    else:
        # Pehle se hi full link hai
        return channel_username
