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
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}

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

# ================== توابع کمکی ==================
def search_in_site(query):
    try:
        search_url = f"https://banehstoore.ir/search?q={query.replace(' ', '+')}"
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        products = []
        links = soup.find_all('a', href=re.compile(r'/product/'))
        for link in links:
            title = link.get_text(strip=True)
            url = link.get('href')
            if url.startswith('/'): url = f"https://banehstoore.ir{url}"
            if title and len(title) > 3 and not any(p['url'] == url for p in products):
                products.append({"title": title, "url": url})
        return products
    except: return []

# ================== منوی اصلی ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID:
        markup.row("🛠 پنل مدیریت")
    return markup

# ================== هندلرهای اصلی ==================

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id)
    bot.send_message(message.chat.id, "👋 به بانه استور خوش آمدید\nگزینه مورد نظر را انتخاب کنید:", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products_btn(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/category/air-fryer"),
        types.InlineKeyboardButton("🛍 همه محصولات", url="https://banehstoore.ir/products")
    )
    bot.send_message(message.chat.id, "🛒 دسته‌بندی محصولات:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support_btn(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📞 تماس مستقیم", callback_data="call_admin"),
        types.InlineKeyboardButton("💬 واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"),
        types.InlineKeyboardButton("📍 آدرس روی نقشه", url=MAP_URL)
    )
    bot.send_message(message.chat.id, "📞 پشتیبانی بانه استور:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def channel_btn(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"))
    bot.send_message(message.chat.id, f"📢 کانال تلگرام ما:\n{CHANNEL_ID}", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔍 جستجوی محصول")
def search_btn_hint(message):
    bot.send_message(message.chat.id, "🔎 نام محصول مورد نظر را تایپ کنید:")

# ================== بخش پیگیری سفارش (اصلاح شده برای میکسین) ==================

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_order_start(message):
    msg = bot.send_message(message.chat.id, "🔢 لطفاً شماره سفارش خود را وارد کنید:")
    bot.register_next_step_handler(msg, track_order_result)

def track_order_result(message):
    order_id = message.text.strip()
    
    # خروج از حالت پیگیری در صورت کلیک روی دکمه‌های اصلی
    if order_id in ["🛒 محصولات", "🔍 جستجوی محصول", "📦 پیگیری سفارش", "📞 پشتیبانی و تماس", "📢 کانال فروشگاه"]:
        if order_id == "🛒 محصولات": products_btn(message)
        elif order_id == "🔍 جستجوی محصول": search_btn_hint(message)
        elif order_id == "📦 پیگیری سفارش": track_order_start(message)
        elif order_id == "📞 پشتیبانی و تماس": support_btn(message)
        elif order_id == "📢 کانال فروشگاه": channel_btn(message)
        return

    if order_id.isdigit():
        # اصلاح آدرس طبق ساختار استاندارد میکسین (استفاده از کوئری پارامتر)
        track_url = f"https://banehstoore.ir/order/track?id={order_id}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌐 مشاهده وضعیت در سایت", url=track_url))
        
        bot.send_message(
            message.chat.id, 
            f"📦 **درخواست پیگیری برای سفارش {order_id}**\n\nبرای مشاهده وضعیت سفارش و کد رهگیری پستی، روی دکمه زیر کلیک کنید:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "❌ شماره سفارش باید فقط عدد باشد.")

# ================== پنل مدیریت ==================

@bot.message_handler(func=lambda m: m.text == "🛠 پنل مدیریت" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📣 ارسال همگانی", "📊 آمار")
    markup.row("🔙 بازگشت")
    bot.send_message(ADMIN_ID, "🛠 پنل مدیریت:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 آمار" and m.from_user.id == ADMIN_ID)
def admin_stats(message):
    bot.send_message(ADMIN_ID, f"👥 کل کاربران: {len(get_all_users())}")

@bot.message_handler(func=lambda m: m.text == "📣 ارسال همگانی" and m.from_user.id == ADMIN_ID)
def admin_broadcast(message):
    msg = bot.send_message(ADMIN_ID, "پیام را بفرستید:")
    bot.register_next_step_handler(msg, broadcast_now)

def broadcast_now(message):
    if message.text == "🔙 بازگشت": admin_panel(message); return
    users = get_all_users()
    for u in users:
        try: bot.copy_message(u, message.chat.id, message.message_id)
        except: pass
    bot.send_message(ADMIN_ID, "✅ پیام ارسال شد.")

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت")
def back_btn(message):
    start(message)

# ================== موتور جستجو ==================

@bot.message_handler(func=lambda m: True)
def auto_search(message):
    query = message.text
    if len(query) < 2: return
    
    bot.send_chat_action(message.chat.id, 'typing')
    results = search_in_site(query)
    
    if results:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for res in results:
            markup.add(types.InlineKeyboardButton(res['title'], url=res['url']))
        bot.send_message(message.chat.id, f"✅ نتایج برای '{query}':", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ موردی یافت نشد.")

@bot.callback_query_handler(func=lambda call: call.data == "call_admin")
def call_back(call):
    bot.send_message(call.message.chat.id, f"📱 شماره تماس:\n`{PHONE_NUMBER}`", parse_mode="Markdown")

# ================== سرور ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Baneh Stoore Search Fixed!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
