import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import os
import re
import html
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_COOKIE = os.environ.get("MY_COOKIE", "") 
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# هدر مطابق با اسکرین‌شات Network شما
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Cookie": MY_COOKIE,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://banehstoore.ir/profile/",
    "Connection": "keep-alive"
}

# ================== تابع استخراج فاکتور ==================
def fetch_order_details_complete(order_id):
    if not MY_COOKIE:
        return "⚠️ متغیر MY_COOKIE در رندر تنظیم نشده است."
        
    try:
        url = f"https://banehstoore.ir/profile/order-details/{order_id}/"
        response = requests.get(url, headers=HEADERS, timeout=25)
        
        if "login" in response.url or "ورود" in response.text:
            return "❌ <b>خطا:</b> سایت اجازه ورود نداد. احتمالاً کوکی منقضی شده است."

        soup = BeautifulSoup(response.text, "html.parser")
        
        # استخراج داده‌ها بر اساس متن‌های موجود در عکس شما
        def get_val(label):
            target = soup.find(string=re.compile(label))
            if target:
                # مقدار معمولاً در تگ بعدی یا والد تگ بعدی است
                return html.escape(target.parent.get_text().replace(label, "").replace(":", "").strip())
            return "یافت نشد"

        receiver = get_val("تحویل گیرنده")
        phone = get_val("شماره تماس")
        address = get_val("ارسال به")
        price = get_val("مبلغ کل")
        status = get_val("وضعیت")

        res = f"<b>📑 جزئیات فاکتور شماره {order_id}</b>\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"👤 <b>تحویل گیرنده:</b> {receiver}\n"
        res += f"📞 <b>شماره تماس:</b> <code>{phone}</code>\n"
        res += f"📍 <b>آدرس:</b> {address}\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"🚩 <b>وضعیت:</b> {status}\n"
        res += f"💰 <b>مبلغ کل:</b> {price}\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += "✅ بانه استور - مرجع لوازم خانگی"
        return res

    except Exception as e:
        return f"⚠️ خطای سیستمی: {str(e)}"

# ================== دکمه‌ها (بدون تغییر موارد قبلی) ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 خوش آمدید", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 تایید شماره موبایل", request_contact=True))
    bot.send_message(message.chat.id, "🔐 ابتدا موبایل خود را تایید کنید:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def contact(message):
    msg = bot.send_message(message.chat.id, "🔢 شماره سفارش را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, track_final)

def track_final(message):
    if message.text.isdigit():
        bot.send_message(message.chat.id, "⏳ در حال دریافت فاکتور...")
        res = fetch_order_details_complete(message.text)
        bot.send_message(message.chat.id, res, parse_mode="HTML", reply_markup=get_main_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ فقط عدد وارد کنید.")

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def p(m): bot.send_message(m.chat.id, "🛒 https://banehstoore.ir/products")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def s(m): bot.send_message(m.chat.id, f"📞 {PHONE_NUMBER}\n💬 {WHATSAPP}")

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def c(m): bot.send_message(m.chat.id, f"📢 {CHANNEL_ID}")

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot is Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
