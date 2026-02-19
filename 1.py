import telebot
from telebot import types
import requests
import os
import threading
import time
from flask import Flask, request

# ================== تنظیمات اصلی ==================
# توکن ربات تلگرام را حتما در پنل Render در بخش Environment Variables ست کنید
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"

# 🔑 توکن سایت خودت را اینجا بین دو کوتیشن قرار بده
MIXIN_API_KEY = "XfixI1ex7mrBCtJDX1NvopQ0lFOQJjQ9cmdZd5tBCARMaOsLKzzsgHj-GZtTDtkenCq0TSf4WTWEJoqclEQqLQ"

# آدرس API مشتریان سایت بانه استور
MIXIN_API_URL = "https://banehstoore.ir/api/management/v1/customers/"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# برای جلوگیری از ارسال پیام تکراری
last_seen_customer_id = None

# ================== تابع مانیتورینگ سایت (میکسین) ==================
def monitor_mixin_site():
    global last_seen_customer_id
    print("Monitoring Mixin Site started...")
    
    while True:
        try:
            # ارسال درخواست به سایت با استفاده از توکن شما
            headers = {
                "Authorization": f"Api-Key {MIXIN_API_KEY}",
                "Content-Type": "application/json"
            }
            response = requests.get(MIXIN_API_URL, headers=headers, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                # در میکسین لیست مشتریان معمولاً در فیلد results است
                customers = data.get('results', [])
                
                if customers:
                    # مشتری اول در لیست، جدیدترین مشتری است
                    latest_customer = customers[0]
                    current_id = latest_customer.get('id')
                    
                    # اگر اولین بار است که چک میکنیم، فقط آیدی را ذخیره کن
                    if last_seen_customer_id is None:
                        last_seen_customer_id = current_id
                    
                    # اگر آیدی جدیدتر از قبلی بود، یعنی مشتری جدید داریم
                    elif current_id > last_seen_customer_id:
                        first_name = latest_customer.get('first_name', '')
                        last_name = latest_customer.get('last_name', '')
                        phone = latest_customer.get('phone_number', 'بدون شماره')
                        
                        report = f"""
🆕 **ثبت‌نام جدید در سایت!**
---------------------------
👤 نام: {first_name} {last_name}
📞 شماره: {phone}
📅 تاریخ: {latest_customer.get('date_joined', 'نامشخص')}
---------------------------
🌐 banehstoore.ir
"""
                        bot.send_message(ADMIN_ID, report, parse_mode="Markdown")
                        last_seen_customer_id = current_id
            
            elif response.status_code == 401:
                print("Error: Mixin Token is invalid!")
                
        except Exception as e:
            print(f"Mixin Monitor Error: {e}")
            
        # هر 5 دقیقه یکبار چک کن (300 ثانیه)
        time.sleep(300)

# شروع به کار مانیتورینگ در یک رشته جداگانه
threading.Thread(target=monitor_mixin_site, daemon=True).start()

# ================== بخش ربات تلگرام (ثبت‌نام مشتری) ==================
@bot.message_handler(commands=['start'])
def start(message):
    msg = bot.send_message(
        message.chat.id, 
        "👋 به ربات بانه استور خوش آمدید\n\nلطفاً جهت دسترسی به منو، **نام و نام خانوادگی** خود را وارد کنید:"
    )
    bot.register_next_step_handler(msg, get_name)

def get_name(message):
    user_full_name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 اشتراک‌گذاری شماره موبایل", request_contact=True))
    
    msg = bot.send_message(
        message.chat.id, 
        f"ممنون {user_full_name} عزیز. حالا برای تایید، دکمه زیر را لمس کنید:", 
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, get_phone, user_full_name)

def get_phone(message, user_full_name):
    phone = message.contact.phone_number if message.contact else message.text
    
    # گزارش به ادمین درباره کاربر تلگرام
    bot.send_message(
        ADMIN_ID, 
        f"👤 **مشتری جدید در ربات!**\n📝 نام: {user_full_name}\n📞 شماره: {phone}\n🆔 آیدی: `{message.from_user.id}`",
        parse_mode="Markdown"
    )
    
    # منوی اصلی
    main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    main_menu.add("🛒 محصولات", "📞 پشتیبانی")
    bot.send_message(message.chat.id, "✅ ثبت‌نام شما با موفقیت انجام شد.", reply_markup=main_menu)

# ================== پشتیبانی و محصولات ==================
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
    bot.send_message(message.chat.id, "🛒 محصولات بانه استور:", reply_markup=markup)

# ================== وب‌هوک و اجرا ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    # آدرس رندر خود را اینجا چک کنید
    bot.set_webhook(url='https://telegram-bot-5-qw7c.onrender.com/' + BOT_TOKEN)
    return "<h1>Bot & Site Monitor is running!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
