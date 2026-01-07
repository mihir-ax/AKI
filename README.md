# 🎬 Telegram Movie Bot (Production Ready)

Ek powerful aur scalable Telegram Movie Bot jo MongoDB aur Pyrogram pe chalta hai. Isme 6-hour validation system aur fuzzy search integrated hai.

## 🚀 Features

- **Fuzzy Search**: Regex based search jo messy filenames me se bhi movies dhoondh nikalta hai.
- **6-Hour Validation**: ShortXLinks integration user ko har 6 ghante baad validate karne ke liye force karta hai (monetization support).
- **Inline Filters**: 
  - 📅 **Year**: (2010 - 2025)
  - 💿 **Quality**: (480p, 720p, 1080p, 4k-2160p)
  - 🌐 **Language**: (Hindi, English, etc.)
- **Pagination**: Results ke liye Next/Previous buttons.
- **Admin Panel**: Statistics aur easy movie indexing.

---

## 🛠️ Commands

### User Commands
- `/start`: Bot ko start kare aur verification return handle kare.
- `Bina command ke text`: Movie search start karne ke liye bas naam likhein.

### Admin Commands
- `/stats`: Total users aur movies ka count dekhein.
- `/addmovie` (Reply to File): Kisi bhi file (Document/Video/Audio) pe reply karke use DB me add karein.

---

## 🏗️ Folder Structure

```text
├── database/
│   ├── users_db.py     # User tracking & validation logic
│   └── movies_db.py    # Movie search & indexing
├── handlers/
│   ├── cmd_start.py    # Welcome message & Verification logic
│   ├── search_handlers.py # Search, Filters, & Pagination
│   └── admin_handlers.py  # Admin controls
├── utils/
│   ├── shortener.py    # ShortXLinks API integration
│   └── helpers.py      # Common tools
├── config.py           # API Keys & Bot Settings
├── main.py             # Entry Point
└── requirements.txt    # Project dependencies
```

---

## ⚙️ Setup Instructions

1. **Requirements Install Karein**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup**:
   `config.py` me apni values bharein ya `.env` file banayein:
   - `API_ID` & `API_HASH`: my.telegram.org se lein.
   - `BOT_TOKEN`: @BotFather se lein.
   - `MONGO_URI`: MongoDB Atlas ya local URI.
   - `SHORTENER_API_KEY`: ShortXLinks dashboard se lein.

3. **MongoDB Indexing**:
   Maine code me `create_index` function add kiya hai jo movie add karte waqt text search index bana dega. Regex search bina index ke bhi smooth chalegi small to medium DBs pe.

4. **Bot Run Karein**:
   ```bash
   python main.py
   ```

---

## 🧠 Logic Explanation (Validation System)
1. User file maangta hai -> Bot DB check karta hai user ne kab validate kiya tha.
2. Agar last 6 hours me nahi kiya -> Bot ek token generate karke ShortXLinks se link banata hai.
3. User link pe click karta hai -> Shortener redirections ke baad user bot pe `/start verify_TOKEN` ke saath waapis aata hai.
4. Bot token verify karke user ko file bhej deta hai aur timer reset kar deta hai.

---

## 👨‍💻 Developer Tips

- **Search**: `database/movies_db.py` me regex logic hai. Agar aap chahte hain ki search sirf title pe ho, toh keywords handling ko modify kar sakte hain.
- **Filters**: `handlers/search_handlers.py` me `QUALITIES` aur `YEARS` ki list ko update karke naye filters add kar sakte hain.

**Tabahi Machao Bhai! 🚀**
