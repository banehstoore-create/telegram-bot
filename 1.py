import telebot
from telebot import types
import requests
import os
import threading
import time
import json
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
WHATSAPP = "09180514202"

# توکن و آدرس سایت
MIXIN_API_KEY = "XfixI1ex7mrBCtJDX1NvopQ0lFOQJjQ9cmdZd5tBCARMaOsLKzzsgHj-GZtTDtkenCq0TSf4WTWEJoqclEQqLQ"
MIXIN_API_URL = "https://banehstoore.ir/api/management/v1/customers/"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# حافظه کاربران تلگرام
USERS_FILE = "users_db.json"
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f: registered_users = json.load(f)
else: registered_users = []

def save_user(user_id):
    if user_id not in registered_users:
        registered_users.append(user_id)
        with open(USERS_FILE, "w") as f: json.dump(registered_users, f)

last_seen_customer_id = None
monitor_started = False # برای جلوگیری از اجرای چندباره

# ================== مانیتورینگ هوشمند ==================
def monitor_mixin_site():
    global last_seen_customer_id, monitor_started
    monitor_started = True
    
    # ارسال پیام تست به ادمین برای اطمینان از بیدار شدن کد
    bot.send_message(ADMIN_ID, "✅ ربات بیدار شد و مانیتورینگ سایت فعال است.")
    
    while True:
        try:
            headers = {"Authorization": f"Api-Key {MIXIN_API_KEY}"}
            response = requests.get(MIXIN_API_URL, headers=headers, timeout=20)
            
            if response.status_code == 200:
                customers = response.json().get('results', [])
                if customers:
                    current_id = customers[0].get('id')
                    if last_seen_customer_id is not None and current_id > last_seen_customer_id:
                        c = customers[0]
                        msg = f"🆕 **ثبت‌نام جدید در سایت!**\n👤 {c.get('first_name')} {c.get('last_name')}\n📞 {c.get('phone_number')}"
                        bot.send_message(ADMIN_ID, msg)
                    last_seen_customer_id = current_id
            elif response.status_code == 401:
                bot.send_message(ADMIN_ID, "⚠️ خطای توکن: API Key سایت اشتباه است.")
        except Exception as e:
            print(f"Loop Error: {e}")
        
        time.sleep(300) # چک کردن هر 5 دقیقه

# ================== ربات تلگرام ==================
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id in registered_users:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🛒 محصولات", "📞 پشتیبانی")
        bot.send_message(message.chat.id, "👋 خوش آمدید مجدد!", reply_markup=markup)
    else:
        msg = bot.send_message(message.chat.id, "👋 لطفاً نام و نام خانوادگی خود را وارد کنید:")
        bot.register_next_step_handler(msg, get_name)

def get_name(message):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 ارسال شماره", request_contact=True))
    msg = bot.send_message(message.chat.id, f"ممنون {name}. شماره خود را تایید کنید:", reply_markup=markup)
    bot.register_next_step_handler(msg, get_phone, name)

def get_phone(message, name):
    phone = message.contact.phone_number if message.contact else message.text
    save_user(message.from_user.id)
    bot.send_message(ADMIN_ID, f"👤 **مشتری جدید تلگرام:**\n📝 {name}\n📞 {phone}")
    bot.send_message(message.chat.id, "✅ ثبت‌نام شد.")

# ================== وب‌هوک و بیدارساز ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    # به محض باز شدن آدرس اصلی، مانیتورینگ شروع میشود
    if not monitor_started:
        threading.Thread(target=monitor_mixin_site, daemon=True).start()
    
    bot.remove_webhook()
    bot.set_webhook(url='https://telegram-bot-5-qw7c.onrender.com/' + BOT_TOKEN)
    return "<h1>Monitor Active!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
