import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import os
import threading
import time
import json
from flask import Flask, request

# ================== تنظیمات اصلی (ثابت) ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"

# توکن شما
MIXIN_API_KEY = "XfixI1ex7mrBCtJDX1NvopQ0lFOQJjQ9cmdZd5tBCARMaOsLKzzsgHj-GZtTDtkenCq0TSf4WTWEJoqclEQqLQ"

# آدرس‌های احتمالی برای دریافت لیست کاربران
API_URLS = [
    "https://banehstoore.ir/api/management/v1/customers/",
    "https://banehstoore.ir/api/v1/users/",
    "https://banehstoore.ir/api/v1/customers/"
]

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ================== مدیریت دیتابیس کاربران تلگرام ==================
USERS_FILE = "registered_users.json"
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f: registered_users = json.load(f)
else: registered_users = []

def save_user(user_id):
    if user_id not in registered_users:
        registered_users.append(user_id)
        with open(USERS_FILE, "w") as f: json.dump(registered_users, f)

# ================== مانیتورینگ هوشمند سایت ==================
last_customer_count = None
monitor_started = False 

def monitor_mixin_site():
    global last_customer_count, monitor_started
    monitor_started = True
    
    bot.send_message(ADMIN_ID, "🔍 مانیتورینگ بانه استور بیدار شد.\nدر حال جستجوی لیست مشتریان در دیتابیس سایت...")
    
    while True:
        success = False
        for url in API_URLS:
            try:
                headers = {
                    "Authorization": f"Api-Key {MIXIN_API_KEY}",
                    "Accept": "application/json"
                }
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    # بررسی فیلدهای مختلف که ممکن است لیست در آن‌ها باشد
                    customers = data.get('results', data.get('data', data.get('users', [])))
                    current_count = data.get('count', len(customers))
                    
                    if current_count > 0 or last_customer_count is not None:
                        if last_customer_count is None:
                            last_customer_count = current_count
                            bot.send_message(ADMIN_ID, f"✅ اتصال با موفقیت برقرار شد!\nتعداد مشتریان شناسایی شده: {current_count}\nآدرس فعال: {url}")
                        
                        elif current_count > last_customer_count:
                            if customers:
                                latest = customers[0]
                                name = f"{latest.get('first_name', '')} {latest.get('last_name', '')}"
                                phone = latest.get('phone_number', latest.get('mobile', 'نامشخص'))
                                bot.send_message(ADMIN_ID, f"🆕 **ثبت‌نام جدید در سایت!**\n---------------------------\n👤 نام: {name}\n📞 شماره: {phone}\n---------------------------")
                            last_customer_count = current_count
                        
                        success = True
                        break # اگر این آدرس جواب داد، بقیه را چک نکن
            except:
                continue
        
        if not success and last_customer_count is None:
            # اگر هیچ آدرسی دیتا نداشت
            print("No valid data found in provided URLs.")
            
        time.sleep(300)

# ================== بخش ربات تلگرام (ثابت) ==================
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🛒 محصولات", "📞 پشتیبانی"); return m

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id in registered_users:
        bot.send_message(message.chat.id, "👋 به فروشگاه بانه استور خوش آمدید.", reply_markup=main_menu())
    else:
        msg = bot.send_message(message.chat.id, "👋 خوش آمدید! لطفاً نام و نام خانوادگی خود را وارد کنید:")
        bot.register_next_step_handler(msg, get_name)

def get_name(message):
    name = message.text
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    m.add(types.KeyboardButton("📲 اشتراک‌گذاری شماره", request_contact=True))
    msg = bot.send_message(message.chat.id, f"ممنون {name}. شماره خود را تایید کنید:", reply_markup=m)
    bot.register_next_step_handler(msg, get_phone, name)

def get_phone(message, name):
    phone = message.contact.phone_number if message.contact else message.text
    save_user(message.from_user.id)
    bot.send_message(ADMIN_ID, f"👤 **مشتری جدید تلگرام!**\n📝 نام: {name}\n📞 شماره: {phone}\n🆔 آیدی: `{message.from_user.id}`")
    bot.send_message(message.chat.id, "✅ ثبت‌نام شما با موفقیت انجام شد.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📲 واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"))
    bot.send_message(message.chat.id, "پشتیبانی بانه استور:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer"),
        types.InlineKeyboardButton("🛍 مشاهده همه", url="https://banehstoore.ir")
    )
    bot.send_message(message.chat.id, "🛒 محصولات بانه استور:", reply_markup=markup)

# ================== وب‌هوک و اجرا ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    if not monitor_started:
        threading.Thread(target=monitor_mixin_site, daemon=True).start()
    bot.remove_webhook()
    bot.set_webhook(url='https://telegram-bot-5-qw7c.onrender.com/' + BOT_TOKEN)
    return "<h1>Monitor Active!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
