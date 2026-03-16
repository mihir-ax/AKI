from pyrogram import Client, compose
from config import API_ID, API_HASH, BOT_TOKENS, API
import logging
from database.movies_db import create_indexes
from aiohttp import web
import aiohttp
import asyncio

# Basic logging
logging.basicConfig(level=logging.INFO)

async def health_check(request):
    return web.Response(text="MovieBots are Alive!")

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
                    pass
        except Exception:
            pass
        await asyncio.sleep(20) # 20 second ka sleep
# -------------------

async def main():
    # 1. Database Indexes
    await create_indexes()

    print("🚀 Starting Database...")
    print("""
███╗   ███╗ ███████╗ ██╗   ██╗
████╗ ████║ ██╔════╝ ██║   ██║
██╔████╔██║ ███████╗ ██║   ██║
██║╚██╔╝██║ ╚════██║ ╚██╗ ██╔╝
██║ ╚═╝ ██║ ███████║  ╚████╔╝
╚═╝     ╚═╝ ╚══════╝   ╚═══╝
""")

    # 2. DUMMY SERVER START
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    print("🌐 Health Check Server started on port 8000")

    # 3. PINGER START
    asyncio.create_task(ping_other_bot())

    # 4. START MULTIPLE BOTS
    clients = []
    if not BOT_TOKENS:
        print("❌ No Bot Tokens found in config (.env)!")
        return

    for i, token in enumerate(BOT_TOKENS):
        client = Client(
            name=f"MovieBot_{i+1}", # Is naam se MovieBot_1.session banegi
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=token,
            plugins=dict(root="handlers")
        )
        clients.append(client)
        print(f"🤖 Bot {i+1} Ready & Armed!")

    print("🚀 All Bots Started Successfully!")

    # Ye saare bots ko ek saath run karega
    await compose(clients)

if __name__ == "__main__":
    asyncio.run(main())
