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
        return await message.reply_text("❌ `/index START_LINK END_LINK`")

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

    s_chat, s_id = parse_link(message.command[1])
    e_chat, e_id = parse_link(message.command[2])

    if not s_id or not e_id or s_chat != e_chat:
        return await message.reply_text("❌ Invalid Links!")

    start_time = time.time()
    status_msg = await message.reply_text("🚀 **Initializing Lightning Indexer...**")

    total_fetched = 0
    saved_count = 0
    duplicate_count = 0
    unsupported_count = 0
    current_id = s_id
    
    last_processed_count = 0
    last_update_time = start_time

    while current_id <= e_id:
        batch_ids = list(range(current_id, min(current_id + 200, e_id + 1)))

        try:
            msgs = await client.get_messages(s_chat, batch_ids)
            
            # --- FASTER DUPLICATE CHECK: Batch se saare filenames nikal lo ---
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

            # DB se ek baar mein check karo kaunse names already hain
            existing_files = await movies.find({"file_name": {"$in": batch_filenames}}).to_list(length=len(batch_filenames))
            existing_names = {f["file_name"] for f in existing_files}

            bulk_ops = []
            for msg, file in valid_msgs:
                file_name = file.file_name or "Unknown_File"
                clean_name = clean_file_name(file_name) 
                
                bulk_ops.append(
                    UpdateOne(
                        {"file_name": file_name}, # Original name unique key rahega
                        {
                            "$set": {
                                "file_id": file.file_id,
                                "file_size": file.file_size,
                                "chat_id": s_chat,
                                "message_id": msg.id,
                                "caption_name": clean_name, # Display ke liye saaf naam
                            }
                        },
                        upsert=True,
                    )
                )
                saved_count += 1
                existing_names.add(file_name) # Batch ke andar duplicate rokne ke liye

            if bulk_ops:
                await movies.bulk_write(bulk_ops)

            # --- STATUS UPDATE LOGIC (Same as yours, keeping it clean) ---
            if (total_fetched % 1000 == 0) or (current_id + 200 > e_id):
                current_time = time.time()
                elapsed_time = current_time - start_time
                elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                
                overall_speed = total_fetched / elapsed_time if elapsed_time > 0 else 0
                now = datetime.now().strftime("%d %b %Y, %I:%M %p")
                
                progress_text = (
                    "⚡ **Lightning Indexing in Progress...**\n"
                    "------------------------------------\n"
                    f"📂 **Total Processed:** `{total_fetched}`\n"
                    f"✅ **Saved (Secret On):** `{saved_count}`\n"
                    f"🚫 **Duplicates:** `{duplicate_count}`\n"
                    f"❌ **Unsupported:** `{unsupported_count}`\n"
                    "------------------------------------\n"
                    f"⚡ **Avg Speed:** `{overall_speed:.2f} msgs/sec`\n"
                    f"⏱️ **Elapsed:** `{elapsed_str}`\n"
                    f"🕒 **Updated:** `{now}`"
                )
                try: await status_msg.edit_text(progress_text)
                except: pass

            current_id += 200
            await asyncio.sleep(0.5)

        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Error: {e}")
            current_id += 200

    # --- FINAL REPORT ---
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
    final_message = (
        "🏁 **Indexing Task Completed!**\n\n"
        f"📊 **Final Statistics:**\n"
        f"● Total Fetched: `{total_fetched}`\n"
        f"● New Files Saved: `{saved_count}`\n"
        f"● Duplicates Ignored: `{duplicate_count}`\n"
        f"● Unsupported Media: `{unsupported_count}`\n"
    )
    
    if total_fetched > 0:
        final_message += f"● Success Rate: `{(saved_count / total_fetched * 100):.2f}%`\n\n"
    else:
        final_message += f"● Success Rate: `N/A`\n\n"
    
    final_message += (
        f"⏱️ **Time Taken:** `{time_str}`\n"
        f"⚡ **Processing Speed:** `{speed:.2f} msgs/sec`\n\n"
        f"📅 **Completed at:** `{final_now}`"
    )
    
    await status_msg.edit_text(final_message)