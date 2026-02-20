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
MAP_URL = "https://maps.app.goo.gl/eWv6njTbL8ivfbYa6"
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# هدر بسیار پیشرفته برای شبیه‌سازی دقیق مرورگر واقعی
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Cookie": MY_COOKIE,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://banehstoore.ir/profile/orders/",
    "Connection": "keep-alive"
}

# ================== تابع استخراج فاکتور (با دیباگ هوشمند) ==================
def fetch_order_details_complete(order_id):
    if not MY_COOKIE:
        return "⚠️ مدیر عزیز، ابتدا باید کل متن کوکی را در تنظیمات Render و در متغیر <code>MY_COOKIE</code> قرار دهید."
        
    try:
        url = f"https://banehstoore.ir/profile/order-details/{order_id}/"
        # ایجاد یک جلسه (Session) برای پایداری بیشتر
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=30)
        
        # لاگ برای شما در کنسول Render
        print(f"DEBUG: Status Code: {response.status_code}")
        print(f"DEBUG: Redirected to: {response.url}")

        if "login" in response.url or "ورود" in response.text:
            return "❌ <b>عدم دسترسی:</b> سایت ربات را به صفحه ورود هدایت کرد. این یعنی کوکی شما منقضی شده یا اشتباه کپی شده است.\n\n💡 <b>راه حل:</b> دوباره در Kiwi Browser وارد سایت شوید و کل متن <code>document.cookie</code> را کپی کرده و در Render جایگزین کنید."

        soup = BeautifulSoup(response.text, "html.parser")
        all_text = soup.get_text(separator=" ", strip=True)

        def get_clean_data(pattern):
            match = re.search(pattern, all_text)
            val = match.group(1).strip() if match else "یافت نشد"
            return html.escape(val)

        receiver = get_clean_data(r"تحویل گیرنده\s*[:：]\s*([^👤📍🛒💰🚩]+)")
        phone = get_clean_data(r"شماره تماس\s*[:：]\s*([\d]+)")
        address = get_clean_data(r"ارسال به\s*[:：]\s*([^👤📍🛒💰🚩]+)")
        total_price = get_clean_data(r"مبلغ کل\s*[:：]\s*([\d,]+)\s*تومان")
        status = get_clean_data(r"وضعیت\s*[:：]\s*([^👤📍🛒💰🚩]+)")

        res = f"<b>📑 جزئیات فاکتور شماره {order_id}</b>\n"
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
        return f"⚠️ <b>خطای فنی:</b> <code>{html.escape(str(e))}</code>"

# ================== کیبوردها و هندلرها (بدون هیچ حذفیاتی) ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_step_1(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 تایید و ارسال شماره موبایل", request_contact=True))
    bot.send_message(message.chat.id, "🔐 ابتدا شماره موبایل خود را تایید کنید:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    msg = bot.send_message(message.chat.id, "🔢 حالا **شماره سفارش** را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, track_step_2)

def track_step_2(message):
    order_id = message.text.strip()
    if order_id.isdigit():
        bot.send_message(message.chat.id, "⏳ در حال استخراج فاکتور از سایت...")
        invoice = fetch_order_details_complete(order_id)
        bot.send_message(message.chat.id, invoice, parse_mode="HTML", reply_markup=get_main_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ لطفا فقط عدد وارد کنید.")

# دکمه‌های محصولات، پشتیبانی و کانال
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def prod(m): bot.send_message(m.chat.id, "🛒 محصولات بانه استور:\nhttps://banehstoore.ir/products")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def supp(m): bot.send_message(m.chat.id, f"📞 تماس: {PHONE_NUMBER}\n💬 واتساپ: https://wa.me/98{WHATSAPP[1:]}")

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def chan(m): bot.send_message(m.chat.id, f"📢 کانال تلگرام: {CHANNEL_ID}")

# ================== وب‌هوک و اجرا ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot is Ready with Advanced Headers</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
