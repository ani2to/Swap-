import os
import requests
import base64
import flask
import logging
import telebot
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# Get credentials from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
WORKER_URL = os.environ.get('WORKER_URL', 'YOUR_API_URL_HERE')

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}
WAITING_FOR_SOURCE = 1
WAITING_FOR_TARGET = 2

# Channel information
CHANNELS = [
    {"url": "https://t.me/+zXEppIfULNRhOGNl", "name": "Channel 1", "chat_id": -1002438082284},
    {"url": "https://t.me/+mL09ZgHctA5hZDA9", "name": "Channel 2", "chat_id": -1002267241920},
    {"url": "https://t.me/SPBotz", "name": "SPBotz", "chat_id": "@SPBotz"},
    {"url": "https://t.me/itz_4nuj1", "name": "Anuj", "chat_id": "@itz_4nuj1"}
]

ADMIN_USERIDS = [6899720377, 6302016869]

# Database setup
def init_db():
    conn = sqlite3.connect('bot_stats.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
                  date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_usage
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect('bot_stats.db')
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users (user_id, username, first_name) 
                 VALUES (?, ?, ?)''', (user_id, username, first_name))
    conn.commit()
    conn.close()

def record_api_usage(user_id):
    conn = sqlite3.connect('bot_stats.db')
    c = conn.cursor()
    c.execute('''INSERT INTO api_usage (user_id) VALUES (?)''', (user_id,))
    conn.commit()
    conn.close()

def get_user_stats():
    conn = sqlite3.connect('bot_stats.db')
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) FROM users''')
    total_users = c.fetchone()[0]
    c.execute('''SELECT COUNT(*) FROM api_usage''')
    total_api_calls = c.fetchone()[0]
    c.execute('''SELECT COUNT(*) FROM api_usage WHERE date(timestamp) = date('now')''')
    today_api_calls = c.fetchone()[0]
    conn.close()
    return total_users, total_api_calls, today_api_calls

def get_all_users():
    conn = sqlite3.connect('bot_stats.db')
    c = conn.cursor()
    c.execute('''SELECT user_id FROM users''')
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def check_subscription(user_id):
    try:
        for channel in CHANNELS:
            chat_id = channel["chat_id"]
            try:
                member = bot.get_chat_member(chat_id, user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    return False
            except:
                return False
        return True
    except:
        return False

def create_subscription_keyboard():
    keyboard = InlineKeyboardMarkup()
    row1 = [
        InlineKeyboardButton("📢 ᴊᴏɪɴ", url=CHANNELS[0]["url"]),
        InlineKeyboardButton("📢 ᴊᴏɪɴ", url=CHANNELS[1]["url"])
    ]
    row2 = [
        InlineKeyboardButton("📢 ᴊᴏɪɴ", url=CHANNELS[2]["url"]),
        InlineKeyboardButton("📢 ᴊᴏɪɴ", url=CHANNELS[3]["url"])
    ]
    keyboard.row(*row1)
    keyboard.row(*row2)
    check_button = InlineKeyboardButton("✅ Check Subscription", callback_data="check_subscription")
    keyboard.row(check_button)
    return keyboard

def send_loading_animation(chat_id):
    loading_steps = [
        "🔄 Processing your images... █░░░░░░░░░",
        "🎭 Detecting faces... ███░░░░░░░",
        "✨ Swapping faces... █████░░░░░",
        "📸 Finalizing result... ███████░░░",
        "✅ Almost done... ██████████░"
    ]
    
    message_id = None
    for i, text in enumerate(loading_steps):
        try:
            if i == 0:
                msg = bot.send_message(chat_id, text)
                message_id = msg.message_id
            else:
                bot.edit_message_text(text, chat_id, message_id)
            import time
            time.sleep(2)
        except:
            pass
    return message_id

@bot.message_handler(commands=['start', 'help'])
def start_help(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    add_user(user_id, username, first_name)
    
    if not check_subscription(user_id):
        welcome_text = """🔒 **Access Required** 🔒

🎭 *Welcome to Face Swapper Bot!* 🎭

To use our face swap bot you need to join our channels first! 

📢 **Join these channels:**"""
        
        bot.send_message(
            chat_id, 
            welcome_text,
            reply_markup=create_subscription_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # User is subscribed
    welcome_text = f"""👋 **Hey {first_name}! Welcome to Face Swapper Bot!** 👋

✨ *This bot helps you to swap faces in photos!* ✨

**How to use:**
1️⃣ Send me the **source photo** (the face you want to use)
2️⃣ Send me the **target photo** (the face you want to replace)
3️⃣ Wait for the magic to happen! 🎭

🚀 *Get started by sending your first photo!*

---
👨‍💻 **Developed by:** [𝙰𝚗𝚞𝚓](tg://user?id=6899720377) × [#𝐒𝐏](tg://user?id=6302016869)
💫 *Your photos are processed securely*"""
    
    bot.send_message(chat_id, welcome_text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    if check_subscription(user_id):
        first_name = call.from_user.first_name
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        
        welcome_text = f"""👋 **Hey {first_name}! Welcome to Face Swapper Bot!** 👋

✨ *This bot helps you to swap faces in photos!* ✨

**How to use:**
1️⃣ Send me the **source photo** (the face you want to use)
2️⃣ Send me the **target photo** (the face you want to replace)
3️⃣ Wait for the magic to happen! 🎭

🚀 *Get started by sending your first photo!*

---
👨‍💻 **Developed by:** [𝙰𝚗𝚞𝚓](tg://user?id=6899720377) × [#𝐒𝐏](tg://user?id=6302016869)
💫 *Your photos are processed securely*"""
        
        bot.send_message(chat_id, welcome_text, parse_mode='Markdown')
    else:
        bot.answer_callback_query(call.id, "❌ Please join all channels first! Make sure you've joined ALL 4 channels.", show_alert=True)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ Please join all channels first using /start")
        return
    
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        img_bytes = requests.get(file_url).content

        if chat_id not in user_data:
            user_data[chat_id] = {
                "state": WAITING_FOR_TARGET,
                "source": img_bytes
            }
            bot.reply_to(message, "✅ **Great! Source face saved!** \n\n📸 Now send me the **target photo** (the face you want to replace)")
        else:
            if user_data[chat_id]["state"] == WAITING_FOR_TARGET:
                user_data[chat_id]["target"] = img_bytes
                user_data[chat_id]["state"] = None
                
                loading_msg_id = send_loading_animation(chat_id)
                
                source_b64 = base64.b64encode(user_data[chat_id]["source"]).decode('utf-8').replace('\n','')
                target_b64 = base64.b64encode(user_data[chat_id]["target"]).decode('utf-8').replace('\n','')

                payload = {
                    "source": source_b64,
                    "target": target_b64,
                    "security": {
                        "token": "0.ufDEMbVMT7mc9_XLsFDSK5CQqdj9Cx_Zjww0DevIvXN5M4fXQr3B9YtPdGkKAHjXBK6UC9rFcEbZbzCfkxxgmdTYV8iPzTby0C03dTKv5V9uXFYfwIVlqwNbIsfOK_rLRHIPB31bQ0ijSTEd-lLbllf3MkEcpkEZFFmmq8HMAuRuliCXFEdCwEB1HoYSJtvJEmDIVsooU3gYdrCm5yOJ8_lZ4DiHCSvy7P8-YxwJKkapJNCMUCFIfJbWDkDzvh8DGPyTRoHbURX8kClfImmPrGcqlfd7kkoNRcudS25IbNf1CGBsh8V96MtEhnTZvOpZfnp5dpV7MfgwOgvx7hUazUaC_wxQE63Aa0uOPuGvJ70BNrmeZIIrY9roD1Koj316L4g2BZ_LLZZF11wcrNNon8UXB0iVudiNCJyDQCxLUmblXUpt4IUvRoiOqXBNtWtLqY0su0ieVB0jjyDf_-zs7wc8WQ_jqp-NsTxgKOgvZYWV6Elz_lf4cNxGHZJ5BdcyLEoRBH3cksvwoncmYOy5Ulco22QT-x2z06xVFBZYZMVulxAcmvQemKfSFKsNaDxwor35p-amn9Vevhyb-GzA_oIoaTmc0fVXSshax2rdFQHQms86fZ_jkTieRpyIuX0mI3C5jLGIiOXzWxNgax9eZeQstYjIh8BIdMiTIUHfyKVTgtoLbK0hjTUTP0xDlCLnOt5qHdwe_iTWedBsswAJWYdtIxw0YUfIU22GMYrJoekOrQErawNlU5yT-LhXquBQY3EBtEup4JMWLendSh68d6HqjN2T3sAfVw0nY5jg7_5LJwj5gqEk57devNN8GGhogJpfdGzYoNGja22IZIuDnPPmWTpGx4VcLOLknSHrzio.tXUN6eooS69z3QtBp-DY1g.d882822dfe05be2b36ed1950554e1bac753abfe304a289adc4289b3f0d517356",
                        "type": "invisible",
                        "id": "deepswapper"
                    }
                }

                response = requests.post(WORKER_URL, json=payload)

                try:
                    bot.delete_message(chat_id, loading_msg_id)
                except:
                    pass

                if response.status_code == 200:
                    record_api_usage(user_id)
                    caption = "🎉 **Face Swap Completed!** 🎉\n\n✨ *Bot BY* - [𝙰𝚗𝚞𝚓](tg://user?id=6899720377) × [#𝐒𝐏](tg://user?id=6302016869)"
                    
                    with open("swapped.png", "wb") as f:
                        f.write(response.content)
                    with open("swapped.png", "rb") as photo:
                        bot.send_photo(chat_id, photo, caption=caption, parse_mode='Markdown')
                    os.remove("swapped.png")
                    del user_data[chat_id]
                else:
                    bot.reply_to(message, f"❌ **API request failed** with status {response.status_code}\n\nPlease try again later!")
            else:
                bot.reply_to(message, "⚠️ Please send the **target photo** (the face to replace).")
    except Exception as e:
        bot.reply_to(message, f"❌ **An error occurred:** {str(e)}\n\nPlease try again!")
        if chat_id in user_data:
            del user_data[chat_id]

# ===== Admin Commands =====
@bot.message_handler(commands=['stats'])
def stats_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_USERIDS:
        bot.reply_to(message, "❌ **Access Denied!** Admin only command.")
        return
    
    total_users, total_api_calls, today_api_calls = get_user_stats()
    
    stats_text = f"""📊 **Bot Statistics** 📊

👥 **Total Users:** `{total_users}`
🔄 **Total API Calls:** `{total_api_calls}`
📈 **Today's API Calls:** `{today_api_calls}`
📅 **Last Updated:** `{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`"""
    
    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['apistats'])
def apistats_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_USERIDS:
        bot.reply_to(message, "❌ **Access Denied!** Admin only command.")
        return
    
    total_users, total_api_calls, today_api_calls = get_user_stats()
    
    api_stats_text = f"""🔧 **API Statistics** 🔧

🔄 **Total API Calls:** `{total_api_calls}`
📈 **Today's API Calls:** `{today_api_calls}`
👥 **Average per User:** `{total_api_calls/max(1, total_users):.2f}`
📅 **Last Updated:** `{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`"""
    
    bot.reply_to(message, api_stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_USERIDS:
        bot.reply_to(message, "❌ **Access Denied!** Admin only command.")
        return
    
    if message.reply_to_message:
        broadcast_message = message.reply_to_message
        users = get_all_users()
        success = 0
        failed = 0
        
        bot.reply_to(message, f"📢 **Starting broadcast to {len(users)} users...**")
        
        for user_id in users:
            try:
                if broadcast_message.text:
                    bot.send_message(user_id, broadcast_message.text, parse_mode='Markdown')
                elif broadcast_message.photo:
                    bot.send_photo(user_id, broadcast_message.photo[-1].file_id, 
                                 caption=broadcast_message.caption, 
                                 parse_mode='Markdown')
                else:
                    bot.copy_message(user_id, message.chat.id, broadcast_message.message_id)
                success += 1
            except:
                failed += 1
        
        result_text = f"""✅ **Broadcast Completed!**

📤 **Sent successfully:** `{success}`
❌ **Failed:** `{failed}`
📊 **Success rate:** `{(success/len(users))*100:.1f}%`"""
        
        bot.reply_to(message, result_text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ **Usage:** Reply to a message with `/broadcast` to send it to all users.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ Please join all channels first using /start")
        return
        
    if chat_id in user_data:
        bot.reply_to(message, "📸 Please send the **target photo** (the face you want to replace)")
    else:
        bot.reply_to(message, "👋 Welcome! Use /start to begin face swapping! ✨")

print("🤖 Bot is running...")
bot.polling()
from flask import Flask
from threading import Thread


app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_flask).start()
