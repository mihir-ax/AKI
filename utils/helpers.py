import asyncio
import re
from config import AUTO_DELETE_TIME, GROQ_API_KEY
from pyrogram.enums import ChatMemberStatus
from groq import Groq

groq_client = Groq(api_key=GROQ_API_KEY)

def get_readable_size(size_bytes):
    if size_bytes < 1024: return f"{size_bytes} B"
    elif size_bytes < 1048576: return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1073741824: return f"{size_bytes/1048576:.2f} MB"
    else: return f"{size_bytes/1073741824:.2f} GB"

async def auto_delete_message(client, chat_id, message, delay=AUTO_DELETE_TIME):
    await asyncio.sleep(delay)
    try:
        msg_id = message.id if hasattr(message, 'id') else message
        await client.delete_messages(chat_id, [msg_id])
    except: pass

async def auto_delete_messages(client, chat_id, messages, delay=AUTO_DELETE_TIME):
    await asyncio.sleep(delay)
    for msg in messages:
        if msg is None: continue
        try:
            # Handle both Pyrogram Message objects and MessageId objects safely
            msg_id = msg.id if hasattr(msg, 'id') else msg
            await client.delete_messages(chat_id, [msg_id])
        except Exception:
            pass  # Agar user ka msg delete karne ki admin permission nahi hogi, toh error aayega par baaki msg delete ho jayenge

async def is_subscribed(client, user_id):
    from config import ADMINS, FSUB_CHANNEL
    if user_id in ADMINS: return True
    if not FSUB_CHANNEL: return True

    try:
        member = await client.get_chat_member(FSUB_CHANNEL, user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
        return False
    except:
        return False

async def check_fsub_on_demand(client, user_id):
    """
    New Force Join Logic: Creates a fresh invite link if the user hasn't joined.
    Automatically handles string/integer channel IDs and proper fallbacks.
    """
    from config import ADMINS, FSUB_CHANNEL, FSUB_ENABLED, FSUB_LINK
    from pyrogram.enums import ChatMemberStatus

    if user_id in ADMINS: return True, None, None
    if not FSUB_ENABLED or not FSUB_CHANNEL: return True, None, None

    chat_id = FSUB_CHANNEL
    if isinstance(chat_id, str):
        chat_id = chat_id.strip()
        if chat_id.lstrip('-').isdigit():
            chat_id = int(chat_id)

    try:
        member = await client.get_chat_member(chat_id, user_id)

        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True, None, None

        raise Exception("User not joined")

    except Exception as e:
        fsub_link = None

        try:
            link_obj = await client.create_chat_invite_link(chat_id=chat_id)
            fsub_link = link_obj.invite_link
        except Exception as e2:
            print(f"⚠️ Failed to create invite link: {e2}")

            if FSUB_LINK and FSUB_LINK.strip().startswith("http"):
                fsub_link = FSUB_LINK.strip()

            elif isinstance(chat_id, str) and chat_id.startswith("@"):
                fsub_link = f"https://t.me/{chat_id.replace('@', '')}"

            else:
                fsub_link = "https://t.me/telegram"

        error_msg = "❌ **Channel Join Required!**\n\n📢 **Join the channel first to download the file. After joining, click the file button again!**"

        return False, error_msg, fsub_link

async def get_ai_correction(query):
    from config import GROQ_MODEL, GROQ_SYSTEM_PROMPT
    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": GROQ_SYSTEM_PROMPT}, {"role": "user", "content": f"Correct this movie title: '{query}'"}],
            temperature=0.2, max_tokens=50
        )
        corrected_name = completion.choices[0].message.content.strip()
        if corrected_name.lower() != query.lower(): return corrected_name
        return None
    except: return None

def clean_file_name(file_name):
    file_name = re.sub(r"\[.*?\]", "", file_name)
    file_name = re.sub(r"@[^\s_]+", "", file_name)
    file_name = file_name.replace("_", " ")
    file_name = re.sub(r"\.([a-zA-Z])", r" \1", file_name)
    file_name = re.sub(r"\s+", " ", file_name).strip()
    return file_name

def is_valid_text(text):
    if re.search(r"(https?://|t\.me|telegram\.me|@)", text): return False
    bot_phrases = ["No results found", "Search Results", "Show results for", "Try different keywords"]
    if any(phrase.lower() in text.lower() for phrase in bot_phrases): return False
    allowed_pattern = r'^[a-zA-Z0-9\s\u0900-\u097F\U00010000-\U0010ffff.,!?-]+$'
    if not re.match(allowed_pattern, text): return False
    return True
