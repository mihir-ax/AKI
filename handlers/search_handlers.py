from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.movies_db import movies, search_movies
from database.users_db import get_user, is_validated
from utils.helpers import get_readable_size, auto_delete_message, clean_file_name, is_valid_text, auto_delete_messages, check_fsub_on_demand, get_ai_correction
from config import RESULT_MODE, LANGUAGES, QUALITIES, YEARS, SEASONS, EPISODES
from config import FSUB_LINK, CUSTOM_CAPTION, RESULT_DELETE_TIME
from bson.objectid import ObjectId
from pyrogram.enums import ParseMode, ChatType
from handlers.cmd_start import generate_verify_link  # Import this if it's in cmd_start
import asyncio
import urllib.parse

@Client.on_message(filters.text & (filters.private | filters.group) & ~filters.bot & ~filters.command(["start", "index", "stats", "ban", "unban"]))
async def main_search_handler(client: Client, message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    chat_type = message.chat.type
    if message.from_user and message.from_user.is_bot:
        return

    # 1. 🔒 Ban Check
    if user.get("is_banned"):
        return await message.reply_text(f"⛔ **Access Denied!**\n\n📛 **Reason:** {user.get('ban_reason')}\n\n🚫 Your account has been restricted from using this bot.")

    # 2. 🚫 Group Spam Filter
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if not is_valid_text(message.text):
            try: 
                await message.delete()
            except: 
                pass
            return

    # 3. 🔍 Search Execution (NO F-SUB CHECK HERE)
    query = message.text
    sent_msg = await show_results(client, message, query, page=0)
    
    # 4. 🗑️ Dual Deletion Logic
    if sent_msg:
        asyncio.create_task(auto_delete_messages([message, sent_msg], delay=RESULT_DELETE_TIME))

# Callback handler for F-Sub check
@Client.on_callback_query(filters.regex(r"^check_fsub_"))
async def check_fsub_callback(client, callback):
    user_id = callback.from_user.id
    query = callback.data.split("_", 2)[2]  # Query extract

    if await is_subscribed(client, user_id):
        await callback.message.delete()  # Remove join message
        await show_results(client, callback.message, query, page=0)  # Show search results
    else:
        await callback.answer("⚠️ Channel Not Joined!\n\n👉 Please join the required channel first!", show_alert=True)

# 📂 File button handler
@Client.on_callback_query(filters.regex(r"^get_"))
async def handle_file_button(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # --- 🛡️ PRE-FILE SEND F-SUB CHECK ---
    is_joined, error_msg = await check_fsub_on_demand(client, user_id)
    
    if not is_joined:
        # Join channel message with movie_id preserved
        movie_id = callback.data.split("_")[1]
        return await callback.message.edit_text(
            f"📣 **Channel Membership Required!**\n\n{error_msg}\n\nAfter joining, click the file button again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 𝐉𝐎𝐈𝐍 𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url=FSUB_LINK)],
                [InlineKeyboardButton("🔄 𝐓𝐑𝐘 𝐀𝐆𝐀𝐈𝐍", callback_data=f"get_{movie_id}")]
            ])
        )
    
    movie_id = callback.data.split("_")[1]
    
    # 1. 🔐 Validation Check (6 hours rule)
    if not await is_validated(user_id):
        # If not validated, show verification link
        await callback.answer("🛡️ Verification Required!", show_alert=False)
        
        bot_info = await client.get_me()
        v_link = generate_verify_link(bot_info.username, movie_id)
        
        return await callback.message.reply_text(
            "**🤖 𝐇𝐮𝐦𝐚𝐧 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧 𝐑𝐞𝐪𝐮𝐢𝐫𝐞𝐝**\n\n"
            "**🔒 To continue with file download, please verify that you are not a robot.**\n"
            "**⏳ Verification Valid: 6 Hours**\n\n"
            "**👉 Click the button below to verify:**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 𝐕𝐄𝐑𝐈𝐅𝐘 𝐍𝐎𝐖", url=v_link)]])
        )

    # 2. ✅ If validated, send the file
    movie = await movies.find_one({"_id": ObjectId(movie_id)})
    if not movie:
        return await callback.answer("❌ 𝐅𝐢𝐥𝐞 𝐍𝐨𝐭 𝐅𝐨𝐮𝐧𝐝!\n\nFile has been removed from database.", show_alert=True)

    clean_name = clean_file_name(movie['file_name'])
    caption = CUSTOM_CAPTION.format(
        filename=clean_name,
        filesize=get_readable_size(movie["file_size"])
    )
    
    await callback.answer("📤 𝐒𝐞𝐧𝐝𝐢𝐧𝐠 𝐅𝐢𝐥𝐞...")
    
    try:
        sent_file = await client.copy_message(
            chat_id=callback.message.chat.id,
            from_chat_id=movie["chat_id"],
            message_id=movie["message_id"],
            caption=caption
        )
        # Auto delete logic
        asyncio.create_task(auto_delete_message(sent_file))
    except Exception as e:
        print(f"Error sending file: {e}")
        await callback.message.reply_text("🚨 𝐔𝐩𝐥𝐨𝐚𝐝 𝐄𝐫𝐫𝐨𝐫!\n\nAn error occurred while sending the file. Please try again.")

async def show_results(client, message, query, page=0):
    """
    🎯 Main function to display search results.
    Handles both CAPTION and BUTTON modes based on config.
    """
    
    limit = 10
    skip = page * limit
    
    # 1. 🔍 INITIAL SEARCH
    results, total = await search_movies(query, skip=skip, limit=limit)
    
    original_query = query  # Save original query
    ai_correction_used = False  # Track AI correction

    # 2. 🤖 AI CORRECTION IF NO RESULTS
    if not results and page == 0:
        ai_name = await get_ai_correction(query)
        
        if ai_name and ai_name.lower() != query.lower():
            # AI gave correction? Search with corrected name
            results, total = await search_movies(ai_name, skip=0, limit=10)
            
            if results:
                # Results found with AI correction!
                query = ai_name  # Update query with corrected name
                ai_correction_used = True
                
                # Notify user about correction
                correction_msg = await message.reply_text(f"💡 **Did you mean:** `{ai_name}`?")
                asyncio.create_task(auto_delete_message(correction_msg, delay=10))

    # 3. 📭 NO RESULTS FOUND (EVEN AFTER AI)
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
            asyncio.create_task(auto_delete_messages([message, err_msg], delay=120))
            return None

    # Get bot info for deep linking
    bot = await client.get_me()
    keyboard = []

    # 4. 📄 CAPTION MODE (Text List with Clickable Links)
    if RESULT_MODE == "CAPTION":
        text = f"<b>📂 𝐒𝐄𝐀𝐑𝐂𝐇 𝐑𝐄𝐒𝐔𝐋𝐓𝐒 ({total} 𝐅𝐢𝐥𝐞𝐬)</b>\n\n"
        if ai_correction_used:
            text += f"<b>✨ 𝐒𝐡𝐨𝐰𝐢𝐧𝐠 𝐫𝐞𝐬𝐮𝐥𝐭𝐬 𝐟𝐨𝐫:</b> `{query}`\n<b>📝 𝐎𝐫𝐢𝐠𝐢𝐧𝐚𝐥 𝐬𝐞𝐚𝐫𝐜𝐡:</b> `{original_query}`\n\n"
        else:
            text += f"<b>🔎 𝐒𝐞𝐚𝐫𝐜𝐡 𝐐𝐮𝐞𝐫𝐲:</b> `{query}`\n\n"
        
        text += "<b>📦 𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐅𝐢𝐥𝐞𝐬:</b>\n\n"
        
        for i, movie in enumerate(results, 1):
            size = get_readable_size(movie['file_size'])
            clean_name = movie.get('caption_name', "No Name") 
            link = f"https://t.me/{bot.username}?start=file_{movie['_id']}"
            text += f"{i}. <b><a href='{link}'>📄 {size} | {clean_name}</a></b>\n\n"
    else:
        # 🎛️ BUTTON MODE
        if ai_correction_used:
            text = f"<b>🎬 𝐑𝐞𝐬𝐮𝐥𝐭𝐬 𝐟𝐨𝐫:</b> `{query}`\n<b>💡 𝐎𝐫𝐢𝐠𝐢𝐧𝐚𝐥 𝐬𝐞𝐚𝐫𝐜𝐡:</b> `{original_query}`\n\n"
        else:
            text = f"<b>🎬 𝐒𝐞𝐚𝐫𝐜𝐡 𝐑𝐞𝐬𝐮𝐥𝐭𝐬</b>\n\n<b>🔎 𝐐𝐮𝐞𝐫𝐲:</b> `{query}`\n\n"
        
        text += "<b>⬇️ 𝐂𝐥𝐢𝐜𝐤 𝐛𝐮𝐭𝐭𝐨𝐧𝐬 𝐛𝐞𝐥𝐨𝐰 𝐭𝐨 𝐠𝐞𝐭 𝐟𝐢𝐥𝐞𝐬 ⬇️</b>"
            
        for movie in results:
            size = get_readable_size(movie['file_size'])
            clean_name = movie.get('caption_name') or clean_file_name(movie.get('file_name', 'Unknown'))
            keyboard.append([InlineKeyboardButton(f"📁 [{size}] {clean_name}", callback_data=f"get_{movie['_id']}")])

    # 5. 🎚️ FILTER MANAGEMENT
    query_words = query.split()
    
    # 🔧 If filters are applied (more than one word)
    if len(query_words) > 1:
        filter_rows = [
            [InlineKeyboardButton("🌐 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄", callback_data=f"list_lang_{query}_{page}")],
            [InlineKeyboardButton("🎞️ 𝐐𝐔𝐀𝐋𝐈𝐓𝐘", callback_data=f"list_qual_{query}_{page}"), 
             InlineKeyboardButton("📺 𝐒𝐄𝐀𝐒𝐎𝐍", callback_data=f"list_season_{query}_{page}")],
            [InlineKeyboardButton("📅 𝐘𝐄𝐀𝐑", callback_data=f"list_year_{query}_{page}"),
             InlineKeyboardButton("🎬 𝐄𝐏𝐈𝐒𝐎𝐃𝐄", callback_data=f"list_ep_{query}_{page}")]
        ]
        keyboard.extend(filter_rows)
        
        # 🔄 RESET FILTER BUTTON - go back to first word
        original_word = query_words[0]
        keyboard.append([InlineKeyboardButton("🔄 𝐑𝐄𝐒𝐄𝐓 𝐀𝐋𝐋 𝐅𝐈𝐋𝐓𝐄𝐑𝐒", callback_data=f"page_{original_word}_0")])
    else:
        # If no filters applied (single word query), show filter options
        filter_rows = [
            [InlineKeyboardButton("🌐 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄", callback_data=f"list_lang_{query}_{page}"),
            InlineKeyboardButton("🎞️ 𝐐𝐔𝐀𝐋𝐈𝐓𝐘", callback_data=f"list_qual_{query}_{page}")],
            [InlineKeyboardButton("📅 𝐘𝐄𝐀𝐑", callback_data=f"list_year_{query}_{page}"),
            InlineKeyboardButton("📺 𝐒𝐄𝐀𝐒𝐎𝐍 / 𝐄𝐏𝐈𝐒𝐎𝐃𝐄", callback_data=f"list_season_{query}_{page}")]
        ]
        keyboard.extend(filter_rows)

    # 6. 📄 PAGINATION BUTTONS
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ 𝐏𝐑𝐄𝐕", callback_data=f"page_{query}_{page-1}"))
    
    # Current page indicator
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{(total//10)+1}", callback_data="none"))
    
    if total > (page + 1) * limit:
        nav_buttons.append(InlineKeyboardButton("𝐍𝐄𝐗𝐓 ▶️", callback_data=f"page_{query}_{page+1}"))
    
    keyboard.append(nav_buttons)

    # 7. 📤 SEND OR EDIT MESSAGE
    final_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if isinstance(message, CallbackQuery):
            return await message.message.edit_text(
                text, 
                reply_markup=final_markup, 
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )
        else:
            return await message.reply_text(
                text, 
                reply_markup=final_markup, 
                disable_web_page_preview=True, 
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        print(f"Error updating UI: {e}")
        return None
    
@Client.on_callback_query(filters.regex(r"^list_"))
async def show_filter_options(client, callback: CallbackQuery):
    data = callback.data.split("_")
    category, query, page = data[1], data[2], data[3]

    items = []
    category_names = {
        "lang": "🌐 Language",
        "qual": "🎞️ Quality",
        "year": "📅 Year",
        "season": "📺 Season",
        "ep": "🎬 Episode"
    }
    
    if category == "lang": items = LANGUAGES
    elif category == "qual": items = QUALITIES
    elif category == "year": items = YEARS
    elif category == "season": items = SEASONS
    elif category == "ep": items = EPISODES

    buttons = []
    row = []
    for item in items:
        new_query = f"{query} {item}"
        cb_data = f"page_{new_query}_0"
        if len(cb_data) > 64: cb_data = f"page_{query[:20]}.._{item}_0"  # Data limit fix

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
    query, page = data[1], int(data[2])
    await show_results(client, callback, query, page)