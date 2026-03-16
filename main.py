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

# --- PINGER TASK (UPDATED FOR MULTIPLE URLs) ---
async def ping_other_bot():
    """Ye function har 20 sec me saari URLs ko ek sath ping karega"""
    if not API:
        print("⚠️ API URLs set nahi hain. Pinger start nahi hua.")
        return

    # String ko comma se split karke list bana lo, aur extra spaces hata do
    urls = [url.strip() for url in API.split(",") if url.strip()]
    
    if not urls:
        print("⚠️ Koi valid URL nahi mili.")
        return

    print(f"🔄 Pinger started for {len(urls)} URLs: {urls}")

    while True:
        try:
            # Ek hi session mein saari requests bhejenge (Fast & Efficient)
            async with aiohttp.ClientSession() as session:
                tasks = []
                for url in urls:
                    # Har url ke liye ek GET request task banao
                    tasks.append(session.get(url))
                
                # asyncio.gather saari URLs ko ek hi time pe ping karega
                # return_exceptions=True ka matlab agar ek fail hui toh dusri rukegi nahi
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            # Agar session banane me koi error aaye
            print(f"Pinger Error: {e}")
            
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
