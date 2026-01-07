from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.movies_db import movies, search_movies
from database.users_db import get_user, is_validated
from utils.helpers import get_readable_size, auto_delete_message, clean_file_name, is_valid_text, auto_delete_messages, check_fsub_on_demand, get_ai_correction
from config import RESULT_MODE, LANGUAGES, QUALITIES, YEARS, SEASONS, EPISODES
from config import FSUB_LINK, CUSTOM_CAPTION, RESULT_DELETE_TIME
from bson.objectid import ObjectId
from pyrogram.enums import ParseMode, ChatType
from handlers.cmd_start import generate_verify_link # Import this if it's in cmd_start
import asyncio
import urllib.parse

@Client.on_message(filters.text & (filters.private | filters.group) & ~filters.command(["start", "index", "stats", "ban", "unban"]))
async def main_search_handler(client: Client, message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    chat_type = message.chat.type

    # 1. Ban Check
    if user.get("is_banned"):
        return await message.reply_text(f"❌ **You are restricted!**\nReason: {user.get('ban_reason')}")

    # 2. Group Spam Filter
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if not is_valid_text(message.text):
            try: 
                await message.delete()
            except: 
                pass
            return

    # 3. Search Execution (NO F-SUB CHECK HERE)
    query = message.text
    sent_msg = await show_results(client, message, query, page=0)
    
    # 4. Dual Deletion Logic
    if sent_msg:
        asyncio.create_task(auto_delete_messages([message, sent_msg], delay=RESULT_DELETE_TIME))

# Callback handler for F-Sub check
@Client.on_callback_query(filters.regex(r"^check_fsub_"))
async def check_fsub_callback(client, callback):
    user_id = callback.from_user.id
    query = callback.data.split("_", 2)[2] # Query wapas nikal li

    if await is_subscribed(client, user_id):
        await callback.message.delete() # Join message delete karo
        await show_results(client, callback.message, query, page=0) # Search result dikhao
    else:
        await callback.answer("❌ Abhi bhi join nahi kiya bhai! Pehle join karo.", show_alert=True)

# File button handler
@Client.on_callback_query(filters.regex(r"^get_"))
async def handle_file_button(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # --- FILE BHEJNE SE PEHLE F-SUB CHECK ---
    is_joined, error_msg = await check_fsub_on_demand(client, user_id)
    
    if not is_joined:
        # Join channel message with movie_id preserve
        movie_id = callback.data.split("_")[1]
        return await callback.message.edit_text(
            f"{error_msg}\n\nJoin karne ke baad phir se file button click karo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=FSUB_LINK)],
                [InlineKeyboardButton("🔄 Try Again", callback_data=f"get_{movie_id}")]
            ])
        )
    
    movie_id = callback.data.split("_")[1]
    
    # 1. Validation Check (6 hours rule)
    if not await is_validated(user_id):
        # Agar validated nahi hai, toh alert ki jagah verification link bhejo
        await callback.answer("Verification Required!", show_alert=False)
        
        bot_info = await client.get_me()
        v_link = generate_verify_link(bot_info.username, movie_id)
        
        return await callback.message.reply_text(
            "🚀 **Verification Required!**\n\nFile download karne ke liye niche button pe click karke validate karein (Valid for 6 hours):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Verify / Open Link", url=v_link)]])
        )

    # 2. Agar validated hai, toh file bhej do
    movie = await movies.find_one({"_id": ObjectId(movie_id)})
    if not movie:
        return await callback.answer("❌ File records mein nahi hai!", show_alert=True)

    clean_name = clean_file_name(movie['file_name'])
    caption = CUSTOM_CAPTION.format(
        filename=clean_name,
        filesize=get_readable_size(movie["file_size"])
    )
    
    await callback.answer("Sending file... 📤")
    
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
        await callback.message.reply_text("❌ Kuch error aaya file bhejne mein!")

async def show_results(client, message, query, page=0):
    """
    Main function to display search results.
    Handles both CAPTION and BUTTON modes based on config.
    """
    
    limit = 10
    skip = page * limit
    
    # 1. PEHLE NORMAL SEARCH KARO
    results, total = await search_movies(query, skip=skip, limit=limit)
    
    original_query = query  # Original query save karo
    ai_correction_used = False  # Track if AI correction was used

    # 2. AGAR RESULTS NAHI MILE AUR FIRST PAGE HAI, TOH AI SE PUCHO
    if not results and page == 0:
        ai_name = await get_ai_correction(query)
        
        if ai_name and ai_name.lower() != query.lower():
            # AI ne correction di? Toh fir se search karo sahi naam se
            results, total = await search_movies(ai_name, skip=0, limit=10)
            
            if results:
                # Agar AI ki wajah se results mil gaye!
                query = ai_name  # Query ko sahi naam se badal do
                ai_correction_used = True
                
                # User ko bataye ki AI ne correction kiya
                correction_msg = await message.reply_text(f"💡 **Did you mean:** `{ai_name}`?")
                # Correction message ko bhi auto-delete ke liye add karo
                asyncio.create_task(auto_delete_message(correction_msg, delay=10))

    # 3. AGAR ABHI BHI RESULTS NAHI MILE (AI BHI FAIL HO GAYA)
    if not results:
        # Wahi purana Google wala logic
        google_query = urllib.parse.quote(query)
        google_link = f"https://www.google.com/search?q={google_query}"
        
        not_found_text = f"❌ **No results found for:** `{query}`\nTry different keywords!"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Search on Google", url=google_link)]])

        if isinstance(message, CallbackQuery):
            await message.answer(not_found_text, show_alert=True)
            return None
        else:
            err_msg = await message.reply_text(not_found_text, reply_markup=markup)
            # 2 MINUTE BAAD DELETE (User ka msg + Bot ka error msg)
            asyncio.create_task(auto_delete_messages([message, err_msg], delay=120))
            return None

    # Get bot info for deep linking
    bot = await client.get_me()
    keyboard = []

    text = f"📂 **Search Results: {total}**\n\n"

    # 4. CAPTION MODE (Text List with Clickable Links)
    if RESULT_MODE == "CAPTION":
        text = f"📂 **Search Results: {total}**\n\n"
        if ai_correction_used:
            text += f"💡 *Showing results for:* `{query}`\n*(Originally searched: {original_query})*\n\n"
        
        for i, movie in enumerate(results, 1):
            size = get_readable_size(movie['file_size'])
            # CLEANING AB JARURAT NAHI HAI! DB se uthao
            clean_name = movie.get('caption_name', "No Name") 
            
            link = f"https://t.me/{bot.username}?start=file_{movie['_id']}"
            text += f"{i}. <b><a href='{link}'>{clean_name}</a></b>\n      └ 💾 <code>{size}</code>\n\n"
    else:
        # BUTTON MODE
        if ai_correction_used:
            text = f"🎬 **Results for:** `{query}`\n💡 *Originally searched:* `{original_query}`\n\n*(Files niche buttons mein hain)*"
        else:
            text = f"🎬 **Results for:** `{query}`\n\n*(Files niche buttons mein hain)*"
            
        for movie in results:
            size = get_readable_size(movie['file_size'])
            clean_name = movie.get('caption_name') or clean_file_name(movie.get('file_name', 'Unknown'))
            keyboard.append([InlineKeyboardButton(f"[{size}] {clean_name}", callback_data=f"get_{movie['_id']}")])

    # 5. CHECK IF FILTERS ARE APPLIED
    # Pehle words count dekho - agar query mein ek se zyada words hain toh filter laga hua hai
    query_words = query.split()
    
    # Agar filter laga hua hai (ek se zyada words) toh filter buttons dikhao
    if len(query_words) > 1:
        filter_rows = [
            [InlineKeyboardButton("•CHOOSE LANGUAGE•", callback_data=f"list_lang_{query}_{page}")],
            [InlineKeyboardButton("•QUALITY", callback_data=f"list_qual_{query}_{page}"), 
             InlineKeyboardButton("season•", callback_data=f"list_season_{query}_{page}")],
            [InlineKeyboardButton("Year 📅", callback_data=f"list_year_{query}_{page}"),
             InlineKeyboardButton("Episode 📺", callback_data=f"list_ep_{query}_{page}")]
        ]
        keyboard.extend(filter_rows)
        
        # RESET FILTER BUTTON - pehle word par wapas jao
        original_word = query_words[0]
        keyboard.append([InlineKeyboardButton("🔄 RESET ALL FILTERS", callback_data=f"page_{original_word}_0")])
    else:
        # Agar koi filter nahi laga (single word query), toh filter selection options dikhao
        filter_rows = [
            [InlineKeyboardButton("🎭 Add Language Filter", callback_data=f"list_lang_{query}_{page}")],
            [InlineKeyboardButton("📀 Add Quality Filter", callback_data=f"list_qual_{query}_{page}")],
            [InlineKeyboardButton("📅 Add Year Filter", callback_data=f"list_year_{query}_{page}")],
            [InlineKeyboardButton("📺 Add Season/Episode Filter", callback_data=f"list_season_{query}_{page}")]
        ]
        keyboard.extend(filter_rows)
        # RESET button nahi dikhao kyunki kuch reset karne ko hai hi nahi

    # 6. PAGINATION BUTTONS
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ PREV", callback_data=f"page_{query}_{page-1}"))
    
    # Current page indicator
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{(total//10)+1}", callback_data="none"))
    
    if total > (page + 1) * limit:
        nav_buttons.append(InlineKeyboardButton("NEXT ➡️", callback_data=f"page_{query}_{page+1}"))
    
    keyboard.append(nav_buttons)

    # 7. SEND OR EDIT MESSAGE
    # We disable web page preview so the clickable links don't show thumbnails
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
        if len(cb_data) > 64: cb_data = f"page_{query[:20]}.._{item}_0" # Data limit fix

        row.append(InlineKeyboardButton(item, callback_data=cb_data))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton("⬅️ BACK", callback_data=f"page_{query}_{page}")])
    await callback.message.edit_text(f"🎯 **Filters for:** `{query}`", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^page_"))
async def handle_pagination(client, callback: CallbackQuery):
    data = callback.data.split("_")
    query, page = data[1], int(data[2])
    await show_results(client, callback, query, page)