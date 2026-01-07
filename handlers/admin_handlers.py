# --- handlers/admin_handlers.py ---
from pyrogram import Client, filters
from pyrogram.types import Message
from config import ADMINS
from database.users_db import get_db_stats, ban_user, unban_user
from database.movies_db import get_total_movies
from database.stats_db import get_stats_by_date
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.enums import ChatType

@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def admin_stats(client, message):
    m = await message.reply_text("📊 **Fetching Statistics...**")
    db_stats = await get_db_stats()
    total_files = await get_total_movies()
    
    stats_text = f"""
**📊 𝐁𝐎𝐓 𝐒𝐓𝐀𝐓𝐈𝐒𝐓𝐈𝐂𝐒 𝐃𝐀𝐒𝐇𝐁𝐎𝐀𝐑𝐃**
━━━━━━━━━━━━━━━━━━━━━━

👥 **𝐔𝐬𝐞𝐫 𝐒𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐜𝐬:**
├ 👤 **𝐓𝐨𝐭𝐚𝐥 𝐔𝐬𝐞𝐫𝐬:** `{db_stats['total_users']:,}`
└ 👥 **𝐓𝐨𝐭𝐚𝐥 𝐆𝐫𝐨𝐮𝐩𝐬:** `{db_stats['total_groups']:,}`

📂 **𝐅𝐢𝐥𝐞 𝐒𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐜𝐬:**
└ 🎬 **𝐓𝐨𝐭𝐚𝐥 𝐅𝐢𝐥𝐞𝐬:** `{total_files:,}`

💾 **𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧:**
├ 📦 **𝐃𝐚𝐭𝐚 𝐔𝐬𝐚𝐠𝐞:** `{db_stats['data_mb']} MB`
└ 📂 **𝐒𝐭𝐨𝐫𝐚𝐠𝐞 𝐒𝐢𝐳𝐞:** `{db_stats['storage_mb']} MB`

━━━━━━━━━━━━━━━━━━━━━━
⚠️ **𝐒𝐲𝐬𝐭𝐞𝐦 𝐍𝐨𝐭𝐞:**
• 512MB limit applies on free Atlas plan
• Regular maintenance recommended
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