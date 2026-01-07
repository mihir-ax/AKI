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
    m = await message.reply_text("Fetching stats... ⏳")
    db_stats = await get_db_stats()
    total_files = await get_total_movies()
    
    stats_text = (f"""
> 📊 **ʙᴏᴛ ᴅᴀꜱʜʙᴏᴀʀᴅ**

👤 **ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ**  ➤ `{db_stats['total_users']}`

👥 **ᴛᴏᴛᴀʟ ɢʀᴏᴜᴘꜱ**  ➤ `{db_stats['total_groups']}`

🎬 **ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ**  ➤ `{total_files}`

━━━━━━━━━━━━━━━━━━
> 💾 **ᴅᴀᴛᴀʙᴀꜱᴇ ɪɴꜰᴏ**

📦 **ᴅᴀᴛᴀ ᴜꜱᴇᴅ**  ➤ `{db_stats['data_mb']} ᴍʙ`

📂 **ꜱᴛᴏʀᴀɢᴇ ꜱɪᴢᴇ**  ➤ `{db_stats['storage_mb']} ᴍʙ`

> ⚠️ **512ᴍʙ ʟɪᴍɪᴛ ᴀᴘᴘʟɪᴇꜱ ᴏɴ ꜰʀᴇᴇ ᴀᴛʟᴀꜱ ᴘʟᴀɴ**
    """)
    await m.edit_text(stats_text)

@Client.on_message(filters.command("ban") & filters.user(ADMINS))
async def ban_handler(client, message):
    if len(message.command) < 3:
        return await message.reply_text("📌 **ᴜꜱᴀɢᴇ:** `/ban <ᴜꜱᴇʀ_ɪᴅ> <ʀᴇᴀꜱᴏɴ>`")
    
    try:
        user_id = int(message.command[1])
        reason = " ".join(message.command[2:])
        await ban_user(user_id, reason)
        await message.reply_text(f"✅ **ᴜꜱᴇʀ `{user_id}` ʜᴀꜱ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ.**\n📝 **ʀᴇᴀꜱᴏɴ:** {reason}")
    except ValueError:
        await message.reply_text("❌ **ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴜꜱᴇʀ ɪᴅ.**")

@Client.on_message(filters.command("unban") & filters.user(ADMINS))
async def unban_handler(client, message):
    if len(message.command) < 2:
        return await message.reply_text("📌 **ᴜꜱᴀɢᴇ:** `/unban <ᴜꜱᴇʀ_ɪᴅ>`")
    
    user_id = int(message.command[1])
    await unban_user(user_id)
    await message.reply_text(f"✅ **ᴜꜱᴇʀ `{user_id}` ɪꜱ ɴᴏᴡ ꜰʀᴇᴇ ᴛᴏ ᴜꜱᴇ ᴛʜᴇ ʙᴏᴛ.**")

# Group tracker: bot jab group mein add ho
@Client.on_message(filters.new_chat_members)
async def track_groups(client, message):
    if any(m.is_self for m in message.new_chat_members):
        from database.users_db import add_group
        await add_group(message.chat.id, message.chat.title)
        await client.send_message(message.chat.id, "🎉 **ᴛʜᴀɴᴋꜱ ꜰᴏʀ ᴀᴅᴅɪɴɢ ᴍᴇ!**\n🎬 **ɪ ᴄᴀɴ ᴀʟꜱᴏ ꜱᴇᴀʀᴄʜ ᴍᴏᴠɪᴇꜱ ʜᴇʀᴇ.**")

# @Client.on_message(filters.command("index") & filters.user(ADMINS))
# async def bulk_index_handler(client: Client, message: Message):
#     """
#     Usage: /index start_link end_link
#     Example: /index https://t.me/c/12345678/1 https://t.me/c/12345678/100
#     """
#     if len(message.command) < 3:
#         return await message.reply_text(
#             "❌ **Bhai format galat hai!**\n\n"
#             "Sahi tarika: `/index START_LINK END_LINK`"
#         )

#     start_link = message.command[1]
#     end_link = message.command[2]

#     # Function to extract chat_id and message_id from link
#     def parse_link(link):
#         # Pattern for private channel: t.me/c/12345678/10
#         # Pattern for public channel: t.me/channel_name/10
#         pattern = r"t.me/(?:c/)?([^/]+)/(\d+)"
#         match = re.search(pattern, link)
#         if match:
#             chat_id = match.group(1)
#             msg_id = int(match.group(2))
#             if chat_id.isdigit():
#                 chat_id = int("-100" + chat_id) # Convert to private channel ID
#             return chat_id, msg_id
#         return None, None

#     s_chat, s_id = parse_link(start_link)
#     e_chat, e_id = parse_link(end_link)

#     if not s_id or not e_id or s_chat != e_chat:
#         return await message.reply_text("❌ **Invalid Links!** Dono link ek hi channel ki honi chahiye.")

#     status_msg = await message.reply_text(f"🚀 **Indexing Started...**\nFrom: `{s_id}` To: `{e_id}`")
    
#     count = 0
#     # Loop from start message ID to end message ID
#     for current_id in range(s_id, e_id + 1):
#         try:
#             msg = await client.get_messages(s_chat, current_id)
            
#             # Check if message is deleted or empty
#             if not msg or msg.empty:
#                 continue
                
#             # Filter: Only Video or Documents that are videos
#             file = None
#             if msg.video:
#                 file = msg.video
#             elif msg.document and "video" in (msg.document.mime_type or "").lower():
#                 file = msg.document
            
#             if file:
#                 await add_movie(
#                     file_id=file.file_id,
#                     file_name=file.file_name or "Unknown_File",
#                     file_size=file.file_size,
#                     chat_id=s_chat,
#                     message_id=msg.id
#                 )
#                 count += 1

#             # Update status every 20 messages so we don't hit flood limits too fast
#             if current_id % 20 == 0:
#                 await status_msg.edit_text(f"⚡ **Processing...**\nAt ID: `{current_id}`\nFiles Saved: `{count}`")
#                 await asyncio.sleep(1) # Small delay to be safe

#         except FloodWait as e:
#             await asyncio.sleep(e.value) # Wait if Telegram says so
#         except Exception as e:
#             print(f"Error at ID {current_id}: {e}")
#             continue

#     await status_msg.edit_text(f"🏁 **Indexing Finished!**\nTotal `{count}` media files added to DB.")

@Client.on_message(filters.command("id"))
async def get_id_handler(client, message):
    # 1. Private Chat Case
    if message.chat.type == ChatType.PRIVATE:
        await message.reply_text(
            f"**›› ᴏᴜʀ ɪᴅ:** <code>{message.from_user.id}</code>"
        )
    
    # 2. Group / Supergroup Case
    elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        
        # A. Agar kisi user ke message pe reply karke /id likha hai
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            # Check for hidden profiles or bots
            if target_user:
                await message.reply_text(
                    f"**›› ᴜꜱᴇʀ:** {target_user.mention}\n"
                    f"**›› ᴜꜱᴇʀ ɪᴅ:** <code>{target_user.id}</code>\n"
                    f"**›› ɢʀᴏᴜᴘ ɪᴅ:** <code>{message.chat.id}</code>"
                )
            else:
                await message.reply_text("❌ **ᴜɴᴀʙʟᴇ ᴛᴏ ꜰᴇᴛᴄʜ ᴛʜᴇ ᴜꜱᴇʀ ɪᴅ.**\n\n🔒 **ᴛʜᴇ ᴜꜱᴇʀ ᴍᴀʏ ʜᴀᴠᴇ ᴀ ʜɪᴅᴅᴇɴ ᴘʀᴏꜰɪʟᴇ.**")
        
        # B. Bina reply ke sirf /id likha hai
        else:
            await message.reply_text(
                f"**›› ɢʀᴏᴜᴘ ɪᴅ** <code>{message.chat.id}</code>\n"
                f"**›› ʏᴏᴜʀ ɪᴅ*:** <code>{message.from_user.id}</code>"
            )

@Client.on_message(filters.command("dstats") & filters.user(ADMINS))
async def daily_stats_handler(client, message):
    # Aaj ki date
    today = datetime.now().strftime("%Y-%m-%d")
    # Kal ki date (Optional, dekhne ke liye ki kal kya scene tha)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    s_today = await get_stats_by_date(today) or {"links_generated": 0, "links_verified": 0}
    s_yesterday = await get_stats_by_date(yesterday) or {"links_generated": 0, "links_verified": 0}
    
    # Success Percentage nikalne ke liye
    def get_pc(gen, ver):
        if gen == 0: return 0
        return round((ver / gen) * 100, 2)

    text = (f"""
📅 **ᴅᴀɪʟʏ ᴛʀᴀꜰꜰɪᴄ ʀᴇᴘᴏʀᴛ**
**━━━━━━━━━━━━━━━━━━**
            
**☀️ ᴛᴏᴅᴀʏ ({today})**
**├ 🔗 ʟɪɴᴋꜱ ɢᴇɴᴇʀᴀᴛᴇᴅ**
**│  ››** `{s_today['links_generated']}`
**├ ✅ ʟɪɴᴋꜱ ᴠᴇʀɪꜰɪᴇᴅ**
**│  ››** `{s_today['links_verified']}`
**└ 📊 ꜱᴜᴄᴄᴇꜱꜱ ʀᴀᴛᴇ**
   **››** `{get_pc(s_today['links_generated'], s_today['links_verified'])}%`

**━━━━━━━━━━━━━━━━━━**
**🌙 ʏᴇꜱᴛᴇʀᴅᴀʏ ({yesterday})**
**├ 🔗 ʟɪɴᴋꜱ ɢᴇɴᴇʀᴀᴛᴇᴅ**
**│  ››** `{s_yesterday['links_generated']}`
**├ ✅ ʟɪɴᴋꜱ ᴠᴇʀɪꜰɪᴇᴅ**
**│  ››** `{s_yesterday['links_verified']}`
**└ 📊 ꜱᴜᴄᴄᴇꜱꜱ ʀᴀᴛᴇ**
   **››** `{get_pc(s_yesterday['links_generated'], s_yesterday['links_verified'])}%`
"""    )
    
    await message.reply_text(text)
