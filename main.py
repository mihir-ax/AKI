import os
import asyncio
import time
import logging
from aiohttp import web
import aiohttp
from pyrogram import Client, idle

# Import configuration
from config import (
    API_ID,
    API_HASH,
    BOT_TOKENS,
    TARGET_BOTS,
    ALERIFY_URL,
    START_TIME,
)

from database.movies_db import create_indexes  

# Basic logging
logging.basicConfig(level=logging.INFO)

# -------------------------------------------------------------------
# Web Server – Health Check (Render / Koyeb ke liye)
# -------------------------------------------------------------------
async def health_check(request):
    return web.Response(text="MovieBots are Alive! 🚀")

# -------------------------------------------------------------------
# Alerify Alert Sender
# -------------------------------------------------------------------
async def send_alerify_alert(subject: str, tg_msg: str, email_msg: str):
    payload = {
        "subject": subject,
        "tg_html_message": tg_msg,
        "email_html_message": email_msg
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ALERIFY_URL, json=payload, timeout=15) as resp:
                if resp.status == 200:
                    print(f"✅ Alert Sent via Alerify: {subject}")
                else:
                    print(f"⚠️ Alerify API Failed with status {resp.status}")
    except Exception as e:
        print(f"❌ Failed to connect to Alerify API: {e}")

# -------------------------------------------------------------------
# Startup Alert (new bots ke liye)
# -------------------------------------------------------------------
async def send_startup_alert(clients):
    if not clients:
        return

    bot_names = []
    for client in clients:
        try:
            me = client.me
            if me:
                name = me.mention if hasattr(me, 'mention') else f"@{me.username}" if me.username else me.first_name
                bot_names.append(name)
        except Exception as e:
            print(f"⚠️ Could not get info for a bot: {e}")

    if bot_names:
        subject = "🚀 Bots Started Successfully"
        tg_msg = "<b>🤖 Bots are now online!</b>\n\n"
        for name in bot_names:
            tg_msg += f"• {name}\n"
        email_msg = f"<h2>Bots Started</h2><p>{', '.join(bot_names)}</p>"
        await send_alerify_alert(subject, tg_msg, email_msg)

# -------------------------------------------------------------------
# URL Checker Helper (for Pinger)
# -------------------------------------------------------------------
async def check_url(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            return url, response.status == 200
    except Exception:
        return url, False

# -------------------------------------------------------------------
# Pinger Task (monitors TARGET_BOTS)
# -------------------------------------------------------------------
async def ping_other_bot():
    if not TARGET_BOTS:
        print("⚠️ TARGET_BOTS empty hai. Pinger start nahi hua.")
        return

    print(f"🔄 Advanced Pinger started for {len(TARGET_BOTS)} Bots...")
    bot_states = {url: True for url in TARGET_BOTS.keys()}
    last_hourly_report_time = time.time()

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                tasks = [check_url(session, url) for url in TARGET_BOTS.keys()]
                results = await asyncio.gather(*tasks)

                for url, is_up in results:
                    bot_name = TARGET_BOTS[url]
                    was_up = bot_states[url]

                    if not is_up and was_up:
                        bot_states[url] = False
                        subject = f"🚨 URGENT: {bot_name} is DOWN!"
                        tg_msg = f"<b>🚨 Bot Down Alert!</b>\n\n❌ <b>{bot_name}</b> respond nahi kar raha.\n🔗 URL: {url}\n⏳ Status: <b>DOWN</b>"
                        email_msg = f"<h2>Bot Down Alert</h2><p><b>{bot_name}</b> is offline.</p><p>URL: <a href='{url}'>{url}</a></p>"
                        await send_alerify_alert(subject, tg_msg, email_msg)

                    elif is_up and not was_up:
                        bot_states[url] = True
                        subject = f"✅ RECOVERED: {bot_name} is UP!"
                        tg_msg = f"<b>✅ Bot Recovery Alert!</b>\n\n✅ <b>{bot_name}</b> wapas online aa gaya!\n🔗 URL: {url}\n⏳ Status: <b>UP</b>"
                        email_msg = f"<h2>Bot Recovery</h2><p><b>{bot_name}</b> is back online.</p><p>URL: <a href='{url}'>{url}</a></p>"
                        await send_alerify_alert(subject, tg_msg, email_msg)

            current_time = time.time()
            if current_time - last_hourly_report_time >= 3600:
                last_hourly_report_time = current_time

                report_tg = "<b>📊 Hourly Bot Status Report</b>\n\n"
                report_email = "<h2>Hourly Bot Status Report 📊</h2><ul>"
                all_good = True

                for url, state in bot_states.items():
                    b_name = TARGET_BOTS[url]
                    status_icon = "🟢 UP" if state else "🔴 DOWN"
                    if not state:
                        all_good = False
                    report_tg += f"• {b_name}: <b>{status_icon}</b>\n"
                    report_email += f"<li>{b_name}: {status_icon}</li>"

                report_email += "</ul>"
                subject = "🟢 All Systems Nominal" if all_good else "⚠️ System Status Report (Issues Detected)"
                
                await send_alerify_alert(subject, report_tg, report_email)
                print("🕐 Hourly Report sent to Alerify.")

        except Exception as e:
            print(f"❌ Pinger Core Error: {e}")

        await asyncio.sleep(20)

# -------------------------------------------------------------------
# Main Function
# -------------------------------------------------------------------
async def main():
    print("🚀 Starting Movie Bots...")

    print("🛠️ Initializing Database Optimized Indexes...")
    await create_indexes()

    # 1. Create Pyrogram clients from BOT_TOKENS
    if not BOT_TOKENS:
        print("❌ No BOT_TOKENS provided. Exiting.")
        return

    clients = []
    for idx, token in enumerate(BOT_TOKENS, start=1):
        client = Client(
            name=f"MovieBot_{idx}",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=token,
            plugins=dict(root="handlers")
        )
        clients.append(client)
        print(f"🤖 Bot {idx} configured with plugins.")

    # 2. Start web server
    web_app = web.Application()
    web_app.router.add_get("/", health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Health Check Server running on port {port}")

    # 3. Start all bots
    print("🔄 Starting all bots...")
    try:
        await asyncio.gather(*(client.start() for client in clients))
        print("✅ All bots started successfully.")
    except Exception as e:
        print(f"❌ Error starting bots: {e}")

    # 4. Send startup alert
    await send_startup_alert(clients)

    # 5. Start Pinger background task
    asyncio.create_task(ping_other_bot())
    print("🔄 Pinger background task started.")

    # 6. Keep running until interrupted
    await idle()

    # 7. Cleanup on shutdown
    print("🛑 Shutting down gracefully...")
    for client in clients:
        try:
            await client.stop()
        except:
            pass
    await runner.cleanup()
    print("✅ Cleanup done. Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())
