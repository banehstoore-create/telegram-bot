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
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

# ================== دیتابیس ==================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

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

# ================== پیگیری سفارش اختصاصی میکسین ==================
def track_mixin_order(order_id):
    try:
        # آدرس پیگیری سفارش در سایت‌های میکسینی معمولا به این صورت است
        track_url = f"https://banehstoore.ir/order/track/{order_id}"
        r = requests.get(track_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return "❌ سفارش یافت نشد. لطفا شماره سفارش را بررسی کنید."
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # استخراج وضعیت سفارش (بر اساس تگ‌های رایج در میکسین)
        # میکسین معمولاً وضعیت را در تگ‌هایی با کلاس order-status یا مشابه آن قرار می‌دهد
        status_tag = soup.find(class_=re.compile("status|order-info|step-active", re.I))
        
        if status_tag:
            status_text = status_tag.get_text(strip=True)
            return f"📦 **وضعیت سفارش شماره {order_id}:**\n\n🔹 {status_text}\n\n🌐 مشاهده جزئیات بیشتر:\n{track_url}"
        else:
            return f"✅ سفارش {order_id} در سیستم ثبت شده است.\n🌐 برای مشاهده وضعیت دقیق کلیک کنید:\n{track_url}"
    except:
        return "❌ اختلال در اتصال به سایت. لطفاً بعداً تلاش کنید یا با پشتیبانی تماس بگیرید."

# ================== جستجوی محصول ==================
def search_in_site(query):
    try:
        search_url = f"https://banehstoore.ir/search?q={query.replace(' ', '+')}"
        r = requests.get(search_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        products = []
        links = soup.find_all('a', href=re.compile(r'/product/'))
        for link in links:
            title = link.get_text(strip=True)
            url = link.get('href')
            if url.startswith('/'): url = f"https://banehstoore.ir{url}"
            if title and len(title) > 3:
                if not any(p['url'] == url for p in products):
                    products.append({"title": title, "url": url})
        return products
    except: return []

# ================== منوها ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "🔍 جستجوی محصول")
    markup.add("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.add("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.add("🛠 پنل مدیریت")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id)
    bot.send_message(message.chat.id, "👋 به بانه استور خوش آمدید\nگزینه مورد نظر را انتخاب کنید:", 
                     reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_prompt(message):
    msg = bot.send_message(message.chat.id, "🔢 لطفاً شماره سفارش خود را وارد کنید:\n(مثال: 12345)")
    bot.register_next_step_handler(msg, process_tracking)

def process_tracking(message):
    order_id = message.text.strip()
    if not order_id.isdigit():
        bot.send_message(message.chat.id, "❌ شماره سفارش باید فقط عدد باشد. دوباره تلاش کنید.")
        return
    
    bot.send_chat_action(message.chat.id, 'find_location')
    status_report = track_mixin_order(order_id)
    bot.send_message(message.chat.id, status_report, parse_mode="Markdown")

# ================== مدیریت پیام‌ها ==================
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    if message.from_user.id == ADMIN_ID:
        if message.text == "🛠 پنل مدیریت":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("📣 ارسال همگانی", "📊 آمار", "🔙 بازگشت")
            bot.send_message(ADMIN_ID, "🛠 پنل مدیریت:", reply_markup=markup); return
        elif message.text == "📊 آمار":
            bot.send_message(ADMIN_ID, f"👥 کل کاربران: {len(get_all_users())}"); return
        elif message.text == "📣 ارسال همگانی":
            msg = bot.send_message(ADMIN_ID, "پیام را بفرستید:"); bot.register_next_step_handler(msg, do_broadcast); return
        elif message.text == "🔙 بازگشت":
            bot.send_message(ADMIN_ID, "منوی اصلی:", reply_markup=get_main_keyboard(ADMIN_ID)); return

    # اگر کاربر دکمه جستجو نزده بود اما متن فرستاد، جستجو کن
    if message.text == "🔍 جستجوی محصول":
        bot.send_message(message.chat.id, "🔎 نام محصول را بفرستید:")
        return
    
    query = message.text
    bot.send_chat_action(message.chat.id, 'typing')
    results = search_in_site(query)
    
    if results:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for res in results: markup.add(types.InlineKeyboardButton(res['title'], url=res['url']))
        bot.send_message(message.chat.id, f"✅ نتایج یافت شده:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ موردی پیدا نشد.")

def do_broadcast(message):
    users = get_all_users()
    for u in users:
        try: bot.copy_message(u, message.chat.id, message.message_id)
        except: pass
    bot.send_message(ADMIN_ID, "✅ انجام شد.")

# ================== وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Tracking System Active!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
