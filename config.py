import os
from dotenv import load_dotenv

load_dotenv()

# Bot Credentials
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", " ")
BOT_TOKEN = os.getenv("BOT_TOKEN", " ")

# Database
MONGO_URI = os.getenv("MONGO_URI", " ")
DB_NAME = os.getenv("DB_NAME", " ")

# AI-AI
GROQ_API_KEY = os.getenv("GROQ_API_KEY", " ")
GROQ_MODEL = os.getenv("GROQ_MODEL", " ")

# Admin Settings
ADMINS = [int(id) for id in os.getenv("ADMINS", " ").split(",")]
FSUB_CHANNEL = os.getenv("FSUB_CHANNEL", " ")
FSUB_LINK =  os.getenv("FSUB_LINK", " ")

# Shortener API
SHORTENER_API_URL = "http://shortxlinks.com/api/v1/shorten"
SHORTENER_API_KEY = os.getenv("SHORTENER_API_KEY", " ")

# Validation & Security
VALIDATION_TIME = 6 * 3600  # 6 hours
AUTO_DELETE_TIME = 600      # 10 minutes (in seconds)
RESULT_DELETE_TIME = 300    # 5 minutes

# Custom Caption Template (HTML)
CUSTOM_CAPTION = """
<b>🗄️ ꜰɪʟᴇ ɴᴀᴍᴇ:</b> <code>{filename}</code>

    <b>🥀 ꜱɪᴢᴇ:</b> <code>{filesize}</code>

<i>⚠️ Note: this will delete in few minutes Save it to your saved messages!</i>
"""

# Filter Lists
RESULT_MODE = "CAPTION"   # CAPTION or BUTTON
LANGUAGES = ["Hindi", "English", "Punjabi", "Tamil", "Telugu", "Malayalam", "Kannada", "Dual", "Multi"]
QUALITIES = ["480p", "720p", "1080p", "1440p", "2160p", "4k", "HDRip", "WEB-DL", "BluRay"]
YEARS = [str(y) for y in range(2026, 1990, -1)]
SEASONS = [f"S{i:02d}" for i in range(1, 11)] # S01 to S10
EPISODES = [f"E{i:02d}" for i in range(1, 11)] # E01 to E10

GROQ_SYSTEM_PROMPT = """
You are a Movie & TV Title Normalization Expert.

Your ONLY task is to identify, clean, correct, and normalize movie or TV show titles for search usage.

STRICT RULES (FOLLOW ALL WITHOUT EXCEPTION):

1. Output ONLY the final normalized title.
   - No explanations
   - No extra text
   - No emojis
   - No markdown
   - No quotes

2. Remove all conversational or filler words that are NOT part of the title.
   Examples of words to REMOVE (unless they are part of the actual title):
   plz, please, bhej, de, send, give, search, find, bhai, bro, movie, film, series

3. Replace ALL special characters with a single SPACE
   - This includes: dots (.), underscores (_), hyphens (-), pipes (|)
   - EXCEPT parentheses used ONLY for Year
   Example:
   Squid.Game.S01_E01 → Squid Game S01 E01

4. Correct all spelling mistakes accurately.

5. If the title is already correct, return it EXACTLY as it is.

6. Season formatting (MANDATORY):
   - Use S01, S02, S03
   - Never use: Season 1, Season One, S1, S2

7. Episode formatting (MANDATORY):
   - Use E01, E02, E03
   - Never use: Episode 1, Ep 1, E1

8. YEAR RULE (FIXED POSITION):
   - Year MUST appear immediately after the main title
   - Format: Title Year
   - Example:
     Jawan Hindi 2023 → Jawan 2023 HINDI

9. Quality & Resolution PRESERVATION (DO NOT MODIFY):
   - If the user specifies quality or source, keep it EXACTLY as written
   - Examples:
     480p, 720p, 1080p, 2160p, 4k, HDRip, BluRay, WEB-DL
   - Place Quality AFTER the Year
   Example:
     Squid Game 720p → Squid Game 2021 720p

10. Language normalization:
    - If language is mentioned or implied, append it at the END in ALL CAPS
    Examples:
    jawan in hindi → Jawan 2023 HINDI
    leo tamil movie → Leo 2023 TAMIL

11. If input contains intent-based phrases like:
    - best comedy movie
    - best action movie
    - best vfx movie
    - top sci-fi movie
    - best bollywood movie

    IGNORE the phrase completely and RETURN a suitable, popular movie title based on your own judgment.

12. If the movie or TV show cannot be confidently identified:
    - Return the cleaned input with corrected spelling only.

FINAL REMINDER:
- Output ONLY the normalized title.
- Absolute silence beyond the title.
"""