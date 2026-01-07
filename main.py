from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN
import logging
from database.movies_db import create_indexes # Import karo
from aiohttp import web # Dummy server ke liye
import asyncio

# Basic logging
logging.basicConfig(level=logging.INFO)

async def health_check(request):
    return web.Response(text="Bot is Alive!")

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="MovieBot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="handlers")
        )

    async def start(self):
        await super().start()
        await create_indexes()
        print("🚀 Bot Started!")
        print("""
███╗   ███╗ ███████╗ ██╗   ██╗
████╗ ████║ ██╔════╝ ██║   ██║
██╔████╔██║ ███████╗ ██║   ██║
██║╚██╔╝██║ ╚════██║ ╚██╗ ██╔╝
██║ ╚═╝ ██║ ███████║  ╚████╔╝ 
╚═╝     ╚═╝ ╚══════╝   ╚═══╝  
""")
        
        # --- DUMMY SERVER START ---
        app = web.Application()
        app.router.add_get("/", health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8000) # Koyeb/Replit port 8000 check karta hai
        await site.start()
        print("🌐 Health Check Server started on port 8000")

    async def stop(self, *args):
        await super().stop()
        print("👋 Bot Stopped!")

if __name__ == "__main__":
    Bot().run()