import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import re
import os
from flask import Flask, request

# ================== تنظیمات ==================
# مطمئن شوید در پنل Render در بخش Environment Variables مقدار BOT_TOKEN را تعریف کرده‌اید
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
ADMIN_ID = 6690559792 

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================== شروع و ثبت‌نام ==================
@bot.message_handler(commands=['start'])
def start(message):
    msg = bot.send_message(
        message.chat.id,
        "👋 به ربات فروشگاه بانه استور خوش آمدید\n\n"
        "لطفاً جهت دسترسی به خدمات، ابتدا **نام و نام خانوادگی** خود را ارسال کنید:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_full_name)

def get_full_name(message):
    user_name = message.text
    if not user_name or len(user_name) < 3:
        msg = bot.send_message(message.chat.id, "❌ لطفاً یک نام معتبر وارد کنید:")
        bot.register_next_step_handler(msg, get_full_name)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📲 اشتراک‌گذاری شماره موبایل", request_contact=True)
    markup.add(button)

    msg = bot.send_message(
        message.chat.id,
        f"ممنون {user_name} عزیز. حالا برای تکمیل ثبت‌نام، روی دکمه زیر کلیک کنید تا شماره تماس شما تایید شود:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, get_phone, user_name)

def get_phone(message, user_name):
    if message.contact is not None:
        phone = message.contact.phone_number
    else:
        phone = message.text 

    # ارسال گزارش برای ادمین
    admin_msg = f"👤 **مشتری جدید!**\n\n📝 نام: {user_name}\n📞 شماره: {phone}\n🆔 آیدی: `{message.from_user.id}`"
    bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")

    # نمایش منوی اصلی
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "📞 پشتیبانی")
    bot.send_message(message.chat.id, "✅ ثبت‌نام موفق! از منو استفاده کنید:", reply_markup=markup)

# ================== پشتیبانی و محصولات ==================
@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📲 واتساپ", url="https://wa.me/98" + WHATSAPP[1:]),
        types.InlineKeyboardButton("💬 تلگرام ادمین", url=f"tg://user?id={ADMIN_ID}")
    )
    bot.send_message(message.chat.id, "📞 ارتباط با ما:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer"),
        types.InlineKeyboardButton("🛍 مشاهده سایت", url="https://banehstoore.ir")
    )
    bot.send_message(message.chat.id, "🛒 دسته‌بندی محصولات:", reply_markup=markup)

# ================== استخراج و ارسال محصول (ادمین) ==================
def fetch_product(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("h1").get_text(strip=True)
    image = soup.find("meta", property="og:image")["content"] if soup.find("meta", property="og:image") else None
    
    price = "تماس بگیرید"
    price_tag = soup.find("p", class_="price")
    if price_tag: price = price_tag.get_text(strip=True)
    
    stock = "✅ موجود" if "ناموجود" not in soup.text else "❌ ناموجود"
    return title, image, price, stock

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and "banehstoore.ir/product/" in (m.text or ""))
def handle_product_link(message):
    try:
        title, image, price, stock = fetch_product(message.text)
        caption = f"🛍 *{title}*\n💰 قیمت: {price}\n📦 وضعیت: {stock}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 خرید", url=message.text))
        bot.send_photo(CHANNEL_ID, image, caption=caption, parse_mode="Markdown", reply_markup=markup)
        bot.send_message(ADMIN_ID, "✅ در کانال منتشر شد.")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ خطا: {e}")

# ================== WEBHOOK & FLASK ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    # آدرس URL اختصاصی شما در رندر
    bot.set_webhook(url='https://telegram-bot-5-qw7c.onrender.com/' + BOT_TOKEN)
    return "<h1>Bot is Running! Webhook Set.</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
