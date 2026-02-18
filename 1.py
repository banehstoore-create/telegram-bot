import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import re
from keep_alive import keep_alive
keep_alive()
# ================== تنظیمات ==================
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
ADMIN_ID = 6690559792  # آیدی عددی تلگرام خودت

bot = telebot.TeleBot(BOT_TOKEN)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ================== منوی شروع ==================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "📞 پشتیبانی")

    bot.send_message(
        message.chat.id,
        "👋 به ربات فروشگاه بانه استور خوش آمدید\n"
        "لطفاً از منوی زیر استفاده کنید:",
        reply_markup=markup
    )

# ================== پشتیبانی ==================
@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    markup = types.InlineKeyboardMarkup(row_width=2)

    wa = types.InlineKeyboardButton(
        "📲 واتساپ",
        url="https://wa.me/98" + WHATSAPP[1:]
    )
    tg = types.InlineKeyboardButton(
        "💬 تلگرام",
        url="https://t.me/share/url?text=سلام،%20برای%20پشتیبانی%20پیام%20می‌دهم"
    )

    markup.add(wa, tg)

    bot.send_message(
        message.chat.id,
        "📞 ارتباط با پشتیبانی بانه استور:",
        reply_markup=markup
    )

# ================== دسته‌بندی محصولات ==================
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products(message):
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer"),
        types.InlineKeyboardButton("🥘 لوازم پخت‌وپز", url="https://banehstoore.ir/product-category/cookware"),
        types.InlineKeyboardButton("🧹 جاروبرقی", url="https://banehstoore.ir/product-category/vacuum-cleaner"),
        types.InlineKeyboardButton("🍲 غذاساز و خردکن", url="https://banehstoore.ir/product-category/food-processor"),
        types.InlineKeyboardButton("🔥 سماور برقی", url="https://banehstoore.ir/product-category/electric-samovar"),
        types.InlineKeyboardButton("🛍 مشاهده همه محصولات", url="https://banehstoore.ir")
    )

    bot.send_message(
        message.chat.id,
        "🛒 دسته‌بندی محصولات بانه استور:",
        reply_markup=markup
    )

# ================== دریافت اطلاعات محصول ==================
def fetch_product(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.find("h1").get_text(strip=True)

    image = None
    og = soup.find("meta", property="og:image")
    if og:
        image = og.get("content")

    price = "تماس بگیرید"
    for span in soup.find_all("span"):
        txt = span.get_text(strip=True).replace(",", "")
        if txt.isdigit() and len(txt) >= 5:
            price = span.get_text(strip=True) + " تومان"
            break

    stock = "✅ موجود"
    if "ناموجود" in soup.text:
        stock = "❌ ناموجود"

    return title, image, price, stock

# ================== دریافت لینک محصول و ارسال به کانال ==================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and re.search(r'https?://banehstoore.ir', m.text or ""))
def handle_product_link(message):
    bot.send_message(message.chat.id, "⏳ در حال پردازش لینک محصول...")

    try:
        title, image, price, stock = fetch_product(message.text)

        caption = f"""
🛍 **{title}**

💰 قیمت: {price}
📦 وضعیت: {stock}

🚚 ارسال سریع به سراسر کشور  
💯 ضمانت اصالت کالا  
🤝 خرید مطمئن از بانه استور
"""

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🛒 خرید محصول", "url": message.text},
                    {"text": "📲 تماس در واتساپ", "url": f"https://wa.me/98{WHATSAPP[1:]}"}
                ]
            ]
        }

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        data = {
            "chat_id": CHANNEL_ID,
            "photo": image,
            "caption": caption,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }

        requests.post(url, json=data)

        bot.send_message(message.chat.id, "✅ محصول با موفقیت در کانال منتشر شد")

    except Exception:
        bot.send_message(message.chat.id, "❌ خطا در پردازش یا ارسال محصول")

# ================== پیام‌های متفرقه ==================
@bot.message_handler(func=lambda m: True)
def other(message):
    bot.send_message(message.chat.id, "👇 لطفاً از دکمه‌های منو استفاده کنید")

# ================== اجرای ربات ==================
bot.infinity_polling(
    timeout=20,
    long_polling_timeout=20
)
