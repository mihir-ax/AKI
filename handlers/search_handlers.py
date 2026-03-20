from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.movies_db import movies, search_movies
from database.users_db import get_user, is_validated
from database.settings_db import get_settings
from utils.helpers import get_readable_size, clean_file_name, is_valid_text, auto_delete_message, auto_delete_messages, check_fsub_on_demand, get_ai_correction
from config import RESULT_MODE, LANGUAGES, QUALITIES, YEARS, SEASONS, EPISODES
from config import CUSTOM_CAPTION, SEPARATE_NOTE, RESULT_DELETE_TIME
from bson.objectid import ObjectId
from pyrogram.enums import ParseMode, ChatType
from handlers.cmd_start import generate_verify_link
import asyncio
import urllib.parse
import re # <-- New import for query cleaning

# 🛠️ HELPER FUNCTION: To make search Solid
def clean_search_query(query):
    """Faltu special characters aur extra spaces hatane ke liye"""
    query = query.lower().strip()
    query = re.sub(r"[@_+\-.,:;()\[\]{}!?]", " ", query) # Remove special chars
    query = re.sub(r"\s+", " ", query).strip() # Remove extra spaces
    return query

@Client.on_message(filters.text & (filters.private | filters.group) & ~filters.bot & ~filters.command(["start", "index", "stats", "ban", "unban", "settings", "fsub", "id"]))
async def main_search_handler(client: Client, message: Message):
    chat_type = message.chat.type
    settings = await get_settings()

    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        is_banned_content = False
        if getattr(message, "forward_date", None) or getattr(message, "forward_origin", None):
            is_banned_content = True
        elif message.sender_chat:
            is_banned_content = True
        elif not is_valid_text(message.text):
            is_banned_content = True

        if is_banned_content:
            if settings.get("delete_banned", True):
                try: await message.delete()
                except: pass
            return

    if not message.from_user: return

    user_id = message.from_user.id
    user = await get_user(user_id)

    if user.get("is_banned"):
        return await message.reply_text(f"⛔ **Access Denied!**")

    if chat_type == ChatType.PRIVATE and not settings.get("pm_search", True):
        return await message.reply_text("❌ **PM Search is Disabled!**\n\nPlease join our official group to request and download movies.")

    # 🔍 QUERY CLEANING APPLIED HERE
    raw_query = message.text
    clean_query = clean_search_query(raw_query)
    
    if len(clean_query) < 2:
        return await message.reply_text("⚠️ **Please type at least 2 characters to search!**")

    temp_msg = await message.reply_text(f"🔍 **Searching for:** `{raw_query}`...")

    sent_msg = await show_results(client, message, clean_query, page=0)

    try: await temp_msg.delete()
    except: pass

    if sent_msg:
        msgs_to_delete = [sent_msg]
        if settings.get("auto_delete", True):
            msgs_to_delete.append(message)
        asyncio.create_task(auto_delete_messages(client, message.chat.id, msgs_to_delete, delay=RESULT_DELETE_TIME))


@Client.on_callback_query(filters.regex(r"^get_"))
async def handle_file_button(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = await get_settings()

    is_joined, error_msg, fsub_link = await check_fsub_on_demand(client, user_id)

    if not is_joined:
        movie_id = callback.data.split("_")[1]
        buttons = []
        if fsub_link: buttons.append([InlineKeyboardButton("🎯 𝐉𝐎𝐈𝐍 𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url=fsub_link)])
        buttons.append([InlineKeyboardButton("🔄 𝐂𝐇𝐄𝐂𝐊 𝐀𝐆𝐀𝐈𝐍", callback_data=f"get_{movie_id}")])
        return await callback.message.edit_text(f"📣 **Channel Membership Required!**\n\n{error_msg}", reply_markup=InlineKeyboardMarkup(buttons))

    movie_id = callback.data.split("_")[1]

    if not await is_validated(user_id):
        await callback.answer("🛡️ Verification Required!", show_alert=False)
        bot_info = await client.get_me()
        v_link = await generate_verify_link(bot_info.username, movie_id)
        return await callback.message.reply_text(
            "**🤖 𝐇𝐮𝐦𝐚𝐧 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧 𝐑𝐞𝐪𝐮𝐢𝐫𝐞𝐝**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 𝐕𝐄𝐑𝐈𝐅𝐘 𝐍𝐎𝐖", url=v_link)]])
        )

    movie = await movies.find_one({"_id": ObjectId(movie_id)})
    if not movie: return await callback.answer("❌ 𝐅𝐢𝐥𝐞 𝐍𝐨𝐭 𝐅𝐨𝐮𝐧𝐝!", show_alert=True)

    clean_name = clean_file_name(movie['file_name'])
    caption = CUSTOM_CAPTION.format(filename=clean_name, filesize=get_readable_size(movie["file_size"]))

    await callback.answer("📤 𝐒𝐞𝐧𝐝𝐢𝐧𝐠 𝐅𝐢𝐥𝐞...")

    try:
        sent_file = await client.copy_message(
            chat_id=callback.message.chat.id, from_chat_id=movie["chat_id"],
            message_id=movie["message_id"], caption=caption
        )
        note_msg = await callback.message.reply_text(SEPARATE_NOTE)
        asyncio.create_task(auto_delete_messages(client, callback.message.chat.id, [sent_file, note_msg], delay=RESULT_DELETE_TIME))
    except Exception as e:
        print(f"Error sending file: {e}")
        await callback.message.reply_text("🚨 𝐔𝐩𝐥𝐨𝐚𝐝 𝐄𝐫𝐫𝐨𝐫!")


async def show_results(client, message, query, page=0):
    limit = 10
    skip = page * limit

    results, total = await search_movies(query, skip=skip, limit=limit)
    original_query = query
    ai_correction_used = False

    if not results and page == 0:
        ai_name = await get_ai_correction(query)
        if ai_name and ai_name.lower() != query.lower():
            ai_clean_query = clean_search_query(ai_name) # Clean AI query too
            results, total = await search_movies(ai_clean_query, skip=0, limit=10)
            if results:
                query = ai_clean_query
                ai_correction_used = True
                correction_msg = await message.reply_text(f"💡 **Did you mean:** `{ai_name}`?")
                asyncio.create_task(auto_delete_message(client, message.chat.id, correction_msg, delay=10))

    if not results:
        google_query = urllib.parse.quote(query)
        google_link = f"https://www.google.com/search?q={google_query}"
        not_found_text = f"**🔍 𝐍𝐨 𝐑𝐞𝐬𝐮𝐥𝐭𝐬 𝐅𝐨𝐮𝐧𝐝**\n\n📝 **Searched for:** `{query}`\n\n✨ **Suggestions:**\n• Try different keywords\n• Check spelling\n• Be more specific"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🌐 𝐒𝐞𝐚𝐫𝐜𝐡 𝐨𝐧 𝐆𝐨𝐨𝐠𝐥𝐞", url=google_link)]])

        if isinstance(message, CallbackQuery):
            await message.answer(not_found_text, show_alert=True)
            return None
        else:
            err_msg = await message.reply_text(not_found_text, reply_markup=markup)
            settings = await get_settings()
            msgs_to_delete = [err_msg]
            if settings.get("auto_delete", True):
                msgs_to_delete.append(message)
            asyncio.create_task(auto_delete_messages(client, message.chat.id, msgs_to_delete, delay=120))
            return None

    bot = await client.get_me()
    keyboard = []

    if RESULT_MODE == "CAPTION":
        text = f"<b>📂 𝐒𝐄𝐀𝐑𝐂𝐇 𝐑𝐄𝐒𝐔𝐋𝐓𝐒 ({total} 𝐅𝐢𝐥𝐞𝐬)</b>\n\n"
        if ai_correction_used: text += f"<b>✨ 𝐒𝐡𝐨𝐰𝐢𝐧𝐠 𝐫𝐞𝐬𝐮𝐥𝐭𝐬 𝐟𝐨𝐫:</b> `{query}`\n<b>📝 𝐎𝐫𝐢𝐠𝐢𝐧𝐚𝐥 𝐬𝐞𝐚𝐫𝐜𝐡:</b> `{original_query}`\n\n"
        else: text += f"<b>🔎 𝐒𝐞𝐚𝐫𝐜𝐡 𝐐𝐮𝐞𝐫𝐲:</b> `{query}`\n\n"
        text += "<b>📦 𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐅𝐢𝐥𝐞𝐬:</b>\n\n"

        for i, movie in enumerate(results, 1):
            size = get_readable_size(movie['file_size'])
            clean_name = movie.get('caption_name') or clean_file_name(movie.get('file_name', 'Unknown'))
            link = f"https://t.me/{bot.username}?start=file_{movie['_id']}"
            text += f"{i}. <b><a href='{link}'>📄 {size} | {clean_name}</a></b>\n\n"
    else:
        if ai_correction_used: text = f"<b>🎬 𝐑𝐞𝐬𝐮𝐥𝐭𝐬 𝐟𝐨𝐫:</b> `{query}`\n<b>💡 𝐎𝐫𝐢𝐠𝐢𝐧𝐚𝐥 𝐬𝐞𝐚𝐫𝐜𝐡:</b> `{original_query}`\n\n"
        else: text = f"<b>🎬 𝐒𝐞𝐚𝐫𝐜𝐡 𝐑𝐞𝐬𝐮𝐥𝐭𝐬</b>\n\n<b>🔎 𝐐𝐮𝐞𝐫𝐲:</b> `{query}`\n\n"
        text += "<b>⬇️ 𝐂𝐥𝐢𝐜𝐤 𝐛𝐮𝐭𝐭𝐨𝐧𝐬 𝐛𝐞𝐥𝐨𝐰 𝐭𝐨 𝐠𝐞𝐭 𝐟𝐢𝐥𝐞𝐬 ⬇️</b>"

        for movie in results:
            size = get_readable_size(movie['file_size'])
            clean_name = movie.get('caption_name') or clean_file_name(movie.get('file_name', 'Unknown'))
            keyboard.append([InlineKeyboardButton(f"📁 [{size}] {clean_name}", callback_data=f"get_{movie['_id']}")])

    query_words = query.split()
    # Safely truncate query for Callback Data to prevent 64-Byte Crash
    safe_query = query[:25] 

    if len(query_words) > 1:
        filter_rows = [
            [InlineKeyboardButton("🌐 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄", callback_data=f"list_lang_{safe_query}_{page}")],
            [InlineKeyboardButton("🎞️ 𝐐𝐔𝐀𝐋𝐈𝐓𝐘", callback_data=f"list_qual_{safe_query}_{page}"),
             InlineKeyboardButton("📺 𝐒𝐄𝐀𝐒𝐎𝐍", callback_data=f"list_season_{safe_query}_{page}")],
            [InlineKeyboardButton("📅 𝐘𝐄𝐀𝐑", callback_data=f"list_year_{safe_query}_{page}"),
             InlineKeyboardButton("🎬 𝐄𝐏𝐈𝐒𝐎𝐃𝐄", callback_data=f"list_ep_{safe_query}_{page}")]
        ]
        keyboard.extend(filter_rows)
        original_word = query_words[0][:25]
        keyboard.append([InlineKeyboardButton("🔄 𝐑𝐄𝐒𝐄𝐓 𝐀𝐋𝐋 𝐅𝐈𝐋𝐓𝐄𝐑𝐒", callback_data=f"page_{original_word}_0")])
    else:
        filter_rows = [
            [InlineKeyboardButton("🌐 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄", callback_data=f"list_lang_{safe_query}_{page}"),
            InlineKeyboardButton("🎞️ 𝐐𝐔𝐀𝐋𝐈𝐓𝐘", callback_data=f"list_qual_{safe_query}_{page}")],
            [InlineKeyboardButton("📅 𝐘𝐄𝐀𝐑", callback_data=f"list_year_{safe_query}_{page}"),
            InlineKeyboardButton("📺 𝐒𝐄𝐀𝐒𝐎𝐍 / 𝐄𝐏𝐈𝐒𝐎𝐃𝐄", callback_data=f"list_season_{safe_query}_{page}")]
        ]
        keyboard.extend(filter_rows)

    nav_buttons = []
    if page > 0: nav_buttons.append(InlineKeyboardButton("◀️ 𝐏𝐑𝐄𝐕", callback_data=f"page_{safe_query}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{(total//10)+1}", callback_data="none"))
    if total > (page + 1) * limit: nav_buttons.append(InlineKeyboardButton("𝐍𝐄𝐗𝐓 ▶️", callback_data=f"page_{safe_query}_{page+1}"))
    keyboard.append(nav_buttons)

    final_markup = InlineKeyboardMarkup(keyboard)

    try:
        if isinstance(message, CallbackQuery): return await message.message.edit_text(text, reply_markup=final_markup, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
        else: return await message.reply_text(text, reply_markup=final_markup, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"Error updating UI: {e}")
        return None

@Client.on_callback_query(filters.regex(r"^list_"))
async def show_filter_options(client, callback: CallbackQuery):
    data = callback.data.split("_")
    category, query, page = data[1], data[2], data[3]

    items = []
    category_names = {"lang": "🌐 Language", "qual": "🎞️ Quality", "year": "📅 Year", "season": "📺 Season", "ep": "🎬 Episode"}

    if category == "lang": items = LANGUAGES
    elif category == "qual": items = QUALITIES
    elif category == "year": items = YEARS
    elif category == "season": items = SEASONS
    elif category == "ep": items = EPISODES

    buttons = []
    row = []
    for item in items:
        new_query = f"{query} {item}"
        # Telegram Callback 64-byte limit fix
        cb_data = f"page_{new_query[:30]}_0" 
        row.append(InlineKeyboardButton(item, callback_data=cb_data))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 𝐁𝐀𝐂𝐊", callback_data=f"page_{query}_{page}")])

    await callback.message.edit_text(
        f"**{category_names.get(category, 'Filter')} 🎯**\n\n**Search:** `{query}`\n\n**Select {category_names.get(category, 'option').lower()}:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r"^page_"))
async def handle_pagination(client, callback: CallbackQuery):
    data = callback.data.split("_")
    # Join in case query had underscores
    query = "_".join(data[1:-1]) 
    page = int(data[-1])
    await show_results(client, callback, query, page)
