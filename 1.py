import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import os
import re
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# کوکی که در مرحله قبل کپی کردید را در تنظیمات Render در متغیر MY_COOKIE قرار دهید
MY_COOKIE = os.environ.get("MY_COOKIE", "") 
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"
MAP_URL = "https://maps.app.goo.gl/eWv6njTbL8ivfbYa6"
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# هدر برای عبور از سد امنیتی سایت و نمایش جزئیات فاکتور
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Cookie": MY_COOKIE,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8",
    "Referer": "https://banehstoore.ir/profile/orders/"
}

user_track_data = {}

# ================== تابع استخراج فاکتور (بروزرسانی شده با عکس) ==================
def fetch_order_details_complete(order_id):
    if not MY_COOKIE:
        return "⚠️ مدیر عزیز، لطفاً ابتدا کوکی (MY_COOKIE) را در پنل Render ست کنید."
        
    try:
        url = f"https://banehstoore.ir/profile/order-details/{order_id}/"
        response = requests.get(url, headers=HEADERS, timeout=25)
        
        if response.status_code != 200:
            return f"❌ خطا در اتصال (کد {response.status_code}). احتمالاً کوکی منقضی شده است."
        
        soup = BeautifulSoup(response.text, "html.parser")
        all_text = soup.get_text(separator=" ", strip=True)

        # جستجوی اطلاعات بر اساس کلمات کلیدی موجود در اسکرین‌شات شما
        def get_data(pattern):
            match = re.search(pattern, all_text)
            return match.group(1).strip() if match else "نامشخص"

        receiver = get_data(r"تحویل گیرنده\s*[:：]\s*([^👤📍🛒💰🚩]+)")
        phone = get_data(r"شماره تماس\s*[:：]\s*([\d]+)")
        address = get_data(r"ارسال به\s*[:：]\s*([^👤📍🛒💰🚩]+)")
        total_price = get_data(r"مبلغ کل\s*[:：]\s*([\d,]+)\s*تومان")
        status = get_data(r"وضعیت\s*[:：]\s*([^👤📍🛒💰🚩]+)")

        # استخراج نام محصول از باکس محصولات
        product_name = "جهت مشاهده جزئیات بیشتر به سایت مراجعه کنید"
        product_box = soup.find(string=re.compile(r"مدل|سرخ کن|اسپرسو", re.I))
        if product_box:
            product_name = product_box.parent.get_text(strip=True)

        # ساخت فاکتور نهایی برای نمایش در تلگرام
        res = f"📑 **جزئیات فاکتور سفارش {order_id}**\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"👤 **تحویل گیرنده:** {receiver.split('شماره')[0].strip()}\n"
        res += f"📞 **شماره تماس:** `{phone}`\n"
        res += f"📍 **آدرس:** {address.split('مبلغ کل')[0].strip()}\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"🛒 **محصول:** {product_name}\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"🚩 **وضعیت:** {status.split('پرداخت')[0].strip()}\n"
        res += f"💰 **مبلغ کل پرداختی:** {total_price} تومان\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += "✅ بانه استور - مرجع لوازم خانگی"
        return res
    except Exception as e:
        return f"⚠️ خطای فنی: {str(e)}"

# ================== کیبورد و منوها (بدون هیچ حذفیاتی) ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور", 
                     reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products_btn(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛍 مشاهده فروشگاه", url="https://banehstoore.ir/products"))
    bot.send_message(message.chat.id, "🛒 لیست محصولات در وب‌سایت ما:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support_btn(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💬 پیام در واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"),
        types.InlineKeyboardButton("📍 لوکیشن فروشگاه", url=MAP_URL)
    )
    bot.send_message(message.chat.id, f"📞 شماره تماس: {PHONE_NUMBER}\nبرای ارتباط آنلاین از دکمه‌های زیر استفاده کنید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def channel_btn(message):
    bot.send_message(message.chat.id, f"📢 آخرین تخفیف‌ها در کانال تلگرام:\n{CHANNEL_ID}")

# ================== فرآیند پیگیری سفارش ==================
@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 تایید و ارسال شماره موبایل", request_contact=True))
    msg = bot.send_message(message.chat.id, "🔐 برای امنیت اطلاعات فاکتور، ابتدا شماره موبایل خود را تایید کنید:", reply_markup=markup)
    bot.register_next_step_handler(msg, track_phone)

def track_phone(message):
    if message.contact:
        user_track_data[message.chat.id] = {'phone': message.contact.phone_number}
        msg = bot.send_message(message.chat.id, "✅ تایید شد. حالا **شماره سفارش** خود را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, track_final)
    else:
        bot.send_message(message.chat.id, "❌ خطا! باید روی دکمه تایید موبایل کلیک کنید.", reply_markup=get_main_keyboard(message.from_user.id))

def track_final(message):
    order_id = message.text.strip()
    if order_id.isdigit():
        bot.send_message(message.chat.id, "⏳ در حال دریافت جزئیات فاکتور از سایت...")
        invoice = fetch_order_details_complete(order_id)
        bot.send_message(message.chat.id, invoice, parse_mode="Markdown", reply_markup=get_main_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ شماره سفارش باید فقط عدد باشد.", reply_markup=get_main_keyboard(message.from_user.id))

# ================== وب‌هوک و اجرا ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot is Running with Full Features</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
