import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import re
import os
import psycopg2
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"
MAP_URL = "https://maps.app.goo.gl/eWv6njTbL8ivfbYa6"
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================== مدیریت دیتابیس Neon ==================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error initializing database: {e}")

def save_user(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING', (user_id,))
        conn.commit()
        cur.close()
        conn.close()
    except: pass

def get_all_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT user_id FROM users')
        users = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return users
    except: return []

init_db()

# ================== تابع منوی هوشمند ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "🔍 جستجوی محصول")
    markup.add("📞 پشتیبانی و تماس", "📢 کانال فروشگاه")
    if user_id == ADMIN_ID:
        markup.add("🛠 پنل مدیریت")
    return markup

# ================== توابع جستجو و محصول ==================
def search_in_site(query):
    """جستجو در محصولات سایت"""
    try:
        search_url = f"https://banehstoore.ir/?s={query}"
        r = requests.get(search_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # پیدا کردن محصولات (براساس کلاس‌های متداول ووکامرس)
        products = []
        # این بخش نام محصولات را از تگ‌های h2 یا h3 که لینک دارند استخراج می‌کند
        items = soup.find_all(["h2", "h3"], class_=re.compile("product-title|loop-product__title|title"))
        
        for item in items[:8]: # نمایش حداکثر 8 نتیجه اول
            a_tag = item.find("a") or item.parent.find("a")
            if a_tag and a_tag.get("href"):
                products.append({
                    "title": item.get_text(strip=True),
                    "url": a_tag.get("href")
                })
        return products
    except:
        return []

def fetch_product(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "محصول بانه استور"
        image = soup.find("meta", property="og:image")["content"] if soup.find("meta", property="og:image") else None
        price_tag = soup.find("p", class_="price")
        price = price_tag.get_text(strip=True) if price_tag else "تماس بگیرید"
        stock = "✅ موجود" if "موجود" in soup.text and "ناموجود" not in soup.text else "❌ ناموجود"
        return title, image, price, stock
    except: return None

# ================== مدیریت پیام‌ها ==================

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "👋 به ربات بانه استور خوش آمدید\nمحصول مورد نظرت را جستجو کن یا از منو استفاده کن:",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

@bot.message_handler(func=lambda m: m.text == "🔍 جستجوی محصول")
def search_prompt(message):
    bot.send_message(message.chat.id, "🔎 لطفاً نام محصول مورد نظر خود را تایپ کنید (مثلاً: سرخ کن)")

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker/"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer/"),
        types.InlineKeyboardButton("🧹 جاروبرقی", url="https://banehstoore.ir/product-category/vacuum-cleaner/"),
        types.InlineKeyboardButton("🛍 مشاهده همه محصولات", url="https://banehstoore.ir/shop/")
    )
    bot.send_message(message.chat.id, "🛒 **دسته‌بندی‌های اصلی:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📞 تماس مستقیم", callback_data="call_us"),
        types.InlineKeyboardButton("💬 پیام در واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"),
        types.InlineKeyboardButton("📍 آدرس فروشگاه", url=MAP_URL)
    )
    bot.send_message(message.chat.id, "📞 راه‌های ارتباطی:", reply_markup=markup)

# ================== منطق جستجوی متن آزاد ==================
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    # چک کردن اگر ادمین لینک فرستاده برای کانال
    if message.from_user.id == ADMIN_ID and "banehstoore.ir" in message.text:
        admin_post_product(message)
        return

    # چک کردن دکمه‌های ادمین
    if message.from_user.id == ADMIN_ID:
        if message.text == "🛠 پنل مدیریت": admin_panel(message); return
        if message.text == "📊 آمار کاربران": stats(message); return
        if message.text == "📣 ارسال پیام همگانی": broadcast_prompt(message); return
        if message.text == "🔙 بازگشت به منوی اصلی": back_home(message); return

    # در غیر این صورت، جستجو در سایت
    query = message.text
    bot.send_chat_action(message.chat.id, 'typing')
    results = search_in_site(query)
    
    if results:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for res in results:
            markup.add(types.InlineKeyboardButton(res['title'], url=res['url']))
        
        bot.send_message(message.chat.id, f"🔎 نتایج جستجو برای '{query}':", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ متأسفانه محصولی پیدا نشد. لطفاً نام محصول را دقیق‌تر بنویسید.")

# ================== بخش مدیریت و ارسال به کانال (همان کدهای قبلی) ==================

def admin_panel(message):
    users = get_all_users()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📣 ارسال پیام همگانی", "📊 آمار کاربران")
    markup.add("🔙 بازگشت به منوی اصلی")
    bot.send_message(message.chat.id, f"🛠 **پنل مدیریت**\nکاربران: `{len(users)}`", reply_markup=markup, parse_mode="Markdown")

def stats(message):
    users = get_all_users()
    bot.send_message(message.chat.id, f"👥 کل کاربران: `{len(users)}`", parse_mode="Markdown")

def broadcast_prompt(message):
    msg = bot.send_message(message.chat.id, "📣 پیام همگانی را بفرستید:")
    bot.register_next_step_handler(msg, do_broadcast)

def do_broadcast(message):
    users = get_all_users()
    for uid in users:
        try: bot.copy_message(uid, message.chat.id, message.message_id)
        except: pass
    bot.send_message(ADMIN_ID, "✅ ارسال شد.")

def back_home(message):
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=get_main_keyboard(message.from_user.id))

def admin_post_product(message):
    bot.send_message(message.chat.id, "⏳ در حال ارسال به کانال...")
    try:
        url = re.search(r'(https?://[^\s]+)', message.text).group(0)
        data = fetch_product(url)
        if data:
            title, image, price, stock = data
            caption = f"🛍 **{title}**\n\n💰 قیمت: {price}\n📦 وضعیت: {stock}\n\n🆔 {CHANNEL_ID}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🛒 خرید از سایت", url=url),
                       types.InlineKeyboardButton("📲 سفارش", url=f"https://wa.me/98{WHATSAPP[1:]}"))
            if image: bot.send_photo(CHANNEL_ID, image, caption=caption, parse_mode="Markdown", reply_markup=markup)
            else: bot.send_message(CHANNEL_ID, caption, parse_mode="Markdown", reply_markup=markup)
            bot.send_message(message.chat.id, "✅ ارسال شد.")
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطا: {e}")

# ================== وب‌هوک و سرور ==================

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Baneh Stoore Bot Search is Ready!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
