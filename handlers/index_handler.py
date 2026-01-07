# --- handlers/index_handler.py ---

import asyncio
import re
import time
import pytz
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from config import ADMINS
from database.movies_db import movies  # DB Collection
from pymongo import UpdateOne
from utils.helpers import clean_file_name

# Timezone setup
IST = pytz.timezone('Asia/Kolkata')

# Global variable to track indexing process
INDEXING_ACTIVE = False

@Client.on_message(filters.command("cancel") & filters.user(ADMINS))
async def cancel_indexing(client: Client, message: Message):
    global INDEXING_ACTIVE
    if INDEXING_ACTIVE:
        INDEXING_ACTIVE = False
        await message.reply_text("⏹️ **Indexing cancelled successfully!**")
    else:
        await message.reply_text("ℹ️ **No active indexing process to cancel.**")

@Client.on_message(filters.command("index") & filters.user(ADMINS))
async def bulk_index_handler(client: Client, message: Message):
    global INDEXING_ACTIVE
    
    if INDEXING_ACTIVE:
        return await message.reply_text("⚠️ **Indexing already in progress!**\nUse `/cancel` to stop current process.")
    
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
    
    # Start indexing
    INDEXING_ACTIVE = True
    
    start_time = time.time()
    start_datetime = datetime.now(IST)
    status_msg = await message.reply_text("⚡ **Starting Lightning Indexer...**\n\n📊 Initializing data processing...")
    
    total_fetched = 0
    saved_count = 0
    duplicate_count = 0
    unsupported_count = 0
    current_id = s_id
    
    # Store initial time for ETA calculation
    last_eta_update_time = start_time
    last_eta_processed = 0
    
    try:
        while current_id <= e_id and INDEXING_ACTIVE:
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
                
                # Calculate ETA every 1000 messages or at the end
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Update ETA calculation more frequently for better accuracy
                eta_update_interval = 500  # Update ETA every 500 messages
                if (total_fetched % eta_update_interval == 0) or (current_id + 200 > e_id):
                    # Calculate processing speed (messages per second)
                    if elapsed_time > 0:
                        processing_speed = total_fetched / elapsed_time
                        
                        # Calculate remaining messages
                        total_messages = e_id - s_id + 1
                        processed_messages = current_id - s_id
                        remaining_messages = total_messages - processed_messages
                        
                        # Calculate ETA in seconds
                        if processing_speed > 0:
                            eta_seconds = remaining_messages / processing_speed
                            
                            # Format ETA
                            if eta_seconds < 60:
                                eta_str = f"{eta_seconds:.0f} seconds"
                            elif eta_seconds < 3600:
                                eta_minutes = eta_seconds / 60
                                eta_str = f"{eta_minutes:.1f} minutes"
                            elif eta_seconds < 86400:
                                eta_hours = eta_seconds / 3600
                                eta_str = f"{eta_hours:.1f} hours"
                            else:
                                eta_days = eta_seconds / 86400
                                eta_str = f"{eta_days:.1f} days"
                            
                            # Calculate predicted completion datetime (in IST)
                            predicted_completion = datetime.now(IST) + timedelta(seconds=eta_seconds)
                            predicted_str = predicted_completion.strftime("%d %b %Y, %I:%M %p")
                        else:
                            eta_str = "Calculating..."
                            predicted_str = "Calculating..."
                    else:
                        processing_speed = 0
                        eta_str = "Calculating..."
                        predicted_str = "Calculating..."
                
                # Progress update display
                if (total_fetched % 1000 == 0) or (current_id + 200 > e_id):
                    elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                    
                    # Get current datetime in IST
                    now = datetime.now(IST)
                    current_datetime_str = now.strftime("%d %b %Y, %I:%M %p")
                    
                    # Calculate progress percentage
                    total_range = e_id - s_id + 1
                    progress_percent = min(100, (current_id - s_id) / total_range * 100) if total_range > 0 else 0
                    
                    # Format the progress message
                    progress_text = f"""
**⚡ 𝐋𝐈𝐆𝐇𝐓𝐍𝐈𝐍𝐆 𝐈𝐍𝐃𝐄𝐗𝐄𝐑 — 𝐈𝐍 𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒**
**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**

📊 **𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 𝐒𝐓𝐀𝐓𝐔𝐒**
**›› Current ID           :** `{current_id} - {current_id + 200}`
**›› Total Processed      :** `{total_fetched:,}`
**›› Saved Files          :** `{saved_count:,}`
**›› Duplicates           :** `{duplicate_count:,}`
**›› Unsupported          :** `{unsupported_count:,}`

**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**
📈 **𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 𝐃𝐄𝐓𝐀𝐈𝐋𝐒**
**›› Progress             :** `{progress_percent:.1f}%`
**›› Range                :** `{s_id} → {e_id}`
**›› Remaining            :** `{max(0, e_id - current_id):,}`

**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**
⏰ **𝐓𝐈𝐌𝐄 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐓𝐈𝐎𝐍**
**›› Started At           :** `{start_datetime.strftime('%d %b %Y, %I:%M %p')}`
**›› Current Time         :** `{current_datetime_str}`
**›› Elapsed              :** `{elapsed_str}`
**›› ETA                  :** `{eta_str}`
**›› Completion           :** `{predicted_str}`

**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**
⚙️ **𝐏𝐄𝐑𝐅𝐎𝐑𝐌𝐀𝐍𝐂𝐄**
**›› Speed                :** `{processing_speed:.2f} msgs/sec`
**›› Command              : /cancel**
**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**
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
        
        if not INDEXING_ACTIVE:
            end_time = time.time()
            total_time = end_time - start_time
            end_datetime = datetime.now(IST)
            
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
            
            cancel_message = f"""
**⏹️ 𝐈𝐍𝐃𝐄𝐗𝐈𝐍𝐆 𝐂𝐀𝐍𝐂𝐄𝐋𝐋𝐄𝐃 𝐁𝐘 𝐔𝐒𝐄𝐑**
**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**

📊 **𝐏𝐀𝐑𝐓𝐈𝐀𝐋 𝐒𝐓𝐀𝐓𝐈𝐒𝐓𝐈𝐂𝐒**
**›› Last Message ID       :** `{current_id}`
**›› Total Scanned        :** `{total_fetched:,}`
**›› New Files Added      :** `{saved_count:,}`
**›› Duplicates Skipped   :** `{duplicate_count:,}`
**›› Unsupported Media    :** `{unsupported_count:,}`

⏰ **𝐓𝐈𝐌𝐄 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐓𝐈𝐎𝐍**
**›› Start Time           :** `{start_datetime.strftime('%d %b %Y, %I:%M %p')}`
**›› Stop Time            :** `{end_datetime.strftime('%d %b %Y, %I:%M %p')}`
**›› Total Time Taken     :** `{time_str}`
**›› Duration             :** `{str(end_datetime - start_datetime).split('.')[0]}`

**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**
ℹ️ Indexing stopped by user command."""
            await status_msg.edit_text(cancel_message)
            return
        
        # Final completion report
        end_time = time.time()
        total_time = end_time - start_time
        end_datetime = datetime.now(IST)
        
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
        
        final_now = datetime.now(IST).strftime("%d %b %Y, %I:%M %p")
        
        # Success rate calculation
        success_rate = (saved_count / total_fetched * 100) if total_fetched > 0 else 0
        
        final_message = f"""
**🏁 𝐈𝐍𝐃𝐄𝐗𝐈𝐍𝐆 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄𝐃 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋𝐋𝐘!**
**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**

📊 **𝐅𝐈𝐍𝐀𝐋 𝐒𝐓𝐀𝐓𝐈𝐒𝐓𝐈𝐂𝐒**
**›› Total Scanned        :** `{total_fetched:,}`
**›› New Files Added      :** `{saved_count:,}`
**›› Duplicates Skipped   :** `{duplicate_count:,}`
**›› Unsupported Media    :** `{unsupported_count:,}`

⏰ **𝐓𝐈𝐌𝐄 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐓𝐈𝐎𝐍**
**›› Start Time           :** `{start_datetime.strftime('%d %b %Y, %I:%M %p')}`
**›› End Time             :** `{end_datetime.strftime('%d %b %Y, %I:%M %p')}`
**›› Total Time Taken     :** `{time_str}`
**›› Duration             :** `{str(end_datetime - start_datetime).split('.')[0]}`

📈 **𝐏𝐄𝐑𝐅𝐎𝐑𝐌𝐀𝐍𝐂𝐄 𝐑𝐄𝐏𝐎𝐑𝐓**
**›› Success Rate         :** `{success_rate:.2f}%`
**›› Average Speed        :** `{speed:.2f} msgs/sec`
**›› Completed On         :** `{final_now}`

**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**
✨ Database has been successfully updated!"""
        
        await status_msg.edit_text(final_message)
    
    finally:
        # Reset indexing flag
        INDEXING_ACTIVE = False