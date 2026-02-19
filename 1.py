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
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"

# 🔑 توکن سایت خود را اینجا قرار دهید
MIXIN_API_KEY = "XfixI1ex7mrBCtJDX1NvopQ0lFOQJjQ9cmdZd5tBCARMaOsLKzzsgHj-GZtTDtkenCq0TSf4WTWEJoqclEQqLQ"
MIXIN_API_URL = "https://banehstoore.ir/api/management/v1/customers/"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# فایل ذخیره کاربران ثبت‌نام شده
USERS_FILE = "registered_users.json"

# بارگذاری لیست کاربران از فایل
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        registered_users = json.load(f)
else:
    registered_users = []

def save_user(user_id):
    if user_id not in registered_users:
        registered_users.append(user_id)
        with open(USERS_FILE, "w") as f:
            json.dump(registered_users, f)

# برای جلوگیری از ارسال پیام تکراری از سایت
last_seen_customer_id = None

# ================== تابع مانیتورینگ سایت (نسخه اصلاح شده) ==================
def monitor_mixin_site():
    global last_seen_customer_id
    # یکبار پیام میدهد که بفهمید مانیتورینگ استارت خورده
    try:
        bot.send_message(ADMIN_ID, "🚀 سیستم مانیتورینگ سایت بانه استور فعال شد.\nهر ۵ دقیقه سایت چک می‌شود.")
    except:
        pass
    
    while True:
        try:
            headers = {
                "Authorization": f"Api-Key {MIXIN_API_KEY}",
                "Accept": "application/json"
            }
            # اضافه کردن پارامتر برای اطمینان از دریافت جدیدترین‌ها
            response = requests.get(MIXIN_API_URL, headers=headers, timeout=25)
            
            if response.status_code == 200:
                data = response.json()
                # میکسین معمولا داده ها را در 'results' میفرستد
                customers = data.get('results', [])
                
                if customers:
                    # گرفتن اولین نفر (جدیدترین)
                    latest_customer = customers[0]
                    current_id = latest_customer.get('id')
                    
                    if last_seen_customer_id is None:
                        # در اجرای اول فقط آیدی فعلی را ذخیره کن
                        last_seen_customer_id = current_id
                        print(f"Initial ID set to: {current_id}")
                    
                    elif current_id > last_seen_customer_id:
                        # اگر آیدی بزرگتر شد یعنی مشتری واقعا جدید است
                        first_name = latest_customer.get('first_name', '')
                        last_name = latest_customer.get('last_name', '')
                        phone = latest_customer.get('phone_number', 'بدون شماره')
                        
                        report = f"""
🆕 **ثبت‌نام جدید در سایت بانه استور!**
---------------------------
👤 نام: {first_name} {last_name}
📞 شماره: {phone}
🆔 آیدی سیستمی: {current_id}
---------------------------
"""
                        bot.send_message(ADMIN_ID, report)
                        last_seen_customer_id = current_id
            else:
                print(f"Mixin Error: {response.status_code}")
                # اگر توکن اشتباه باشد اینجا متوجه میشوید
                if response.status_code == 401:
                    bot.send_message(ADMIN_ID, "⚠️ اخطار: توکن سایت (Mixin API Key) معتبر نیست!")

        except Exception as e:
            print(f"Monitoring Loop Error: {e}")
            
        # زمان انتظار (۳۰۰ ثانیه = ۵ دقیقه)
        time.sleep(300)

# ================== بخش ربات تلگرام ==================

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "📞 پشتیبانی")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # چک کردن اینکه آیا کاربر قبلاً ثبت‌نام کرده است یا خیر
    if user_id in registered_users:
        bot.send_message(message.chat.id, "👋 خوش آمدید مجدد به بانه استور!", reply_markup=main_menu())
    else:
        msg = bot.send_message(message.chat.id, "👋 خوش آمدید! لطفاً جهت ثبت‌نام، **نام و نام خانوادگی** خود را بفرستید:")
        bot.register_next_step_handler(msg, get_name)

def get_name(message):
    user_full_name = message.text
    if not user_full_name or len(user_full_name) < 3:
        msg = bot.send_message(message.chat.id, "❌ نام معتبر نیست. دوباره ارسال کنید:")
        bot.register_next_step_handler(msg, get_name)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 اشتراک‌گذاری شماره موبایل", request_contact=True))
    msg = bot.send_message(message.chat.id, f"ممنون {user_full_name}. حالا شماره خود را تایید کنید:", reply_markup=markup)
    bot.register_next_step_handler(msg, get_phone, user_full_name)

def get_phone(message, user_full_name):
    user_id = message.from_user.id
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    # ذخیره کاربر در لیست ثبت‌نام شده‌ها
    save_user(user_id)
    
    bot.send_message(ADMIN_ID, f"👤 **مشتری جدید تلگرام!**\n📝 نام: {user_full_name}\n📞 شماره: {phone}")
    bot.send_message(message.chat.id, "✅ ثبت‌نام شما با موفقیت انجام شد.", reply_markup=main_menu())

# ================== مدیریت دکمه‌ها ==================
@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📲 واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"))
    bot.send_message(message.chat.id, "ارتباط با واحد فروش و پشتیبانی:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer")
    )
    bot.send_message(message.chat.id, "🛒 دسته‌بندی محصولات بانه استور:", reply_markup=markup)

# ================== وب‌هوک و فلکسا ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://telegram-bot-5-qw7c.onrender.com/' + BOT_TOKEN)
    return "<h1>Bot is Active!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
