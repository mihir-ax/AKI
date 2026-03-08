from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, API  # API import kiya
import logging
from database.movies_db import create_indexes
from aiohttp import web
import aiohttp
import asyncio

# Basic logging
logging.basicConfig(level=logging.INFO)

async def health_check(request):
    return web.Response(text="MovieBot is Alive!")

# --- PINGER TASK ---
async def ping_other_bot():
    """Ye function har 20 sec me dusre bot ko ping karega"""
    if not API:
        print("⚠️ API URL set nahi hai. Pinger start nahi hua.")
        return
        
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API) as response:
                    print(f"🔄 Pinged {API} - Status: {response.status}")
        except Exception as e:
            print(f"❌ Ping failed: {e}")
            
        await asyncio.sleep(20) # 20 second ka sleep
# -------------------

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
        site = web.TCPSite(runner, "0.0.0.0", 8000)
        await site.start()
        print("🌐 Health Check Server started on port 8000")

        # --- PINGER START KARO ---
        asyncio.create_task(ping_other_bot())

    async def stop(self, *args):
        await super().stop()
        print("👋 Bot Stopped!")

if __name__ == "__main__":
    Bot().run()
