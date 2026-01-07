from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN
import logging
from database.movies_db import create_indexes # Import karo

# Basic logging
logging.basicConfig(level=logging.INFO)

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

    async def stop(self, *args):
        await super().stop()
        print("👋 Bot Stopped!")

if __name__ == "__main__":
    Bot().run()
