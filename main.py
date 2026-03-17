from pyrogram import Client, compose
import logging
from aiohttp import web
import aiohttp
import asyncio
import time
from config import TARGET_BOTS, ALERIFY_URL

# Basic logging
logging.basicConfig(level=logging.INFO)

# DEMO IMPORTS (Apne hisaab se adjust kar lena)
# from config import API_ID, API_HASH, BOT_TOKENS, TARGET_BOTS, ALERIFY_URL
# from database.movies_db import create_indexes

async def health_check(request):
    return web.Response(text="MovieBots are Alive!")

# --- ALERIFY SENDER HELPER ---
async def send_alerify_alert(subject: str, tg_msg: str, email_msg: str):
    """Ye function asynchronously tere Alerify API ko hit karega"""
    payload = {
        "subject": subject,
        "tg_html_message": tg_msg,
        "email_html_message": email_msg
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ALERIFY_URL, json=payload) as resp:
                if resp.status == 200:
                    print(f"✅ Alert Sent: {subject}")
                else:
                    print(f"⚠️ Alerify API Failed with status {resp.status}")
    except Exception as e:
        print(f"❌ Failed to connect to Alerify API: {e}")

# --- URL CHECKER HELPER ---
async def check_url(session, url):
    """Ek single URL ko check karega aur status return karega"""
    try:
        async with session.get(url, timeout=10) as response:
            return url, response.status == 200
    except Exception:
        return url, False


# --- ADVANCED PINGER TASK ---
async def ping_other_bot():
    """Har 20 sec me bots ping karega, fail hone pe alert dega aur 1hr me report bhejega"""
    if not TARGET_BOTS:
        print("⚠️ TARGET_BOTS dictionary khali hai. Pinger start nahi hua.")
        return

    print(f"🔄 Advanced Pinger started for {len(TARGET_BOTS)} Bots...")

    # Dictionary to track state (True = UP, False = DOWN) 
    # Taki har 20 sec me spam na ho
    bot_states = {url: True for url in TARGET_BOTS.keys()}
    
    last_hourly_report_time = time.time()

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Saari URLs ke liye tasks banao
                tasks = [check_url(session, url) for url in TARGET_BOTS.keys()]
                
                # 2. Ek saath sabko ping karo
                results = await asyncio.gather(*tasks)

                # 3. Results check karo
                for url, is_up in results:
                    bot_name = TARGET_BOTS[url]
                    was_up = bot_states[url]

                    if not is_up and was_up:
                        # BOT JUST WENT DOWN 🚨
                        bot_states[url] = False
                        subject = f"🚨 URGENT: {bot_name} is DOWN!"
                        tg_msg = f"<b>Bot Alert!</b>\n\n❌ <b>{bot_name}</b> respond nahi kar raha hai.\n🔗 URL: {url}\n⏳ Status: <b>DOWN</b>"
                        email_msg = f"<h2>Bot Down Alert</h2><p><b>{bot_name}</b> is currently offline.</p><p>URL: {url}</p>"
                        
                        await send_alerify_alert(subject, tg_msg, email_msg)

                    elif is_up and not was_up:
                        # BOT JUST RECOVERED ✅
                        bot_states[url] = True
                        subject = f"✅ RECOVERED: {bot_name} is UP!"
                        tg_msg = f"<b>Bot Recovery</b>\n\n✅ <b>{bot_name}</b> wapas online aa gaya hai!\n🔗 URL: {url}\n⏳ Status: <b>UP</b>"
                        email_msg = f"<h2>Bot Recovery</h2><p><b>{bot_name}</b> is back online.</p><p>URL: {url}</p>"
                        
                        await send_alerify_alert(subject, tg_msg, email_msg)

            # 4. HOURLY REPORT CHECK (1 hour = 3600 seconds)
            current_time = time.time()
            if current_time - last_hourly_report_time >= 3600:
                last_hourly_report_time = current_time
                
                # Report Generate karo
                report_tg = "<b>Hourly Bot Status Report 📊</b>\n\n"
                report_email = "<h2>Hourly Bot Status Report 📊</h2><ul>"
                
                all_good = True
                for url, state in bot_states.items():
                    b_name = TARGET_BOTS[url]
                    status_icon = "🟢 UP" if state else "🔴 DOWN"
                    if not state: all_good = False
                    
                    report_tg += f"• {b_name}: <b>{status_icon}</b>\n"
                    report_email += f"<li>{b_name}: {status_icon}</li>"
                
                report_email += "</ul>"
                subject = "🟢 All Systems Nominal" if all_good else "⚠️ System Status Report (Issues Detected)"
                
                await send_alerify_alert(subject, report_tg, report_email)

        except Exception as e:
            print(f"Pinger Core Error: {e}")
            
        await asyncio.sleep(20) # 20 second ka sleep
# -------------------

async def main():
    print("🚀 Starting Setup...")
    
    # 1. Start Telegram Client (TUNE YE MISS KIYA THA)
    # await app.start()  <-- Isko uncomment kar agar 'app' define kiya hai
    # print("✅ Telegram Bot Started!")

    # 2. Start Web Server
    web_app = web.Application()
    web_app.router.add_get("/", health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    # Koyeb/Render port handle karne ke liye
    import os
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Health Check Server started on port {port}")

    # 3. PINGER START
    asyncio.create_task(ping_other_bot())
    print("🔄 Pinger Background Task Started!")

    try:
        # 4. Yahan pyrogram.idle() use karna hai instead of sleep(3600)
        from pyrogram import idle
        await idle()
    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        print("🛑 Shutting down...")
        # await app.stop() <-- Isko uncomment kar
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
