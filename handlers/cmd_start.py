from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import get_user, update_validation, is_validated
from database.movies_db import movies
from utils.shortener import shorten_url
from utils.helpers import get_readable_size, auto_delete_message, clean_file_name, check_fsub_on_demand
from config import CUSTOM_CAPTION, FSUB_LINK
from bson.objectid import ObjectId
from database.stats_db import increment_gen, increment_verify
from datetime import datetime
import uuid
import asyncio

# Dictionary for pending validations (Can be moved to Redis later)
pending_validations = {}

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.split()
    
    # --- 🛡️ 1. VERIFICATION RETURN HANDLER ---
    if len(text) > 1 and text[1].startswith("verify_"):
        token = text[1].split("_")[1]
        
        if token in pending_validations:
            # 📊 Update verification stats
            today = datetime.now().strftime("%Y-%m-%d")
            await increment_verify(today)
            
            # ✅ Update user validation status
            await update_validation(user_id)
            file_info = pending_validations.pop(token)
            
            # 🎉 Success message
            await message.reply_text(
                "**✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞𝐝!**\n\n"
                "**🤖 𝐇𝐮𝐦𝐚𝐧 𝐂𝐨𝐧𝐟𝐢𝐫𝐦𝐞𝐝** — You have successfully verified.\n\n"
                "**⏳ 𝐕𝐚𝐥𝐢𝐝𝐢𝐭𝐲:** Next 6 hours\n"
                "**🎯 𝐒𝐭𝐚𝐭𝐮𝐬:** Ready for file requests"
            )
            
            # 📦 Send the pending file
            movie = await movies.find_one({"_id": ObjectId(file_info["movie_id"])})
            if movie:
                clean_name = clean_file_name(movie['file_name'])
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
                await message.reply_text("❌ **File Not Found!**\n\nThe requested file is no longer available.")
            return
        else:
            return await message.reply_text("⚠️ **Expired Token!**\n\nThis verification link has expired or is invalid.")

    # --- 📂 2. FILE DEEP LINK HANDLER (From Clickable Filenames) ---
    if len(text) > 1 and text[1].startswith("file_"):
        movie_id = text[1].split("_")[1]
        
        # 🛡️ First: Force Subscribe Check
        is_joined, error_msg = await check_fsub_on_demand(client, user_id)
        
        if not is_joined:
            return await message.reply_text(
                f"**📣 Channel Membership Required!**\n\n{error_msg}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎯 𝐉𝐎𝐈𝐍 𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url=FSUB_LINK)
                ]])
            )
        
        # 🔐 Second: Validation Check (6 hours rule)
        if await is_validated(user_id):
            movie = await movies.find_one({"_id": ObjectId(movie_id)})
            if not movie:
                return await message.reply_text("❌ **File Not Found!**\n\nThis file has been removed from our database.")
            
            clean_name = clean_file_name(movie['file_name'])
            caption = CUSTOM_CAPTION.format(
                filename=clean_name,
                filesize=get_readable_size(movie["file_size"])
            )
            
            await message.reply_text("📤 **Sending File...**")
            sent_file = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=movie["chat_id"],
                message_id=movie["message_id"],
                caption=caption
            )
            asyncio.create_task(auto_delete_message(sent_file))
        else:
            # 🔗 Generate Verification Link
            bot_info = await client.get_me()
            v_link = generate_verify_link(bot_info.username, movie_id)
            
            await message.reply_text(
                "**🛡️ Human Verification Required**\n\n"
                "**🔒 To proceed with file download, please verify that you are not a robot.**\n\n"
                "**⏳ Verification Valid:** 6 Hours\n\n"
                "**👉 Click below to verify:**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 𝐕𝐄𝐑𝐈𝐅𝐘 𝐍𝐎𝐖", url=v_link)]])
            )
        return

    # --- 👋 3. NORMAL START MESSAGE ---
    await get_user(user_id)
    welcome_text = (
        f"**👋 Welcome, {message.from_user.first_name}!**\n\n"
        f"**🎬 Movie Delivery Bot**\n"
        f"**🔍 Start Searching:** Simply type any movie/series name\n\n"
        f"**✨ Features:**\n"
        f"• Instant file delivery\n"
        f"• Advanced filters\n"
        f"• Smart search suggestions\n"
        f"• Secure verification system"
    )
    
    await message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 𝐁𝐎𝐓 𝐒𝐓𝐀𝐓𝐒", callback_data="stats_btn"),
            InlineKeyboardButton("ℹ️ 𝐇𝐄𝐋𝐏", callback_data="help_btn")
        ]])
    )

@Client.on_callback_query(filters.regex("stats_btn"))
async def stats_btn_handler(client, callback):
    from database.movies_db import get_total_movies
    total = await get_total_movies()
    await callback.answer(
        f"📊 Bot Statistics\n\n"
        f"• Total Files: {total:,}\n"
        f"• Active Users: Growing daily!\n"
        f"• Uptime: 99.9%\n\n"
        f"Database updated regularly!",
        show_alert=True
    )

@Client.on_callback_query(filters.regex("help_btn"))
async def help_btn_handler(client, callback):
    help_text = (
        "**📖 Bot Help Guide**\n\n"
        "**🔍 How to Search:**\n"
        "• Just type any movie/series name\n"
        "• Use filters for better results\n\n"
        "**🎯 Available Filters:**\n"
        "• Language 🌐\n"
        "• Quality 🎞️\n"
        "• Year 📅\n"
        "• Season/Episode 📺\n\n"
        "**🛡️ Verification:**\n"
        "• Required every 6 hours\n"
        "• Protects against bots\n\n"
        "**❓ Need More Help?**\n"
        "Contact support if you face issues."
    )
    await callback.message.edit_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 𝐁𝐀𝐂𝐊", callback_data="back_to_start")
        ]])
    )

@Client.on_callback_query(filters.regex("back_to_start"))
async def back_to_start_handler(client, callback):
    welcome_text = (
        f"**👋 Welcome back, {callback.from_user.first_name}!**\n\n"
        f"**🎬 Ready to search?**\n"
        f"Just type any movie/series name to begin!"
    )
    await callback.message.edit_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("ℹ️ 𝐇𝐄𝐋𝐏", callback_data="help_btn")
        ]])
    )

def generate_verify_link(bot_username, movie_id):
    """Generate secure verification link"""
    token = str(uuid.uuid4())[:8]
    pending_validations[token] = {"movie_id": movie_id}
    
    # 📊 Update generation stats (async)
    today = datetime.now().strftime("%Y-%m-%d")
    asyncio.create_task(increment_gen(today))
    
    # 🔗 Create short URL
    original_url = f"https://t.me/{bot_username}?start=verify_{token}"
    short_url = shorten_url(original_url)
    return short_url or original_url