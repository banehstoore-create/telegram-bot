import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import re
import os
from flask import Flask, request

# ================== تنظیمات ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
ADMIN_ID = 6690559792 # آیدی عددی شما

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
    # هدایت کاربر به مرحله دریافت نام
    bot.register_next_step_handler(msg, get_full_name)

def get_full_name(message):
    user_name = message.text
    if not user_name or len(user_name) < 3:
        msg = bot.send_message(message.chat.id, "❌ لطفاً یک نام معتبر وارد کنید:")
        bot.register_next_step_handler(msg, get_full_name)
        return

    # درخواست شماره تماس با دکمه شیشه‌ای یا کیبورد
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
    # چک می‌کنیم که آیا کاربر شماره را فرستاده یا متن تایپ کرده
    if message.contact is not None:
        phone = message.contact.phone_number
    else:
        phone = message.text # اگر دستی تایپ کرد

    # --- ارسال گزارش برای ادمین ---
    admin_msg = f"""
👤 **مشتری جدید ثبت‌نام کرد!**
---------------------------
📝 نام: {user_name}
📞 شماره: {phone}
🆔 آیدی: `{message.from_user.id}`
🔗 یوزرنیم: @{message.from_user.username if message.from_user.username else "ندارد"}
"""
    bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")

    # --- نمایش منوی اصلی به کاربر ---
    show_main_menu(message.chat.id, user_name)

def show_main_menu(chat_id, user_name):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "📞 پشتیبانی")
    
    bot.send_message(
        chat_id,
        f"✅ ثبت‌نام شما با موفقیت انجام شد.\n"
        "حالا می‌توانید از منوی زیر استفاده کنید:",
        reply_markup=markup
    )

# ================== پشتیبانی و محصولات ==================
@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📲 واتساپ", url="https://wa.me/98" + WHATSAPP[1:]),
        types.InlineKeyboardButton("💬 تلگرام ادمین", url=f"tg://user?id={ADMIN_ID}")
    )
    bot.send_message(message.chat.id, "📞 راه‌های ارتباطی با ما:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer"),
        types.InlineKeyboardButton("🧹 جاروبرقی", url="https://banehstoore.ir/product-category/vacuum-cleaner"),
        types.InlineKeyboardButton("🍲 غذاساز", url="https://banehstoore.ir/product-category/food-processor"),
        types.InlineKeyboardButton("🛍 مشاهده کل سایت", url="https://banehstoore.ir")
    )
    bot.send_message(message.chat.id, "🛒 دسته‌بندی محصولات بانه استور:", reply_markup=markup)

# ================== استخراج اطلاعات محصول (Scraper) ==================
def fetch_product(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.find("h1").get_text(strip=True)
    
    # پیدا کردن تصویر
    image = None
    og = soup.find("meta", property="og:image")
    if og: image = og.get("content")

    # قیمت هوشمند (برای ووکامرس)
    price = "تماس بگیرید"
    price_tag = soup.find("p", class_="price")
    if price_tag:
        price = price_tag.get_text(strip=True)

    stock = "✅ موجود در انبار"
    if "ناموجود" in soup.text:
        stock = "❌ ناموجود"

    return title, image, price, stock

# ================== ارسال محصول به کانال (فقط ادمین) ==================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and "banehstoore.ir/product/" in (m.text or ""))
def handle_product_link(message):
    wait_msg = bot.send_message(message.chat.id, "⏳ در حال استخراج اطلاعات محصول...")
    try:
        title, image, price, stock = fetch_product(message.text)

        caption = f"🛍 *{title}*\n\n💰 قیمت: {price}\n📦 وضعیت: {stock}\n\n🚚 ارسال به سراسر کشور\n💯 ضمانت اصالت کالا"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 خرید آنلاین", url=message.text))
        markup.add(types.InlineKeyboardButton("📲 سفارش در واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"))

        bot.send_photo(CHANNEL_ID, image, caption=caption, parse_mode="Markdown", reply_markup=markup)
        bot.delete_message(message.chat.id, wait_msg.message_id)
        bot.send_message(message.chat.id, "✅ محصول در کانال منتشر شد.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا در پردازش: {str(e)}")

# ================== Webhook Setup ==================
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return "Forbidden", 403

@app.route('/')
def home():
    return "Baneh Store Bot is Active!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
