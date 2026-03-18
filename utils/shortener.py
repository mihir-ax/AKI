import aiohttp
import json
import traceback
from config import ADMINS, BOT_TOKENS

async def shorten_url(original_url, api_url, api_key):
    """
    Async URL shortener for svms.in
    Sends detailed error reports directly to ADMINS if it fails.
    """
    if not api_key:
        print("❌ API Key Missing!")
        return None

    # Browser headers to prevent API blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Parameters exactly as you tested and passed
    params = {
        "api_key": api_key,
        "url": original_url,
        "mode": "multipages",
        "num_pages": "2"
    }

    error_message = None

    try:
        # Aiohttp session for async request
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params, headers=headers, timeout=15) as response:
                text_data = await response.text()

                try:
                    data = json.loads(text_data)

                    if data.get("status") == "success":
                        short_url = data.get("shortenedUrl") or data.get("shortened_url")
                        if short_url:
                            return short_url.replace("\\/", "/")
                    else:
                        error_message = (
                            f"⚠️ <b>Shortener API Error:</b>\n"
                            f"<code>{data}</code>\n\n"
                            f"<b>Original URL:</b>\n<code>{original_url}</code>\n\n"
                            f"#short_error"
                        )

                except json.JSONDecodeError:
                    error_message = (
                        f"❌ <b>Shortener API did not return JSON.</b>\n"
                        f"<b>Status Code:</b> {response.status}\n"
                        f"<b>Raw Response:</b>\n<code>{text_data[:200]}</code>\n\n"
                        f"#short_error"
                    )

    except Exception as e:
        error_message = (
            f"❌ <b>Shortener Request Failed:</b>\n"
            f"<code>{str(e)}</code>\n\n"
            f"<b>Original URL:</b>\n<code>{original_url}</code>\n\n"
            f"#short_error"
        )

    # ==========================================
    # 🚨 ERROR AANE PAR ADMIN KO MESSAGE BHEJNA
    # ==========================================
    if error_message:
        print("Shortener Error Detected:", error_message) # Terminal print

        # Agar config mein bot token aur admins list maujood hai
        if BOT_TOKENS and ADMINS:
            bot_token = BOT_TOKENS[0] # Pehle bot ka token use karega msg bhejne ke liye
            send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            async with aiohttp.ClientSession() as session:
                for admin in ADMINS:
                    payload = {
                        "chat_id": admin,
                        "text": error_message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    }
                    try:
                        # Direct Telegram HTTP API call (Bina pyrogram client pass kiye)
                        await session.post(send_url, json=payload, timeout=5)
                    except Exception as admin_err:
                        print(f"⚠️ Failed to send error to Admin {admin}: {admin_err}")

    return None
