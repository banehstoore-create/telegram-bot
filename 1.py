import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import os
import threading
import time
import json
from flask import Flask, request

# ================== تنظیمات اصلی (بدون تغییر) ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"

# توکن و آدرس سایت میکسین
MIXIN_API_KEY = "XfixI1ex7mrBCtJDX1NvopQ0lFOQJjQ9cmdZd5tBCARMaOsLKzzsgHj-GZtTDtkenCq0TSf4WTWEJoqclEQqLQ"
MIXIN_API_URL = "https://banehstoore.ir/api/management/v1/customers/"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ================== مدیریت کاربران (جدید: جلوگیری از ثبت‌نام مجدد) ==================
USERS_FILE = "registered_users.json"

# بارگذاری لیست کاربران از فایل برای تشخیص کاربران قدیمی
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

# ================== مانیتورینگ سایت (اصلاح شده برای پایداری) ==================
last_seen_customer_id = None
monitor_started = False 

def monitor_mixin_site():
    global last_seen_customer_id, monitor_started
    monitor_started = True
    
    # ارسال پیام تایید بیداری ربات به ادمین
    try:
        bot.send_message(ADMIN_ID, "🚀 سیستم مانیتورینگ سایت بانه استور فعال شد.\n(هر ۵ دقیقه بررسی می‌شود)")
    except:
        pass
    
    while True:
        try:
            headers = {"Authorization": f"Api-Key {MIXIN_API_KEY}"}
            response = requests.get(MIXIN_API_URL, headers=headers, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                customers = data.get('results', [])
                
                if customers:
                    latest_customer = customers[0]
                    current_id = latest_customer.get('id')
                    
                    if last_seen_customer_id is None:
                        last_seen_customer_id = current_id
                    elif current_id > last_seen_customer_id:
                        first_name = latest_customer.get('first_name', '')
                        last_name = latest_customer.get('last_name', '')
                        phone = latest_customer.get('phone_number', 'نامشخص')
                        
                        report = f"🆕 **ثبت‌نام جدید در سایت!**\n---------------------------\n👤 نام: {first_name} {last_name}\n📞 شماره: {phone}\n---------------------------"
                        bot.send_message(ADMIN_ID, report)
                        last_seen_customer_id = current_id
            elif response.status_code == 401:
                bot.send_message(ADMIN_ID, "⚠️ خطای API سایت: توکن نامعتبر است.")
        except Exception as e:
            print(f"Monitor Loop Error: {e}")
            
        time.sleep(300)

# ================== بخش ربات تلگرام (ثبت‌نام و منو) ==================

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "📞 پشتیبانی")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # اگر کاربر قبلاً ثبت‌نام کرده، مستقیم منو را نشان بده
    if user_id in registered_users:
        bot.send_message(message.chat.id, "👋 به فروشگاه بانه استور خوش آمدید.", reply_markup=main_menu())
    else:
        msg = bot.send_message(message.chat.id, "👋 خوش آمدید! لطفاً جهت ثبت‌نام، **نام و نام خانوادگی** خود را وارد کنید:")
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
    phone = message.contact.phone_number if message.contact else message.text

    # ذخیره در لیست محلی
    save_user(user_id)
    
    bot.send_message(ADMIN_ID, f"👤 **مشتری جدید تلگرام!**\n📝 نام: {user_full_name}\n📞 شماره: {phone}\n🆔 آیدی: `{user_id}`")
    bot.send_message(message.chat.id, "✅ ثبت‌نام شما با موفقیت انجام شد.", reply_markup=main_menu())

# ================== پشتیبانی و محصولات (بدون تغییر) ==================
@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📲 واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"))
    bot.send_message(message.chat.id, "📞 برای پشتیبانی پیام دهید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer"),
        types.InlineKeyboardButton("🛍 مشاهده همه", url="https://banehstoore.ir")
    )
    bot.send_message(message.chat.id, "🛒 دسته‌بندی محصولات بانه استور:", reply_markup=markup)

# ================== وب‌هوک و بیدارساز ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    # فعال‌سازی مانیتورینگ سایت با اولین بازدید از لینک رندر
    if not monitor_started:
        threading.Thread(target=monitor_mixin_site, daemon=True).start()
    
    bot.remove_webhook()
    bot.set_webhook(url='https://telegram-bot-5-qw7c.onrender.com/' + BOT_TOKEN)
    return "<h1>Bot is Active!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
