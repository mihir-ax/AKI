from pyrogram import Client, filters, compose
import logging
from aiohttp import web
import aiohttp
import asyncio
import time
import os

# --- Configuration from environment ---
API_ID = int(os.getenv("API_ID", "0"))           # Your API ID from my.telegram.org
API_HASH = os.getenv("API_HASH", "")             # Your API Hash
BOT_TOKEN_ENV = os.getenv("BOT_TOKENS", "")      # Comma separated tokens, e.g. "token1,token2"
BOT_TOKENS = [t.strip() for t in BOT_TOKEN_ENV.split(",") if t.strip()]

# URLs of bots to monitor (for pinger)
TARGET_BOTS = {
    "https://auto-caption-bot-qfz4.onrender.com": "CAPTION BOT",
    "https://rook-gh81.onrender.com": "RoOk BOT"
}
ALERIFY_URL = os.getenv("ALERIFY_URL", "https://rapid-x-chi.vercel.app/send")

# Basic logging
logging.basicConfig(level=logging.INFO)

# --- Helper Functions (Alerify and Pinger) ---
async def send_alerify_alert(subject: str, tg_msg: str, email_msg: str):
    """Alerify API ko alert bhejta hai"""
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

async def check_url(session, url):
    """URL ko ping karta hai aur status return karta hai"""
    try:
        async with session.get(url, timeout=10) as response:
            return url, response.status == 200
    except Exception:
        return url, False

async def ping_other_bot():
    """Har 20 sec me bots ping karega, fail hone pe alert aur hourly report"""
    if not TARGET_BOTS:
        print("⚠️ TARGET_BOTS dictionary khali hai. Pinger start nahi hua.")
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
                        tg_msg = f"<b>Bot Alert!</b>\n\n❌ <b>{bot_name}</b> respond nahi kar raha hai.\n🔗 URL: {url}\n⏳ Status: <b>DOWN</b>"
                        email_msg = f"<h2>Bot Down Alert</h2><p><b>{bot_name}</b> is currently offline.</p><p>URL: {url}</p>"
                        await send_alerify_alert(subject, tg_msg, email_msg)
                    elif is_up and not was_up:
                        bot_states[url] = True
                        subject = f"✅ RECOVERED: {bot_name} is UP!"
                        tg_msg = f"<b>Bot Recovery</b>\n\n✅ <b>{bot_name}</b> wapas online aa gaya hai!\n🔗 URL: {url}\n⏳ Status: <b>UP</b>"
                        email_msg = f"<h2>Bot Recovery</h2><p><b>{bot_name}</b> is back online.</p><p>URL: {url}</p>"
                        await send_alerify_alert(subject, tg_msg, email_msg)

            # Hourly report
            current_time = time.time()
            if current_time - last_hourly_report_time >= 3600:
                last_hourly_report_time = current_time
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

        await asyncio.sleep(20)

# --- Health check web server ---
async def health_check(request):
    return web.Response(text="MovieBots are Alive!")

# --- Main function ---
async def main():
    print("🚀 Starting Setup...")

    # 1. Create Pyrogram clients for each bot token
    if not BOT_TOKENS:
        print("❌ No BOT_TOKENS provided. Exiting.")
        return

    clients = []
    for i, token in enumerate(BOT_TOKENS):
        client = Client(
            name=f"bot_{i}",                 # Unique session name
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=token
        )

        # --- Message Handlers (define for each client) ---
        @client.on_message(filters.command("start"))
        async def start_handler(c, m):
            await m.reply(f"Hello! Main {c.me.first_name} hoon. Kya help chahiye?")

        @client.on_message(filters.text & ~filters.command("start"))
        async def echo_handler(c, m):
            await m.reply(f"Aapne kaha: {m.text}")

        clients.append(client)

    # 2. Start web server
    web_app = web.Application()
    web_app.router.add_get("/", health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Health Check Server started on port {port}")

    # 3. Start pinger background task
    asyncio.create_task(ping_other_bot())
    print("🔄 Pinger Background Task Started!")

    # 4. Start all Pyrogram clients together
    print(f"🤖 Starting {len(clients)} bot(s)...")
    await compose(clients)

    # 5. Keep running
    await pyrogram.idle()

    # Cleanup on exit
    await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
