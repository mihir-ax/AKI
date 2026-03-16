import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery
from aiohttp import web

# Database imports
from database.users_db import get_user, users, check_premium

load_dotenv()

PAYMENT_BOT_TOKEN = os.getenv("PAYMENT_BOT_TOKEN", "8718753054:AAEDIdNVTL3q_L34Z7zn9ZpCA-Cp5wPSGk0")
ADMINS = [int(id) for id in os.getenv("ADMINS", "").split(",")]
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://sjadba:jasbfas@cluster0.pxtm9vd.mongodb.net/?appName=Cluster0")

# 🔒 SECURITY TOKEN (React aur Bot dono me same hona chahiye)
WEBHOOK_SECRET = "TUMHARA_SECRET_PASSWORD"

# 🎯 PLANS DICTIONARY
PLANS = {
    "plan_1w": {"name": "Starter", "days": 7, "price": 19, "daily": "₹2.7/day"},
    "plan_1m": {"name": "Premium", "days": 30, "price": 49, "daily": "₹1.6/day (Best Value)"},
    "plan_3m": {"name": "Gold", "days": 90, "price": 129, "daily": "₹1.4/day"},
    "plan_1y": {"name": "Boss", "days": 365, "price": 449, "daily": "₹1.2/day (Smart Choice)"},
}

pay_bot = Client("PaymentBot", api_id=int(os.getenv("API_ID")), api_hash=os.getenv("API_HASH"), bot_token=PAYMENT_BOT_TOKEN)

# ==========================================
# 🌐 WEBHOOK SERVER (Receives Signal from React)
# ==========================================

# CORS Headers (Taaki browser block na kare)
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

async def preflight_handler(request):
    """Browser pehle ek OPTIONS request bhejta hai CORS check karne ke liye"""
    return web.Response(headers=CORS_HEADERS)

async def payment_success_webhook(request):
    """Ye function tera React App call karega jab payment successful hogi"""
    try:
        # 🛡️ SECURITY CHECK
        secret = request.query.get("secret")
        if secret != WEBHOOK_SECRET:
            return web.json_response({"error": "Unauthorized Hacker! 😡"}, status=403, headers=CORS_HEADERS)

        data = await request.json()
        user_id = int(data.get("userid"))
        plan_id = data.get("plan_id")

        if not user_id or plan_id not in PLANS:
            return web.json_response({"error": "Invalid Data"}, status=400, headers=CORS_HEADERS)

        plan = PLANS[plan_id]
        days_to_add = plan["days"]

        # Fetch User from DB
        user = await get_user(user_id)
        current_expiry = user.get("premium_expiry")
        is_premium = user.get("is_premium", False)

        # 🔄 STACKING LOGIC (Add days to existing plan if active)
        if is_premium and current_expiry and current_expiry > datetime.now():
            new_expiry = current_expiry + timedelta(days=days_to_add)
            action_text = "Extended"
        else:
            new_expiry = datetime.now() + timedelta(days=days_to_add)
            action_text = "Upgraded"

        # Update MongoDB Directly
        await users.update_one(
            {"user_id": user_id},
            {"$set": {"is_premium": True, "premium_expiry": new_expiry}},
            upsert=True
        )

        # 📩 SEND SUCCESS MESSAGE TO USER VIA BOT
        success_msg = f"""
🎉 **PAYMENT SUCCESSFUL!** 🎉
━━━━━━━━━━━━━━━━━━━━━━
Welcome to **{plan['name']} Premium**!
Your account has been **{action_text}** by {days_to_add} Days.

🎁 **BONUS:** You now have VIP access to **BOTH (2) MAIN BOTS**!
✅ No Ads | ✅ Direct Files | ✅ 4K Quality

Type /myplan to check your new validity.
"""
        await pay_bot.send_message(chat_id=user_id, text=success_msg)

        # Notify Admins
        for admin in ADMINS:
            try:
                await pay_bot.send_message(admin, f"💸 **NEW SALE!**\nUser: `{user_id}` bought **{plan['name']}**.\nEarned: ₹{plan['price']}")
            except: pass

        return web.json_response({"status": "success", "message": "Premium Activated!"}, headers=CORS_HEADERS)

    except Exception as e:
        print(f"Webhook Error: {e}")
        return web.json_response({"error": str(e)}, status=500, headers=CORS_HEADERS)


# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

@pay_bot.on_message(filters.command("start") & filters.private)
async def start_payment(client, message):
    user_id = message.from_user.id
    is_prem = await check_premium(user_id)

    greeting = ""
    if is_prem:
        user = await get_user(user_id)
        days_left = (user.get("premium_expiry") - datetime.now()).days
        greeting = f"🎉 **You are a Premium Member! ({days_left} Days Left)**\n*Want to extend your plan? Buy again and days will be added automatically!*\n\n"

    text = greeting + f"""
🚨 **STOP WASTING TIME ON ADS & LINKS!** 🚨
━━━━━━━━━━━━━━━━━━━━━━
Dusre log 1 minute me movie download karke dekhna shuru kar dete hain. Aur aap ad-links me fase rehte ho?

🌟 **UPGRADE TO DIRECT PREMIUM** 🌟
✅ **Zero Ads** (Gande popups khatam)
✅ **1-Click Download** (Direct Telegram file)
✅ **Access to 2 VIP Bots** 🤖🤖
✅ **4K Quality Unlocked**

⚡ *Only 7 spots left for today's discounted price!*
"""

    # 🌐 TELEGRAM WEB APP LOGIC
    payment_url = f"https://svms.in/payementxyz-rra/?userid={user_id}"

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 OPEN PREMIUM STORE", web_app=WebAppInfo(url=payment_url))],
        [InlineKeyboardButton("ℹ️ Check Plans", callback_data="show_plans")]
    ])
    await message.reply_text(text, reply_markup=btn)

@pay_bot.on_callback_query(filters.regex("show_plans"))
async def show_plans_handler(client, callback: CallbackQuery):
    text = "**📊 OUR PREMIUM PLANS (All include 2 VIP Bots!)**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for details in PLANS.values():
        text += f"**{details['name']} ({details['days']} Days)**\n💰 Price: ₹{details['price']} | 🔥 {details['daily']}\n\n"

    text += "👇 Click below to open the secure store inside Telegram!"

    payment_url = f"https://svms.in/payementxyz-rra/?userid={callback.from_user.id}"
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🛍️ OPEN STORE", web_app=WebAppInfo(url=payment_url))]])

    await callback.message.edit_text(text, reply_markup=btn)

@pay_bot.on_message(filters.command("myplan") & filters.private)
async def myplan_handler(client, message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    is_prem = await check_premium(user_id)

    if not is_prem:
        return await message.reply_text("❌ **You don't have an active Premium Plan.**\n\nType /start to buy one and stop wasting time on ads!")

    expiry_date = user.get("premium_expiry")
    days_left = (expiry_date - datetime.now()).days
    expiry_str = expiry_date.strftime("%d %B %Y, %I:%M %p")

    text = f"""
👑 **YOUR PREMIUM DASHBOARD**
━━━━━━━━━━━━━━━━━━━━━━
👤 **User:** {message.from_user.first_name}
🆔 **ID:** `{user_id}`

🟢 **Status:** ACTIVE
⏳ **Days Remaining:** {days_left} Days
📅 **Valid Till:** {expiry_str}

✅ Ad-Free Experience
✅ Direct Downloads Enabled
✅ Access to Both (2) Main Bots

*You can extend your plan anytime by typing /start.*
"""
    await message.reply_text(text)

# ==========================================
# 🚀 START BOTH BOT & WEB SERVER CONCURRENTLY
# ==========================================
async def main():
    # 1. Start Web Server
    app = web.Application()

    # CORS Route (Required for Web Browsers)
    app.router.add_options('/webhook/success', preflight_handler)
    # Actual POST Route
    app.router.add_post('/webhook/success', payment_success_webhook)

    runner = web.AppRunner(app)
    await runner.setup()

    # 🌍 RENDER FIX: Render assigns dynamic port using OS Environment
    port = int(os.environ.get("PORT", 8080))

    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 Webhook API Server started on port {port}")

    # 2. Start Bot
    await pay_bot.start()
    print("💸 Payment Bot Started Successfully!")

    # Keep running
    await idle()

    # Shutdown gracefully
    await pay_bot.stop()
    await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
