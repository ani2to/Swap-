import os
import requests
import base64
import telebot
import pymongo
import time
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# Get credentials from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
WORKER_URL = os.environ.get('WORKER_URL', 'YOUR_API_URL_HERE')
MONGO_URI = os.environ.get('MONGO_URI', 'YOUR_MONGODB_URI_HERE')
LOG_CHANNEL_ID = os.environ.get('LOG_CHANNEL_ID', '-1001234567890')  # Add your log channel ID

bot = telebot.TeleBot(BOT_TOKEN)

# MongoDB setup
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client.face_swap_bot
    users_collection = db.users
    api_usage_collection = db.api_usage
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    # Fallback to in-memory storage (will be lost on restart)
    users_collection = None
    api_usage_collection = None

user_data = {}
WAITING_FOR_SOURCE = 1
WAITING_FOR_TARGET = 2

# Channel information
CHANNELS = [
    {"url": "https://t.me/+qy5q53874S1hMzZl", "name": "Channel 1", "chat_id": -1002267241920},
    {"url": "https://t.me/+oOIaCEXNqK04M2Rl", "name": "Channel 2", "chat_id": -1002438082284},
    {"url": "https://t.me/SPBotz", "name": "SPBotz", "chat_id": "@SPBotz"},
    {"url": "https://t.me/itz_4nuj1", "name": "Anuj", "chat_id": "@itz_4nuj1"}
]

ADMIN_USERIDS = [6899720377, 6302016869]

def add_user(user_id, username, first_name):
    """Add user to MongoDB"""
    if users_collection is None:
        return
    
    try:
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "date_joined": datetime.now()
        }
        
        # Check if user already exists
        existing_user = users_collection.find_one({"user_id": user_id})
        if not existing_user:
            users_collection.insert_one(user_data)
            print(f"✅ New user added to MongoDB: {user_id}")
            
            # Send to log channel
            send_to_log_channel(user_id, username, first_name)
        else:
            print(f"ℹ️ User already exists in MongoDB: {user_id}")
            
    except Exception as e:
        print(f"❌ Error adding user to MongoDB: {e}")

def send_to_log_channel(user_id, username, first_name):
    """Send new user information to log channel"""
    try:
        log_message = f"""🆕 New user started the bot Face Swap bot !!

👤 Name: {first_name} !!
🆔 User ID: `{user_id}`
📛 Username: @{username if username else 'No Username'}
📩 Message: The user has started the bot."""
        
        bot.send_message(
            LOG_CHANNEL_ID, 
            log_message,
            parse_mode='Markdown'
        )
        print(f"✅ Log sent to channel for user: {user_id}")
    except Exception as e:
        print(f"❌ Error sending to log channel: {e}")

def record_api_usage(user_id):
    """Record API usage in MongoDB"""
    if api_usage_collection is None:
        return
    
    try:
        usage_data = {
            "user_id": user_id,
            "timestamp": datetime.now()
        }
        api_usage_collection.insert_one(usage_data)
    except Exception as e:
        print(f"❌ Error recording API usage: {e}")

def get_user_stats():
    """Get user statistics from MongoDB"""
    if users_collection is None or api_usage_collection is None:
        return 0, 0, 0
    
    try:
        total_users = users_collection.count_documents({})
        total_api_calls = api_usage_collection.count_documents({})
        
        # Get today's API calls
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_api_calls = api_usage_collection.count_documents({
            "timestamp": {"$gte": today_start}
        })
        
        return total_users, total_api_calls, today_api_calls
    except Exception as e:
        print(f"❌ Error getting user stats: {e}")
        return 0, 0, 0

def get_all_users():
    """Get all user IDs from MongoDB"""
    if users_collection is None:
        return []
    
    try:
        users = users_collection.find({}, {"user_id": 1})
        return [user["user_id"] for user in users]
    except Exception as e:
        print(f"❌ Error getting all users: {e}")
        return []

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
        "🔄 Processing your images...",
        "🎭 Detecting faces...",
        "✨ Swapping faces...",
        "📸 Finalizing result...",
        "✅ Almost done..."
    ]
    
    message_id = None
    for i, text in enumerate(loading_steps):
        try:
            if i == 0:
                msg = bot.send_message(chat_id, text)
                message_id = msg.message_id
            else:
                bot.edit_message_text(text, chat_id, message_id)
            time.sleep(1.5)
        except:
            pass
    return message_id

@bot.message_handler(commands=['start', 'help'])
def start_help(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        first_name = message.from_user.first_name or "User"
        
        add_user(user_id, username, first_name)
        
        if not check_subscription(user_id):
            welcome_text = """🔒 Access Required 🔒

🎭 Welcome to Face Swapper Bot 🎭

To use our face swap bot you need to join our channels first! 

📢 Join these channels:"""
            
            bot.send_message(
                chat_id, 
                welcome_text,
                reply_markup=create_subscription_keyboard()
            )
            return
        
        welcome_text = f"""👋 Hey {first_name}! Welcome to Face Swapper Bot 👋

✨ This bot helps you to swap faces in photos ✨

How to use:
1. Send me the source photo (the face you want to use)
2. Send me the target photo (the face you want to replace)
3. Wait for the result! 🎭

Get started by sending your first photo!

---
Developed by: [𝙰𝚗𝚞𝚓](tg://user?id=6899720377) × [#𝐒𝐏](tg://user?id=6302016869)
Your photos are processed securely"""
        
        bot.send_message(chat_id, welcome_text, parse_mode='Markdown')
    except Exception as e:
        print(f"Error in start command: {e}")

@bot.message_handler(commands=['swap'])
def swap_command(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        if not check_subscription(user_id):
            bot.reply_to(message, "❌ Please join all channels first using /start")
            return
        
        if chat_id in user_data:
            del user_data[chat_id]
        
        bot.reply_to(message, "📸 Please send the source photo (the face you want to use)")
        
    except Exception as e:
        print(f"Error in swap command: {e}")
        bot.reply_to(message, "❌ An error occurred. Please try again.")

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    try:
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        first_name = call.from_user.first_name or "User"
        
        if check_subscription(user_id):
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except:
                pass
            
            welcome_text = f"""👋 Hey {first_name}! Welcome to Face Swapper Bot 👋

✨ This bot helps you to swap faces in photos ✨

How to use:
1. Send me the source photo (the face you want to use)
2. Send me the target photo (the face you want to replace)
3. Wait for the result! 🎭

Get started by sending your first photo!

---
Developed by: [𝙰𝚗𝚞𝚓](tg://user?id=6899720377) × [#𝐒𝐏](tg://user?id=6302016869)
Your photos are processed securely"""
            
            bot.send_message(chat_id, welcome_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ Please join all channels first! Make sure you've joined ALL 4 channels.", show_alert=True)
    except Exception as e:
        print(f"Error in callback: {e}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    try:
        user_id = message.from_user.id
        
        if not check_subscription(user_id):
            bot.reply_to(message, "❌ Please join all channels first using /start")
            return
        
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        img_bytes = requests.get(file_url, timeout=30).content

        if chat_id not in user_data:
            # Save source image
            user_data[chat_id] = {
                "state": WAITING_FOR_TARGET,
                "source": img_bytes
            }
            bot.reply_to(message, "👍 Got your **source face**! Now send the **target photo**.")
        else:
            if user_data[chat_id]["state"] == WAITING_FOR_TARGET:
                user_data[chat_id]["target"] = img_bytes
                user_data[chat_id]["state"] = None
                
                loading_msg_id = send_loading_animation(chat_id)
                
                source_b64 = base64.b64encode(user_data[chat_id]["source"]).decode('utf-8').replace('\n','')
                target_b64 = base64.b64encode(user_data[chat_id]["target"]).decode('utf-8').replace('\n','')

                # YOUR ORIGINAL API PAYLOAD WITH SECURITY TOKEN
                payload = {
                    "source": source_b64,
                    "target": target_b64,
                    "security": {
                        "token": "0.ufDEMbVMT7mc9_XLsFDSK5CQqdj9Cx_Zjww0DevIvXN5M4fXQr3B9YtPdGkKAHjXBK6UC9rFcEbZbzCfkxxgmdTYV8iPzTby0C03dTKv5V9uXFYfwIVlqwNbIsfOK_rLRHIPB31bQ0ijSTEd-lLbllf3MkEcpkEZFFmmq8HMAuRuliCXFEdCwEB1HoYSJtvJEmDIVsooU3gYdrCm5yOJ8_lZ4DiHCSvy7P8-YxwJKkapJNCMUCFIfJbWDkDzvh8DGPyTRoHbURX8kClfImmPrGcqlfd7kkoNRcudS25IbNf1CGBsh8V96MtEhnTZvOpZfnp5dpV7MfgwOgvx7hUazUaC_wxQE63Aa0uOPuGvJ70BNrmeZIIrY9roD1Koj316L4g2BZ_LLZZF11wcrNNon8UXB0iVudiNCJyDQCxLUmblXUpt4IUvRoiOqXBNtWtLqY0su0ieVB0jjyDf_-zs7wc8WQ_jqp-NsTxgKOgvZYWV6Elz_lf4cNxGHZJ5BdcyLEoRBH3cksvwoncmYOy5Ulco22QT-x2z06xVFBZYZMVulxAcmvQemKfSFKsNaDxwor35p-amn9Vevhyb-GzA_oIoaTmc0fVXSshax2rdFQHQms86fZ_jkTieRpyIuX0mI3C5jLGIiOXzWxNgax9eZeQstYjIh8BIdMiTIUHfyKVTgtoLbK0hjTUTP0xDlCLnOt5qHdwe_iTWedBsswAJWYdtIxw0YUfIU22GMYrJoekOrQErawNlU5yT-LhXquBQY3EBtEup4JMWLendSh68d6HqjN2T3sAfVw0nY5jg7_5LJwj5gqEk57devNN8GGhogJpfdGzYoNGja22IZIuDnPPmWTpGx4VcLOLknSHrzio.tXUN6eooS69z3QtBp-DY1g.d882822dfe05be2b36ed1950554e1bac753abfe304a289adc4289b3f0d517356",
                        "type": "invisible",
                        "id": "deepswapper"
                    }
                }

                # Send request to Cloudflare Worker
                response = requests.post(WORKER_URL, json=payload, timeout=60)

                try:
                    bot.delete_message(chat_id, loading_msg_id)
                except:
                    pass

                if response.status_code == 200:
                    record_api_usage(user_id)
                    # Send PNG directly to Telegram
                    with open("swapped.png", "wb") as f:
                        f.write(response.content)
                    with open("swapped.png", "rb") as photo:
                        bot.send_photo(chat_id, photo, caption="🎉 Face Swap Completed! 🎉\n\n✨ Bot BY - [𝙰𝚗𝚞𝚓](tg://user?id=6899720377) × [#𝐒𝐏](tg://user?id=6302016869)", parse_mode='Markdown')
                    os.remove("swapped.png")
                    del user_data[chat_id]
                else:
                    bot.reply_to(message, f"❌ API request failed with status {response.status_code}")
            else:
                bot.reply_to(message, "⚠️ Please send the **target photo** (the face to replace).")
    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")
        if chat_id in user_data:
            del user_data[chat_id]

# ===== Admin Commands =====
@bot.message_handler(commands=['stats'])
def stats_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_USERIDS:
        bot.reply_to(message, "❌ Access Denied! Admin only command.")
        return
    
    total_users, total_api_calls, today_api_calls = get_user_stats()
    
    stats_text = f"""📊 Bot Statistics 📊

Total Users: {total_users}
Total API Calls: {total_api_calls}
Today's API Calls: {today_api_calls}
Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""
    
    bot.reply_to(message, stats_text)

@bot.message_handler(commands=['apistats'])
def apistats_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_USERIDS:
        bot.reply_to(message, "❌ Access Denied! Admin only command.")
        return
    
    total_users, total_api_calls, today_api_calls = get_user_stats()
    
    api_stats_text = f"""🔧 API Statistics 🔧

Total API Calls: {total_api_calls}
Today's API Calls: {today_api_calls}
Average per User: {total_api_calls/max(1, total_users):.2f}
Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""
    
    bot.reply_to(message, api_stats_text)

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_USERIDS:
        bot.reply_to(message, "❌ Access Denied! Admin only command.")
        return
    
    if message.reply_to_message:
        broadcast_message = message.reply_to_message
        users = get_all_users()
        success = 0
        failed = 0
        
        status_msg = bot.reply_to(message, f"📢 Starting broadcast to {len(users)} users...")
        
        for user_id in users:
            try:
                if broadcast_message.text:
                    bot.send_message(user_id, broadcast_message.text)
                elif broadcast_message.photo:
                    bot.send_photo(user_id, broadcast_message.photo[-1].file_id, 
                                 caption=broadcast_message.caption)
                else:
                    bot.copy_message(user_id, message.chat.id, broadcast_message.message_id)
                success += 1
            except:
                failed += 1
        
        result_text = f"""✅ Broadcast Completed!

Sent successfully: {success}
Failed: {failed}
Success rate: {(success/len(users))*100:.1f}%"""
        
        bot.edit_message_text(result_text, chat_id=message.chat.id, message_id=status_msg.message_id)
    else:
        bot.reply_to(message, "❌ Usage: Reply to a message with /broadcast to send it to all users")

# ===== Handle text messages =====
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ Please join all channels first using /start")
        return
        
    if chat_id in user_data:
        bot.reply_to(chat_id, "⚠️ Please send the **target photo** (the face to replace).")
    else:
        bot.reply_to(chat_id, "👋 Welcome! Use /swap to begin face swapping! ✨")

# ===== FLASK KEEP-ALIVE SETUP =====
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Face Swap Bot is running healthy!"

@app.route('/health')
def health():
    return {"status": "healthy", "users_online": len(user_data), "timestamp": datetime.now().isoformat()}

def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def run_bot():
    """Run bot with error handling and auto-restart"""
    while True:
        try:
            print("🤖 Starting Telegram Bot...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Bot crashed: {e}")
            print("🔄 Restarting bot in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    # Start Flask in background thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start bot with auto-restart
    print("🚀 Starting Face Swap Bot...")
    run_bot()
