import uuid
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.users_db import get_user, update_validation, is_validated, check_premium
from database.movies_db import movies, get_total_movies
from database.settings_db import get_settings
from utils.shortener import shorten_url
from utils.helpers import get_readable_size, auto_delete_messages, clean_file_name, check_fsub_on_demand
from config import CUSTOM_CAPTION, SEPARATE_NOTE, RESULT_DELETE_TIME
from bson.objectid import ObjectId
from database.stats_db import increment_gen, increment_verify
from datetime import datetime

pending_validations = {}

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    if getattr(message, "forward_date", None) or getattr(message, "forward_origin", None):
        return

    user_id = message.from_user.id
    text = message.text.split()
    settings = await get_settings()

    if len(text) > 1 and text[1].startswith("verify_"):
        token = text[1].split("_")[1]

        if token in pending_validations:
            today = datetime.now().strftime("%Y-%m-%d")
            await increment_verify(today)
            await update_validation(user_id)
            file_info = pending_validations.pop(token)

            await message.reply_text("**✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞𝐝!**\n\n**🤖 𝐇𝐮𝐦𝐚𝐧 𝐂𝐨𝐧𝐟𝐢𝐫𝐦𝐞𝐝**\n**⏳ 𝐕𝐚𝐥𝐢𝐝𝐢𝐭𝐲:** Next 6 hours")

            movie = await movies.find_one({"_id": ObjectId(file_info["movie_id"])})
            if movie:
                clean_name = clean_file_name(movie['file_name'])
                caption = CUSTOM_CAPTION.format(filename=clean_name, filesize=get_readable_size(movie["file_size"]))

                sent_file = await client.copy_message(
                    chat_id=message.chat.id, from_chat_id=movie["chat_id"],
                    message_id=movie["message_id"], caption=caption
                )
                note_msg = await message.reply_text(SEPARATE_NOTE)

                msgs_to_delete = [sent_file, note_msg] # File aur note hamesha delete honge (Copyright safe)
                if settings.get("auto_delete", True):
                    msgs_to_delete.append(message) # User ka /start command delete hoga agar True hai

                asyncio.create_task(auto_delete_messages(client, message.chat.id, msgs_to_delete, delay=RESULT_DELETE_TIME))
            return
        else:
            return await message.reply_text("⚠️ **Expired Token!**\n\nThis verification link has expired or is invalid.")

    if len(text) > 1 and text[1].startswith("file_"):
        movie_id = text[1].split("_")[1]
        is_joined, error_msg, fsub_link = await check_fsub_on_demand(client, user_id)

        if not is_joined:
            buttons = []
            if fsub_link: buttons.append([InlineKeyboardButton("🎯 𝐉𝐎𝐈𝐍 𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url=fsub_link)])
            buttons.append([InlineKeyboardButton("🔄 𝐂𝐇𝐄𝐂𝐊 𝐀𝐆𝐀𝐈𝐍", callback_data=f"get_{movie_id}")])

            return await message.reply_text(f"**📣 Channel Membership Required!**\n\n{error_msg}", reply_markup=InlineKeyboardMarkup(buttons))

        is_prem = await check_premium(user_id)
        if is_prem or await is_validated(user_id):
            movie = await movies.find_one({"_id": ObjectId(movie_id)})
            if not movie: return await message.reply_text("❌ **File Not Found!**")

            clean_name = clean_file_name(movie['file_name'])
            caption = CUSTOM_CAPTION.format(filename=clean_name, filesize=get_readable_size(movie["file_size"]))

            await message.reply_text("📤 **Sending File...**")
            sent_file = await client.copy_message(
                chat_id=message.chat.id, from_chat_id=movie["chat_id"],
                message_id=movie["message_id"], caption=caption
            )
            note_msg = await message.reply_text(SEPARATE_NOTE)

            msgs_to_delete = [sent_file, note_msg]
            if settings.get("auto_delete", True):
                msgs_to_delete.append(message) # /start command sirf True hone pe delete hogi
            asyncio.create_task(auto_delete_messages(client, message.chat.id, msgs_to_delete, delay=RESULT_DELETE_TIME))
        else:
            bot_info = await client.get_me()
            v_link = await generate_verify_link(bot_info.username, movie_id)
            await message.reply_text(
                "**🛡️ Human Verification Required**\n\n**👉 Click below to verify:**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 𝐕𝐄𝐑𝐈𝐅𝐘 𝐍𝐎𝐖", url=v_link)]])
            )
        return

    await get_user(user_id)
    welcome_text = (
        f"**👋 Welcome, {message.from_user.first_name}!**\n\n"
        f"**🎬 Movie Delivery Bot**\n"
        f"**🔍 Start Searching:** Simply type any movie/series name"
    )
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 𝐁𝐎𝐓 𝐒𝐓𝐀𝐓𝐒", callback_data="stats_btn"), InlineKeyboardButton("ℹ️ 𝐇𝐄𝐋𝐏", callback_data="help_btn")]
    ]))


@Client.on_callback_query(filters.regex(r"^get_"))
async def handle_file_button(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    movie_id = callback.data.split("_")[1]
    settings = await get_settings()

    is_joined, error_msg, fsub_link = await check_fsub_on_demand(client, user_id)
    if not is_joined:
        buttons = []
        if fsub_link:
            buttons.append([InlineKeyboardButton("🎯 𝐉𝐎𝐈𝐍 𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url=fsub_link)])
        buttons.append([InlineKeyboardButton("🔄 𝐂𝐇𝐄𝐂𝐊 𝐀𝐆𝐀𝐈𝐍", callback_data=f"get_{movie_id}")])

        return await callback.message.edit_text(
            f"**📣 Channel Membership Required!**\n\n{error_msg}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    is_prem = await check_premium(user_id)

    if not is_prem and not await is_validated(user_id):
        await callback.answer("🛡️ Verification Required!", show_alert=False)
        bot_info = await client.get_me()
        v_link = await generate_verify_link(bot_info.username, movie_id)
        return await callback.message.reply_text(
            "**🤖 𝐇𝐮𝐦𝐚𝐧 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧 𝐑𝐞𝐪𝐮𝐢𝐫𝐞𝐝**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 𝐕𝐄𝐑𝐈𝐅𝐘 𝐍𝐎𝐖", url=v_link)]])
        )

    movie = await movies.find_one({"_id": ObjectId(movie_id)})
    if not movie:
        return await callback.answer("❌ 𝐅𝐢𝐥𝐞 𝐍𝐨𝐭 𝐅𝐨𝐮𝐧𝐝!", show_alert=True)

    clean_name = clean_file_name(movie['file_name'])
    caption = CUSTOM_CAPTION.format(filename=clean_name, filesize=get_readable_size(movie["file_size"]))

    await callback.message.edit_text("📤 **Sending File...**")
    sent_file = await client.copy_message(
        chat_id=callback.message.chat.id,
        from_chat_id=movie["chat_id"],
        message_id=movie["message_id"],
        caption=caption
    )
    note_msg = await callback.message.reply_text(SEPARATE_NOTE)

    # File bhejte time bot ke dono messages hamesha auto delete honge
    asyncio.create_task(auto_delete_messages(client, callback.message.chat.id, [sent_file, note_msg], delay=RESULT_DELETE_TIME))

    await callback.answer("File sent!", show_alert=False)


@Client.on_callback_query(filters.regex("stats_btn"))
async def stats_btn_handler(client, callback):
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


async def generate_verify_link(bot_username, movie_id):
    token = str(uuid.uuid4())[:8]
    pending_validations[token] = {"movie_id": movie_id}

    today = datetime.now().strftime("%Y-%m-%d")
    asyncio.create_task(increment_gen(today))

    original_url = f"https://t.me/{bot_username}?start=verify_{token}"

    settings = await get_settings()
    short_url = await shorten_url(original_url, settings.get("shortener_url"), settings.get("shortener_api"))

    return short_url or original_url
