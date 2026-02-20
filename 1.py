import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import re
import os
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================== توابع کمکی ==================
def fetch_product(url):
    """استخراج اطلاعات محصول از سایت"""
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    
    title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "محصول بانه استور"
    
    image = None
    og = soup.find("meta", property="og:image")
    if og:
        image = og.get("content")

    price = "تماس بگیرید"
    # جستجوی قیمت در تگ‌های قیمت ووکامرس
    price_tag = soup.find("p", class_="price")
    if price_tag:
        price = price_tag.get_text(strip=True)
    else:
        for span in soup.find_all("span"):
            txt = span.get_text(strip=True).replace(",", "")
            if txt.isdigit() and len(txt) >= 5:
                price = span.get_text(strip=True) + " تومان"
                break

    stock = "✅ موجود در انبار"
    if "ناموجود" in soup.text:
        stock = "❌ ناموجود"

    return title, image, price, stock

# ================== مدیریت پیام‌ها ==================

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "📞 پشتیبانی")
    markup.add("📢 کانال فروشگاه")
    
    bot.send_message(
        message.chat.id,
        "👋 به ربات بانه استور خوش آمدید\nبرای مشاهده محصولات یا ارتباط با ما از منوی زیر استفاده کنید:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer"),
        types.InlineKeyboardButton("🧹 جاروبرقی", url="https://banehstoore.ir/product-category/vacuum-cleaner"),
        types.InlineKeyboardButton("🛍 مشاهده همه", url="https://banehstoore.ir")
    )
    bot.send_message(message.chat.id, "🛒 دسته‌بندی محصولات:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📲 پیام در واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"))
    bot.send_message(message.chat.id, "📞 برای مشاوره و خرید با ما در ارتباط باشید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def channel_info(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"))
    bot.send_message(message.chat.id, f"📢 آخرین محصولات و تخفیف‌ها در کانال بانه استور:\n{CHANNEL_ID}", reply_markup=markup)

# ================== بخش اختصاصی ادمین (ارسال محصول) ==================

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and "banehstoore.ir" in (m.text or ""))
def admin_post_product(message):
    bot.send_message(message.chat.id, "⏳ در حال استخراج اطلاعات محصول و ارسال به کانال...")
    
    try:
        url = re.search(r'(https?://[^\s]+)', message.text).group(0)
        title, image, price, stock = fetch_product(url)

        caption = f"🛍 **{title}**\n\n💰 قیمت: {price}\n📦 وضعیت: {stock}\n\n✅ ضمانت اصالت کالا\n🚚 ارسال به سراسر کشور\n🤝 خرید مطمئن از بانه استور\n\n🆔 {CHANNEL_ID}"

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🛒 خرید/مشاهده سایت", url=url),
            types.InlineKeyboardButton("📲 مشاوره و ثبت سفارش", url=f"https://wa.me/98{WHATSAPP[1:]}")
        )

        if image:
            bot.send_photo(CHANNEL_ID, image, caption=caption, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(CHANNEL_ID, caption, parse_mode="Markdown", reply_markup=markup)

        bot.send_message(message.chat.id, "✅ محصول با موفقیت در کانال منتشر شد.")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا در پردازش لینک:\n{e}")

# ================== تنظیمات وب‌هوک و سرور ==================

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Baneh Stoore Bot is Running!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
