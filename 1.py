import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import os
import re
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_COOKIE = os.environ.get("MY_COOKIE", "") 
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"
MAP_URL = "https://maps.app.goo.gl/eWv6njTbL8ivfbYa6"
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# هدر اصلاح شده - استفاده از HTML به جای Markdown برای امنیت بیشتر در ارسال پیام
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Cookie": MY_COOKIE,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9",
    "Referer": "https://banehstoore.ir/profile/orders/"
}

user_track_data = {}

# ================== تابع استخراج فاکتور (بهینه شده با HTML) ==================
def fetch_order_details_complete(order_id):
    if not MY_COOKIE:
        return "⚠️ ابتدا باید MY_COOKIE را در تنظیمات Render وارد کنید."
        
    try:
        print(f"--- شروع دریافت اطلاعات برای سفارش {order_id} ---")
        url = f"https://banehstoore.ir/profile/order-details/{order_id}/"
        
        # اضافه کردن تایم‌اوت و غیرفعال کردن چک کردن SSL برای سرعت بیشتر
        response = requests.get(url, headers=HEADERS, timeout=20, verify=True)
        
        print(f"وضعیت پاسخ سایت: {response.status_code}")
        
        if response.status_code != 200:
            return f"❌ سایت پاسخ نداد (کد {response.status_code}). احتمالاً کوکی منقضی شده است."
        
        if "ورود به حساب" in response.text or "login" in response.url:
            return "🔑 کوکی شما ناقص است. لطفاً وارد سایت شوید و مطمئن شوید sessionid در کوکی هست."

        soup = BeautifulSoup(response.text, "html.parser")
        all_text = soup.get_text(separator=" ", strip=True)

        def get_data(pattern):
            match = re.search(pattern, all_text)
            return match.group(1).strip() if match else "نامشخص"

        receiver = get_data(r"تحویل گیرنده\s*[:：]\s*([^👤📍🛒💰🚩]+)")
        phone = get_data(r"شماره تماس\s*[:：]\s*([\d]+)")
        address = get_data(r"ارسال به\s*[:：]\s*([^👤📍🛒💰🚩]+)")
        total_price = get_data(r"مبلغ کل\s*[:：]\s*([\d,]+)\s*تومان")
        status = get_data(r"وضعیت\s*[:：]\s*([^👤📍🛒💰🚩]+)")

        # استفاده از تگ‌های HTML به جای Markdown برای جلوگیری از هنگ کردن ربات
        res = f"<b>📑 جزئیات فاکتور سفارش {order_id}</b>\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"👤 <b>تحویل گیرنده:</b> {receiver.split('شماره')[0].strip()}\n"
        res += f"📞 <b>شماره تماس:</b> <code>{phone}</code>\n"
        res += f"📍 <b>آدرس:</b> {address.split('مبلغ کل')[0].strip()}\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"🚩 <b>وضعیت:</b> {status.split('پرداخت')[0].strip()}\n"
        res += f"💰 <b>مبلغ کل:</b> {total_price} تومان\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += "✅ بانه استور - مرجع لوازم خانگی"
        
        return res
    except Exception as e:
        print(f"خطای سیستمی: {str(e)}")
        return f"⚠️ خطای فنی در دریافت اطلاعات. لطفا دوباره تلاش کنید."

# ================== سایر دکمه‌ها (بدون تغییر) ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 به بانه استور خوش آمدید", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 تایید و ارسال شماره موبایل", request_contact=True))
    msg = bot.send_message(message.chat.id, "🔐 ابتدا شماره موبایل خود را تایید کنید:", reply_markup=markup)
    bot.register_next_step_handler(msg, track_phone)

def track_phone(message):
    if message.contact:
        msg = bot.send_message(message.chat.id, "🔢 حالا شماره سفارش را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, track_final)
    else:
        bot.send_message(message.chat.id, "❌ لغو شد.", reply_markup=get_main_keyboard(message.from_user.id))

def track_final(message):
    order_id = message.text.strip()
    if order_id.isdigit():
        bot.send_message(message.chat.id, "⏳ در حال دریافت جزئیات فاکتور...")
        invoice = fetch_order_details_complete(order_id)
        # تغییر پارس مود به HTML برای پایداری
        bot.send_message(message.chat.id, invoice, parse_mode="HTML", reply_markup=get_main_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ لطفا فقط عدد وارد کنید.")

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def prod_btn(m): bot.send_message(m.chat.id, "🛒 محصولات: https://banehstoore.ir/products")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def supp_btn(m): bot.send_message(m.chat.id, f"📞 تماس: {PHONE_NUMBER}\n💬 واتساپ: https://wa.me/98{WHATSAPP[1:]}")

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def chan_btn(m): bot.send_message(m.chat.id, f"📢 کانال: {CHANNEL_ID}")

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot is Updated to HTML Mode</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
