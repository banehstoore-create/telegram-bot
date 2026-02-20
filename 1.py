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
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

# ================== مدیریت دیتابیس ==================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)')
        conn.commit(); cur.close(); conn.close()
    except: pass

def save_user(user_id):
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING', (user_id,))
        conn.commit(); cur.close(); conn.close()
    except: pass

def get_all_users():
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('SELECT user_id FROM users')
        users = [row[0] for row in cur.fetchall()]
        cur.close(); conn.close()
        return users
    except: return []

init_db()

# ================== توابع هوشمند جستجو ==================
def search_in_site(query):
    """جستجوی دقیق در سایت بانه استور"""
    try:
        # آدرس جستجوی مستقیم سایت
        search_url = f"https://banehstoore.ir/?s={query.replace(' ', '+')}"
        r = requests.get(search_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        products = []
        # جستجو در تگ‌های عنوان محصول که معمولاً در وردپرس لینک‌دار هستند
        items = soup.find_all(['h2', 'h3'], class_=re.compile("title|product", re.I))
        
        for item in items:
            link = item.find('a')
            if link and link.get('href') and 'product' in link.get('href'):
                title = item.get_text(strip=True)
                url = link.get('href')
                if not any(p['url'] == url for p in products): # جلوگیری از تکرار
                    products.append({"title": title, "url": url})
            if len(products) >= 10: break # محدودیت برای شلوغ نشدن منو
            
        return products
    except Exception as e:
        print(f"Search Error: {e}")
        return []

# ================== مدیریت منوها ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "🔍 جستجوی محصول")
    markup.add("📞 پشتیبانی و تماس", "📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.add("🛠 پنل مدیریت")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id)
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور\nنام محصول مورد نظرتان را بفرستید تا در سایت جستجو کنم:", 
                     reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔍 جستجوی محصول")
def search_btn(message):
    bot.send_message(message.chat.id, "🔎 کافیست نام محصول را تایپ و ارسال کنید\nمثال: سرخ کن")

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products_cat(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker/"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer/"),
        types.InlineKeyboardButton("🛍 همه محصولات", url="https://banehstoore.ir/shop/")
    )
    bot.send_message(message.chat.id, "🛒 دسته‌بندی‌ها:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📞 تماس", callback_data="call_us"),
               types.InlineKeyboardButton("💬 واتساپ", url=f"https://wa.me/98{PHONE_NUMBER[1:]}"))
    bot.send_message(message.chat.id, "📞 تماس با ما:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "call_us")
def call_us(call):
    bot.send_message(call.message.chat.id, f"📱 شماره تماس ادمین:\n`{PHONE_NUMBER}`", parse_mode="Markdown")

# ================== مدیریت پیام‌های متنی (جستجو و پنل) ==================
@bot.message_handler(func=lambda m: True)
def router(message):
    # چک کردن پنل مدیریت
    if message.from_user.id == ADMIN_ID:
        if message.text == "🛠 پنل مدیریت":
            users = get_all_users()
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("📣 ارسال همگانی", "📊 آمار")
            markup.add("🔙 بازگشت")
            bot.send_message(ADMIN_ID, f"🛠 پنل مدیریت\nکاربران: {len(users)}", reply_markup=markup)
            return
        if message.text == "📊 آمار":
            bot.send_message(ADMIN_ID, f"👥 کل کاربران: {len(get_all_users())}")
            return
        if message.text == "📣 ارسال همگانی":
            msg = bot.send_message(ADMIN_ID, "پیام را بفرستید:")
            bot.register_next_step_handler(msg, broadcast)
            return
        if message.text == "🔙 بازگشت":
            bot.send_message(ADMIN_ID, "منوی اصلی:", reply_markup=get_main_keyboard(ADMIN_ID))
            return
        if "banehstoore.ir" in message.text:
            # ارسال محصول به کانال (کد قبلی شما)
            return

    # موتور جستجو برای همه
    query = message.text
    bot.send_chat_action(message.chat.id, 'typing')
    results = search_in_site(query)
    
    if results:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for res in results:
            markup.add(types.InlineKeyboardButton(f"📦 {res['title']}", url=res['url']))
        bot.send_message(message.chat.id, f"✅ نتایج یافت شده برای '{query}':", reply_markup=markup)
    else:
        # اگر در سایت چیزی پیدا نشد، لینک مستقیم صفحه جستجو را می‌دهیم
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 مشاهده نتایج در سایت", url=f"https://banehstoore.ir/?s={query}"))
        bot.send_message(message.chat.id, f"❌ محصول دقیقاً با این نام در نتایج سریع پیدا نشد.\nمی‌توانید لیست کامل را در سایت ببینید:", reply_markup=markup)

def broadcast(message):
    users = get_all_users()
    for u in users:
        try: bot.copy_message(u, message.chat.id, message.message_id)
        except: pass
    bot.send_message(ADMIN_ID, "✅ ارسال شد.")

# ================== وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Search Fixed!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
