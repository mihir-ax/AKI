# --- handlers/admin_handlers.py ---

import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatType
from config import START_TIME

from config import ADMINS

from database.users_db import get_db_stats, ban_user, unban_user
from database.movies_db import get_total_movies
from database.stats_db import get_stats_by_date
from database.settings_db import get_settings, update_setting

from datetime import datetime, timedelta

# Temporary dictionary to handle Admin text inputs
ADMIN_STATES = {}

# -------- SETTINGS PANEL --------
@Client.on_message(filters.command("settings") & filters.user(ADMINS))
async def settings_handler(client, message):
    settings = await get_settings()

    text = "**⚙️ BOT SETTINGS PANEL**\n\nConfigure bot features below:"

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"PM Search: {'✅ ON' if settings.get('pm_search') else '❌ OFF'}", callback_data="set_toggle_pm_search")],
        [InlineKeyboardButton(f"Auto-Delete: {'✅ ON' if settings.get('auto_delete') else '❌ OFF'}", callback_data="set_toggle_auto_delete")],
        [InlineKeyboardButton(f"Delete Banned Content: {'✅ ON' if settings.get('delete_banned') else '❌ OFF'}", callback_data="set_toggle_delete_banned")],
        [InlineKeyboardButton("🔗 Edit Shortener URL", callback_data="set_edit_url")],
        [InlineKeyboardButton("🔑 Edit Shortener API Key", callback_data="set_edit_api")],
        [InlineKeyboardButton("❌ Close", callback_data="set_close")]
    ])
    await message.reply_text(text, reply_markup=btn)

@Client.on_callback_query(filters.regex(r"^set_") & filters.user(ADMINS))
async def settings_callbacks(client, callback: CallbackQuery):
    action = callback.data.split("_", 1)[1]
    settings = await get_settings()

    if action.startswith("toggle_"):
        key = action.replace("toggle_", "")
        current_val = settings.get(key, True)
        await update_setting(key, not current_val)
        await callback.answer(f"{key.replace('_', ' ').title()} Updated!", show_alert=True)

        # Refresh Panel
        new_settings = await get_settings()
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"PM Search: {'✅ ON' if new_settings.get('pm_search') else '❌ OFF'}", callback_data="set_toggle_pm_search")],
            [InlineKeyboardButton(f"Auto-Delete: {'✅ ON' if new_settings.get('auto_delete') else '❌ OFF'}", callback_data="set_toggle_auto_delete")],
            [InlineKeyboardButton(f"Delete Banned Content: {'✅ ON' if new_settings.get('delete_banned') else '❌ OFF'}", callback_data="set_toggle_delete_banned")],
            [InlineKeyboardButton("🔗 Edit Shortener URL", callback_data="set_edit_url")],
            [InlineKeyboardButton("🔑 Edit Shortener API Key", callback_data="set_edit_api")],
            [InlineKeyboardButton("❌ Close", callback_data="set_close")]
        ])
        await callback.message.edit_reply_markup(btn)

    elif action == "edit_url":
        ADMIN_STATES[callback.from_user.id] = "awaiting_shortener_url"
        await callback.message.reply_text("✏️ **Send the new Shortener URL:**\n(Example: `http://shortxlinks.com/api`)")
        await callback.answer()

    elif action == "edit_api":
        ADMIN_STATES[callback.from_user.id] = "awaiting_shortener_api"
        await callback.message.reply_text("🔑 **Send the new Shortener API Key:**")
        await callback.answer()

    elif action == "close":
        await callback.message.delete()

# Listen for Admin Text inputs for settings
@Client.on_message(filters.text & filters.private & filters.user(ADMINS), group=-1)
async def admin_text_listener(client, message):
    user_id = message.from_user.id
    if user_id in ADMIN_STATES:
        state = ADMIN_STATES[user_id]
        if state == "awaiting_shortener_url":
            await update_setting("shortener_url", message.text.strip())
            await message.reply_text("✅ **Shortener URL Updated Successfully!**")
            del ADMIN_STATES[user_id]
            message.stop_propagation()

        elif state == "awaiting_shortener_api":
            await update_setting("shortener_api", message.text.strip())
            await message.reply_text("✅ **Shortener API Key Updated Successfully!**")
            del ADMIN_STATES[user_id]
            message.stop_propagation()

def get_uptime():
    uptime_sec = int(time.time() - START_TIME)
    days, rem = divmod(uptime_sec, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def admin_stats(client, message):
    m = await message.reply_text("📊 **Fetching Statistics...**")
    db_stats = await get_db_stats()
    total_files = await get_total_movies()
    uptime = get_uptime() # ✅ Uptime fetch kiya

    stats_text = f"""
**📊 𝐁𝐎𝐓 𝐒𝐓𝐀𝐓𝐈𝐒𝐓𝐈𝐂𝐒 𝐃𝐀𝐒𝐇𝐁𝐎𝐀𝐑𝐃**
━━━━━━━━━━━━━━━━━━━━━━

⏱️ **𝐁𝐨𝐭 𝐔𝐩𝐭𝐢𝐦𝐞:** `{uptime}`

👥 **𝐔𝐬𝐞𝐫 𝐒𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐜𝐬:**
├ 👤 **𝐓𝐨𝐭𝐚𝐥 𝐔𝐬𝐞𝐫𝐬:** `{db_stats['total_users']:,}`
└ 👥 **𝐓𝐨𝐭𝐚𝐥 𝐆𝐫𝐨𝐮𝐩𝐬:** `{db_stats['total_groups']:,}`

📂 **𝐅𝐢𝐥𝐞 𝐒𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐜𝐬:**
└ 🎬 **𝐓𝐨𝐭𝐚𝐥 𝐅𝐢𝐥𝐞𝐬:** `{total_files:,}`

💾 **𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧:**
├ 📦 **𝐃𝐚𝐭𝐚 𝐔𝐬𝐚𝐠𝐞:** `{db_stats['data_mb']} MB`
└ 📂 **𝐒𝐭𝐨𝐫𝐚𝐠𝐞 𝐒𝐢𝐳𝐞:** `{db_stats['storage_mb']} MB`

━━━━━━━━━━━━━━━━━━━━━━
"""
    await m.edit_text(stats_text)

@Client.on_message(filters.command("ban") & filters.user(ADMINS))
async def ban_handler(client, message):
    if len(message.command) < 3:
        return await message.reply_text(
            "🛡️ **Usage:** `/ban <user_id> <reason>`\n\n"
            "**Example:** `/ban 123456789 Spamming bot`"
        )

    try:
        user_id = int(message.command[1])
        reason = " ".join(message.command[2:])

        await ban_user(user_id, reason)
        await message.reply_text(
            f"✅ **User Restricted Successfully**\n\n"
            f"**👤 User ID:** `{user_id}`\n"
            f"**📝 Reason:** {reason}\n"
            f"**🛡️ Status:** Banned from bot access"
        )
    except ValueError:
        await message.reply_text("❌ **Invalid User ID**\n\nPlease provide a valid numeric user ID.")
    except Exception as e:
        await message.reply_text(f"⚠️ **Restriction Failed**\n\nError: {str(e)}")

@Client.on_message(filters.command("unban") & filters.user(ADMINS))
async def unban_handler(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            "🛡️ **Usage:** `/unban <user_id>`\n\n"
            "**Example:** `/unban 123456789`"
        )

    try:
        user_id = int(message.command[1])
        await unban_user(user_id)
        await message.reply_text(
            f"✅ **Restriction Removed**\n\n"
            f"**👤 User ID:** `{user_id}`\n"
            f"**🔄 Status:** Access restored successfully"
        )
    except ValueError:
        await message.reply_text("❌ **Invalid User ID**\n\nPlease provide a valid numeric user ID.")
    except Exception as e:
        await message.reply_text(f"⚠️ **Unban Failed**\n\nError: {str(e)}")

# 🏷️ Group tracker: When bot is added to a group
@Client.on_message(filters.new_chat_members)
async def track_groups(client, message):
    if any(m.is_self for m in message.new_chat_members):
        from database.users_db import add_group
        await add_group(message.chat.id, message.chat.title)
        await client.send_message(
            message.chat.id,
            "🎉 **Thanks for adding me!**\n\n"
            "🎬 **I can search movies here too!**\n"
            "🔍 **Just type any movie/series name**\n\n"
            "✨ **Features:**\n"
            "• Instant file delivery\n"
            "• Advanced filters\n"
            "• Group-friendly interface"
        )

# ⚡ Index Command (Commented for now - Remove if not needed)
# @Client.on_message(filters.command("index") & filters.user(ADMINS))
# async def bulk_index_handler(client: Client, message: Message):
#     """
#     Usage: /index start_link end_link
#     Example: /index https://t.me/c/12345678/1 https://t.me/c/12345678/100
#     """
#     if len(message.command) < 3:
#         return await message.reply_text(
#             "❌ **Invalid Format!**\n\n"
#             "📌 **Correct Usage:** `/index START_LINK END_LINK`\n\n"
#             "**Example:**\n"
#             "`/index https://t.me/c/12345678/1 https://t.me/c/12345678/100`"
#         )
#
#     # ... (rest of your existing index handler code remains the same)
#     # The commented code has been left intact as requested

@Client.on_message(filters.command("id"))
async def get_id_handler(client, message):
    # 1. 🏠 Private Chat Case
    if message.chat.type == ChatType.PRIVATE:
        await message.reply_text(
            f"**🆔 𝐔𝐬𝐞𝐫 𝐈𝐃 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧**\n\n"
            f"**👤 Your User ID:** `{message.from_user.id}`\n"
            f"**👤 Username:** @{message.from_user.username or 'Not set'}"
        )

    # 2. 👥 Group / Supergroup Case
    elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:

        # A. 📝 When replying to a user's message
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            if target_user:
                await message.reply_text(
                    f"**🆔 𝐔𝐬𝐞𝐫 𝐈𝐃 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧**\n\n"
                    f"**👤 Target User:** {target_user.mention}\n"
                    f"**🆔 User ID:** `{target_user.id}`\n"
                    f"**👥 Group ID:** `{message.chat.id}`\n"
                    f"**💬 Group Name:** {message.chat.title}"
                )
            else:
                await message.reply_text(
                    "❌ **Unable to Fetch User ID**\n\n"
                    "**Possible reasons:**\n"
                    "• User has hidden profile\n"
                    "• Message from anonymous admin\n"
                    "• System/bot message"
                )

        # B. 🔍 Just /id command without reply
        else:
            await message.reply_text(
                f"**🆔 𝐈𝐃 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧**\n\n"
                f"**👥 Group Information:**\n"
                f"**🆔 Group ID:** `{message.chat.id}`\n"
                f"**💬 Group Name:** {message.chat.title}\n\n"
                f"**👤 Your Information:**\n"
                f"**🆔 Your User ID:** `{message.from_user.id}`\n"
                f"**👤 Username:** @{message.from_user.username or 'Not set'}"
            )

@Client.on_message(filters.command("dstats") & filters.user(ADMINS))
async def daily_stats_handler(client, message):
    # 📅 Today's date
    today = datetime.now().strftime("%Y-%m-%d")
    # 📅 Yesterday's date for comparison
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 📊 Fetch statistics
    s_today = await get_stats_by_date(today) or {"links_generated": 0, "links_verified": 0}
    s_yesterday = await get_stats_by_date(yesterday) or {"links_generated": 0, "links_verified": 0}

    # 📈 Calculate success percentage
    def get_success_rate(generated, verified):
        if generated == 0:
            return 0.0
        return round((verified / generated) * 100, 2)

    today_rate = get_success_rate(s_today['links_generated'], s_today['links_verified'])
    yesterday_rate = get_success_rate(s_yesterday['links_generated'], s_yesterday['links_verified'])

    # 📊 Performance comparison
    trend = "📈" if s_today['links_verified'] > s_yesterday['links_verified'] else "📉" if s_today['links_verified'] < s_yesterday['links_verified'] else "➡️"

    text = f"""
**📅 𝐃𝐀𝐈𝐋𝐘 𝐒𝐓𝐀𝐓𝐈𝐒𝐓𝐈𝐂𝐒 𝐑𝐄𝐏𝐎𝐑𝐓**
━━━━━━━━━━━━━━━━━━━━━━

☀️ **𝐓𝐎𝐃𝐀𝐘 ({today})**
├ 🔗 **Links Generated:** `{s_today['links_generated']:,}`
├ ✅ **Links Verified:** `{s_today['links_verified']:,}`
└ 📊 **Success Rate:** `{today_rate}%`

━━━━━━━━━━━━━━━━━━━━━━
🌙 **𝐘𝐄𝐒𝐓𝐄𝐑𝐃𝐀𝐘 ({yesterday})**
├ 🔗 **Links Generated:** `{s_yesterday['links_generated']:,}`
├ ✅ **Links Verified:** `{s_yesterday['links_verified']:,}`
└ 📊 **Success Rate:** `{yesterday_rate}%`

━━━━━━━━━━━━━━━━━━━━━━
📈 **𝐏𝐄𝐑𝐅𝐎𝐑𝐌𝐀𝐍𝐂𝐄 𝐓𝐑𝐄𝐍𝐃**
├ {trend} **Verification Trend:** {"Up" if trend == "📈" else "Down" if trend == "📉" else "Stable"}
├ 🔄 **Daily Change:** {s_today['links_verified'] - s_yesterday['links_verified']:,}
└ 🎯 **Overall Efficiency:** {"Excellent" if today_rate > 80 else "Good" if today_rate > 60 else "Needs Attention"}
━━━━━━━━━━━━━━━━━━━━━━
"""

    await message.reply_text(text)


@Client.on_message(filters.command("fsub") & filters.user(ADMINS))
async def fsub_toggle_handler(client, message):
    """
    Toggle Force Subscribe feature on/off
    """
    from config import FSUB_ENABLED, FSUB_CHANNEL

    if len(message.command) > 1:
        # /fsub on ya /fsub off
        action = message.command[1].lower()

        if action in ["on", "yes", "true", "enable"]:
            # Enable FSUB
            # Yahan tum apne config ko update karne ka logic add karoge
            # For example, database mein store karo ya config file update karo
            await message.reply_text(
                f"✅ **Force Subscribe ENABLED**\n\n"
                f"**Channel:** {FSUB_CHANNEL}\n"
                f"**Status:** Users must join channel to download files"
            )
        elif action in ["off", "no", "false", "disable"]:
            # Disable FSUB
            await message.reply_text(
                "✅ **Force Subscribe DISABLED**\n\n"
                "**Status:** Users can download files without joining channel"
            )
        else:
            await message.reply_text(
                "⚠️ **Usage:** `/fsub on` or `/fsub off`\n\n"
                f"**Current Status:** {'ENABLED' if FSUB_ENABLED else 'DISABLED'}"
            )
    else:
        # Show current status
        await message.reply_text(
            f"📢 **Force Subscribe Status**\n\n"
            f"**Enabled:** {'✅ Yes' if FSUB_ENABLED else '❌ No'}\n"
            f"**Channel:** {FSUB_CHANNEL or 'Not set'}\n\n"
            f"**Commands:**\n"
            f"• `/fsub on` - Enable force subscribe\n"
            f"• `/fsub off` - Disable force subscribe"
        )
