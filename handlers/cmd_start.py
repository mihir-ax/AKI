from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import get_user, update_validation, is_validated
from database.movies_db import movies
from utils.shortener import shorten_url
from utils.helpers import get_readable_size, auto_delete_message, clean_file_name, check_fsub_on_demand
from config import CUSTOM_CAPTION, FSUB_LINK
from bson.objectid import ObjectId
from database.stats_db import increment_gen # Import karo
from datetime import datetime
import uuid
import asyncio
from database.stats_db import increment_verify

# Dictionary for pending validations (Can be moved to Redis later)
pending_validations = {}

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.split()
    
    # --- 1. HANDLE VERIFICATION RETURN ---
    if len(text) > 1 and text[1].startswith("verify_"):
        token = text[1].split("_")[1]
        if token in pending_validations:
            # Stats update karo
            today = datetime.now().strftime("%Y-%m-%d")
            await increment_verify(today)
            
            await update_validation(user_id)
            file_info = pending_validations.pop(token)
            
            await message.reply_text("✅ **ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ!**\n\n🤖❌ **ʜᴜᴍᴀɴ ᴄᴏɴꜰɪʀᴍᴇᴅ** — **ʏᴏᴜ ᴀʀᴇ ʀᴇᴀʟʟʏ ʜᴜᴍᴀɴ.**\n\n⏳ **ʏᴏᴜ ᴄᴀɴ ʀᴇQᴜᴇꜱᴛ ꜰɪʟᴇꜱ ꜰᴏʀ ᴛʜᴇ ɴᴇxᴛ 6 ʜᴏᴜʀꜱ.**")
            
            # Send the pending file
            movie = await movies.find_one({"_id": ObjectId(file_info["movie_id"])})
            clean_name = clean_file_name(movie['file_name']) # Cleaning yahan bhi laga di
            caption = CUSTOM_CAPTION.format(
                filename=clean_name,
                filesize=get_readable_size(movie["file_size"])
            )
            sent_file = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=movie["chat_id"],
                message_id=movie["message_id"],
                caption=caption
            )
            asyncio.create_task(auto_delete_message(sent_file))
            return
        else:
            return await message.reply_text("❌ __ᴛᴏᴋᴇɴ ᴇxᴘɪʀᴇᴅ!__")

    # --- 2. HANDLE FILE DEEP LINK (From Clickable Filenames) ---
    if len(text) > 1 and text[1].startswith("file_"):
        movie_id = text[1].split("_")[1]
        
        # --- PEHLE F-SUB CHECK ---
        is_joined, error_msg = await check_fsub_on_demand(client, user_id)
        
        if not is_joined:
            return await message.reply_text(
                f"{error_msg}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=FSUB_LINK)
                ]])
            )
        
        # Check if user is already validated (6 hours rule)
        if await is_validated(user_id):
            movie = await movies.find_one({"_id": ObjectId(movie_id)})
            clean_name = clean_file_name(movie['file_name']) # <--- CLEANING HERE
            if not movie: 
                return await message.reply_text("❌ **ꜰɪʟᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ ɪɴ ʀᴇᴄᴏʀᴅꜱ!**")
            
            caption = CUSTOM_CAPTION.format(
                filename=clean_name,
                filesize=get_readable_size(movie["file_size"])
            )
            sent_file = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=movie["chat_id"],
                message_id=movie["message_id"],
                caption=caption
            )
            asyncio.create_task(auto_delete_message(sent_file))
        else:
            # Not validated? Generate Short Link
            bot_info = await client.get_me()
            v_link = generate_verify_link(bot_info.username, movie_id)
            await message.reply_text(
                "**🚀 ᴠᴇʀɪꜰʏ ᴛʜᴀᴛ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ ʀᴏʙᴏᴛ!\n\n**🔐 ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ ᴡɪᴛʜ ᴛʜᴇ ꜰɪʟᴇ ᴅᴏᴡɴʟᴏᴀᴅ, ᴘʟᴇᴀꜱᴇ ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴀɴᴅ ᴠᴇʀɪꜰʏ ᴛʜᴀᴛ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ ʀᴏʙᴏᴛ.**\n\n**⏳ ᴠᴀʟɪᴅɪᴛʏ: 6 ʜᴏᴜʀꜱ**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ ᴠᴇʀɪꜰʏ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ ʀᴏʙᴏᴛ", url=v_link)]])
            )
        return

    # --- 3. NORMAL START MESSAGE (NO F-SUB CHECK HERE) ---
    await get_user(user_id)
    welcome_text = (
        f"""👋 **ʜɪ {message.from_user.first_name}!**

🎬 **ɪ ᴀᴍ ᴀ ᴍᴏᴠɪᴇ ᴅᴇʟɪᴠᴇʀʏ ʙᴏᴛ.**
🔍 **ᴊᴜꜱᴛ ᴛʏᴘᴇ ᴛʜᴇ ᴍᴏᴠɪᴇ ɴᴀᴍᴇ ᴀɴᴅ ꜱᴛᴀʀᴛ ꜱᴇᴀʀᴄʜɪɴɢ!**
"""
    )
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 ꜱᴛᴀᴛꜱ", callback_data="stats_btn")
    ]]))

@Client.on_callback_query(filters.regex("stats_btn"))
async def stats_btn_handler(client, callback):
    from database.movies_db import get_total_movies
    total = await get_total_movies()
    await callback.answer(f"Currently indexing {total} movie files!", show_alert=True)

def generate_verify_link(bot_username, movie_id):
    token = str(uuid.uuid4())[:8]
    pending_validations[token] = {"movie_id": movie_id}
    
    # --- Stats Logic ---
    today = datetime.now().strftime("%Y-%m-d")
    asyncio.create_task(increment_gen(today)) # Async task taaki link slow na ho
    # ------------------

    original_url = f"https://t.me/{bot_username}?start=verify_{token}"
    short_url = shorten_url(original_url)
    return short_url or original_url