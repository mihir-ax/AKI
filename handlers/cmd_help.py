from pyrogram import Client, filters
from config import ADMINS

@Client.on_message(filters.command("commands"))
async def help_command_handler(client, message):
    user_id = message.from_user.id
    
    help_text = (
"""📜 **ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅꜱ & ᴜꜱᴀɢᴇ ɢᴜɪᴅᴇ**
**━━━━━━━━━━━━━━━━━━**

✨ **ᴜꜱᴇʀ ᴄᴏᴍᴍᴀɴᴅꜱ**
**├ `/start`** – ꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ.
**├ `/id`** – ɢᴇᴛ ʏᴏᴜʀ ᴜꜱᴇʀ ᴏʀ ɢʀᴏᴜᴘ ɪᴅ.
**├ `/id` (reply)** – ɢᴇᴛ ᴀɴᴏᴛʜᴇʀ ᴜꜱᴇʀ’ꜱ ɪᴅ.
**└ `search`** – ᴛʏᴘᴇ ᴀ ᴍᴏᴠɪᴇ ɴᴀᴍᴇ ᴅɪʀᴇᴄᴛʟʏ ᴛᴏ ɢᴇᴛ ʀᴇꜱᴜʟᴛꜱ ᴡɪᴛʜ ᴀɪ ᴄᴏʀʀᴇᴄᴛɪᴏɴ.
"""
    )

    if user_id in ADMINS:
        help_text += (
"""🛡️ **ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ**
**━━━━━━━━━━━━━━━━━━**

**├ `/index [StartLink] [EndLink]`** – ʙᴜʟᴋ ɪɴᴅᴇxɪɴɢ.
**├ `/stats`** – ᴠɪᴇᴡ ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ, ɢʀᴏᴜᴘꜱ, ᴀɴᴅ ᴅᴀᴛᴀʙᴀꜱᴇ ꜱᴛᴏʀᴀɢᴇ.
**├ `/dstats`** – ᴠɪᴇᴡ ᴅᴀɪʟʏ ᴛʀᴀꜰꜰɪᴄ ᴀɴᴅ ᴀɪ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ꜱᴛᴀᴛꜱ.
**├ `/ban [UserID] [Reason]`** – ʙᴀɴ ᴀ ᴜꜱᴇʀ ꜰʀᴏᴍ ᴜꜱɪɴɢ ᴛʜᴇ ʙᴏᴛ.
**└ `/unban [UserID]`** – ᴜɴʙᴀɴ ᴀ ᴘʀᴇᴠɪᴏᴜꜱʟʏ ʙᴀɴɴᴇᴅ ᴜꜱᴇʀ.

💡 **ᴛɪᴘ**
**››** ᴡʜɪʟᴇ ɪɴᴅᴇxɪɴɢ, ʟɪɴᴋ ᴏʀᴅᴇʀ ᴅᴏᴇꜱ ɴᴏᴛ ᴍᴀᴛᴛᴇʀ — ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴀᴅᴊᴜꜱᴛ ɪᴛ.

"""        )
    else:
        help_text += "📢 __ɴᴏᴛᴇ__\n**››** ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅꜱ ᴀʀᴇ ᴀᴠᴀɪʟᴀʙʟᴇ ᴏɴʟʏ ꜰᴏʀ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜꜱᴇʀꜱ."

    await message.reply_text(help_text)