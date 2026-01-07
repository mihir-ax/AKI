from pyrogram import Client, filters
from config import ADMINS

@Client.on_message(filters.command("commands"))
async def help_command_handler(client, message):
    user_id = message.from_user.id
    
    help_text = """**📖 𝐁𝐎𝐓 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 & 𝐆𝐔𝐈𝐃𝐄**
━━━━━━━━━━━━━━━━━━━━━━

✨ **𝐔𝐒𝐄𝐑 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒**
├ 🚀 **/start** – Start the bot & get welcome message
├ 🆔 **/id** – Get your user ID
├ 🆔 **/id** (reply) – Get another user's ID
└ 🔍 **Search** – Just type any movie/series name

🎯 **𝐇𝐎𝐖 𝐓𝐎 𝐒𝐄𝐀𝐑𝐂𝐇:**
• Type any movie or series name
• Use filters for better results
• AI will auto-correct spelling mistakes
"""
    
    if user_id in ADMINS:
        help_text += """
🛡️ **𝐀𝐃𝐌𝐈𝐍 𝐂𝐎𝐍𝐓𝐑𝐎𝐋 𝐏𝐀𝐍𝐄𝐋**
━━━━━━━━━━━━━━━━━━━━━━

📊 **𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞 𝐌𝐚𝐧𝐚𝐠𝐞𝐦𝐞𝐧𝐭:**
├ ⚡ **/index** [StartLink] [EndLink] – Bulk indexing
├ 📈 **/stats** – View total users, groups & storage
├ 📊 **/dstats** – Daily traffic & verification stats
└ 🔄 **/broadcast** – Send message to all users

👥 **𝐔𝐬𝐞𝐫 𝐌𝐚𝐧𝐚𝐠𝐞𝐦𝐞𝐧𝐭:**
├ ⛔ **/ban** [UserID] [Reason] – Restrict user access
├ ✅ **/unban** [UserID] – Restore user access
├ 👀 **/users** – List all registered users
└ 📋 **/logs** – View system logs

⚙️ **𝐒𝐲𝐬𝐭𝐞𝐦 𝐂𝐨𝐧𝐭𝐫𝐨𝐥:**
├ 🔧 **/settings** – Bot configuration
├ 📤 **/export** – Export database backup
└ 🚫 **/maintenance** – Enable/disable maintenance mode

💡 **𝐏𝐑𝐎 𝐓𝐈𝐏𝐒:**
• Indexing link order doesn't matter
• Use batch processing for large channels
• Monitor stats regularly for insights
"""
    else:
        help_text += """
🔒 **𝐍𝐎𝐓𝐄:**
• Admin commands are restricted
• Contact support for assistance
• Regular updates ensure best experience

━━━━━━━━━━━━━━━━━━━━━━
📞 **𝐒𝐔𝐏𝐏𝐎𝐑𝐓:**
• Report issues via /support
• Feature requests welcome
• Community-driven updates
"""

    await message.reply_text(
        help_text,
        disable_web_page_preview=True
    )