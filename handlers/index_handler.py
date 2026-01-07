# --- handlers/index_handler.py ---

import asyncio
import re
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from config import ADMINS
from database.movies_db import movies  # DB Collection
from pymongo import UpdateOne
from utils.helpers import clean_file_name

@Client.on_message(filters.command("index") & filters.user(ADMINS))
async def bulk_index_handler(client: Client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text("❌ **Invalid Format!**\n\n📌 **Usage:** `/index START_LINK END_LINK`")
    
    def parse_link(link):
        pattern = r"t.me/(?:c/)?([^/]+)/(\d+)"
        match = re.search(pattern, link)
        if match:
            chat_id = match.group(1)
            msg_id = int(match.group(2))
            if chat_id.isdigit():
                chat_id = int("-100" + chat_id)
            return chat_id, msg_id
        return None, None
    
    # Extract start and end links
    s_chat, s_id = parse_link(message.command[1])
    e_chat, e_id = parse_link(message.command[2])
    
    if not s_id or not e_id or s_chat != e_chat:
        return await message.reply_text("⚠️ **Invalid Links Detected!**\n\nPlease provide valid Telegram message links.")
    
    start_time = time.time()
    status_msg = await message.reply_text("⚡ **Starting Lightning Indexer...**\n\n📊 Initializing data processing...")
    
    total_fetched = 0
    saved_count = 0
    duplicate_count = 0
    unsupported_count = 0
    current_id = s_id
    
    # Progress tracking variables
    last_processed_count = 0
    last_update_time = start_time
    
    while current_id <= e_id:
        batch_ids = list(range(current_id, min(current_id + 200, e_id + 1)))
        
        try:
            # Fetch messages in batch
            msgs = await client.get_messages(s_chat, batch_ids)
            
            # Batch duplicate checking optimization
            batch_filenames = []
            valid_msgs = []
            for msg in msgs:
                total_fetched += 1
                if not msg or msg.empty:
                    unsupported_count += 1
                    continue
                
                file = msg.video or (msg.document if msg.document and "video" in (msg.document.mime_type or "").lower() else None)
                if file:
                    batch_filenames.append(file.file_name or "Unknown_File")
                    valid_msgs.append((msg, file))
                else:
                    unsupported_count += 1
            
            # Check existing files in database
            existing_files = await movies.find({"file_name": {"$in": batch_filenames}}).to_list(length=len(batch_filenames))
            existing_names = {f["file_name"] for f in existing_files}
            
            bulk_ops = []
            for msg, file in valid_msgs:
                file_name = file.file_name or "Unknown_File"
                clean_name = clean_file_name(file_name)
                
                if file_name in existing_names:
                    duplicate_count += 1
                    continue
                
                bulk_ops.append(
                    UpdateOne(
                        {"file_name": file_name},  # Unique identifier
                        {
                            "$set": {
                                "file_id": file.file_id,
                                "file_size": file.file_size,
                                "chat_id": s_chat,
                                "message_id": msg.id,
                                "caption_name": clean_name,  # Clean name for display
                            }
                        },
                        upsert=True,
                    )
                )
                saved_count += 1
                existing_names.add(file_name)  # Prevent duplicates in current batch
            
            if bulk_ops:
                await movies.bulk_write(bulk_ops)
            
            # Progress update display
            if (total_fetched % 1000 == 0) or (current_id + 200 > e_id):
                current_time = time.time()
                elapsed_time = current_time - start_time
                elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                
                overall_speed = total_fetched / elapsed_time if elapsed_time > 0 else 0
                now = datetime.now().strftime("%d %b %Y, %I:%M %p")
                
                # Format the progress message
                progress_text = f"""
**⚡ 𝐋𝐈𝐆𝐇𝐓𝐍𝐈𝐍𝐆 𝐈𝐍𝐃𝐄𝐗𝐄𝐑 | 𝐈𝐍 𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒**
━━━━━━━━━━━━━━━━━━━━━━

📊 **𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠 𝐒𝐭𝐚𝐭𝐮𝐬**
├ 📥 **𝐓𝐨𝐭𝐚𝐥 𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐞𝐝:** `{total_fetched:,}`
├ ✅ **𝐒𝐚𝐯𝐞𝐝 𝐅𝐢𝐥𝐞𝐬:** `{saved_count:,}`
├ 🔄 **𝐃𝐮𝐩𝐥𝐢𝐜𝐚𝐭𝐞𝐬 𝐈𝐠𝐧𝐨𝐫𝐞𝐝:** `{duplicate_count:,}`
└ ❌ **𝐔𝐧𝐬𝐮𝐩𝐩𝐨𝐫𝐭𝐞𝐝:** `{unsupported_count:,}`

━━━━━━━━━━━━━━━━━━━━━━
📈 **𝐏𝐞𝐫𝐟𝐨𝐫𝐦𝐚𝐧𝐜𝐞 𝐌𝐞𝐭𝐫𝐢𝐜𝐬**
├ ⚡ **𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠 𝐒𝐩𝐞𝐞𝐝:** `{overall_speed:.2f} msgs/sec`
├ ⏱️ **𝐄𝐥𝐚𝐩𝐬𝐞𝐝 𝐓𝐢𝐦𝐞:** `{elapsed_str}`
└ 🕒 **𝐋𝐚𝐬𝐭 𝐔𝐩𝐝𝐚𝐭𝐞:** `{now}`
━━━━━━━━━━━━━━━━━━━━━━
"""
                try:
                    await status_msg.edit_text(progress_text)
                except Exception as e:
                    print(f"Update error: {e}")
            
            current_id += 200
            await asyncio.sleep(0.5)
        
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"❌ **Processing Error:** {e}")
            current_id += 200
    
    # Final completion report
    end_time = time.time()
    total_time = end_time - start_time
    
    # Format total time
    if total_time < 60:
        time_str = f"{total_time:.2f} seconds"
    elif total_time < 3600:
        minutes = int(total_time // 60)
        seconds = total_time % 60
        time_str = f"{minutes} minutes {seconds:.2f} seconds"
    else:
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = total_time % 60
        time_str = f"{hours} hours {minutes} minutes {seconds:.2f} seconds"
    
    speed = total_fetched / total_time if total_time > 0 else 0
    
    final_now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    
    # Success rate calculation
    success_rate = (saved_count / total_fetched * 100) if total_fetched > 0 else 0
    
    final_message = f"""
**🏁 𝐈𝐍𝐃𝐄𝐗𝐈𝐍𝐆 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄𝐃 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋𝐋𝐘!**
━━━━━━━━━━━━━━━━━━━━━━

📊 **𝐅𝐈𝐍𝐀𝐋 𝐒𝐓𝐀𝐓𝐈𝐒𝐓𝐈𝐂𝐒**
├ 📥 **𝐓𝐨𝐭𝐚𝐥 𝐌𝐞𝐬𝐬𝐚𝐠𝐞𝐬 𝐒𝐜𝐚𝐧𝐧𝐞𝐝:** `{total_fetched:,}`
├ ✅ **𝐍𝐞𝐰 𝐅𝐢𝐥𝐞𝐬 𝐀𝐝𝐝𝐞𝐝:** `{saved_count:,}`
├ 🔄 **𝐃𝐮𝐩𝐥𝐢𝐜𝐚𝐭𝐞𝐬 𝐒𝐤𝐢𝐩𝐩𝐞𝐝:** `{duplicate_count:,}`
└ ❌ **𝐔𝐧𝐬𝐮𝐩𝐩𝐨𝐫𝐭𝐞𝐝 𝐌𝐞𝐝𝐢𝐚:** `{unsupported_count:,}`

📈 **𝐏𝐄𝐑𝐅𝐎𝐑𝐌𝐀𝐍𝐂𝐄 𝐑𝐄𝐏𝐎𝐑𝐓**
├ 🎯 **𝐒𝐮𝐜𝐜𝐞𝐬𝐬 𝐑𝐚𝐭𝐞:** `{success_rate:.2f}%`
├ ⏱️ **𝐓𝐨𝐭𝐚𝐥 𝐓𝐢𝐦𝐞 𝐓𝐚𝐤𝐞𝐧:** `{time_str}`
├ ⚡ **𝐀𝐯𝐞𝐫𝐚𝐠𝐞 𝐒𝐩𝐞𝐞𝐝:** `{speed:.2f} msgs/sec`
└ 📅 **𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞𝐝 𝐎𝐧:** `{final_now}`
━━━━━━━━━━━━━━━━━━━━━━

✨ **Database has been successfully updated!**
"""
    
    await status_msg.edit_text(final_message)