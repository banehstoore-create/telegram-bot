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

# ================== جستجوی کامل در میکسین ==================
def search_in_site(query):
    try:
        # جستجو در آدرس مخصوص میکسین
        search_url = f"https://banehstoore.ir/search?q={query.replace(' ', '+')}"
        r = requests.get(search_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        products = []
        # پیدا کردن تمامی لینک‌هایی که شامل ساختار محصول هستند
        links = soup.find_all('a', href=re.compile(r'/product/'))
        
        for link in links:
            title = link.get_text(strip=True)
            url = link.get('href')
            
            if url.startswith('/'):
                url = f"https://banehstoore.ir{url}"
            
            # پاکسازی و فیلتر (میکسین گاهی عکس و متن را جدا لینک می‌کند، تکراری‌ها را حذف می‌کنیم)
            if title and len(title) > 3:
                if not any(p['url'] == url for p in products):
                    products.append({"title": title, "url": url})
            
        return products
    except Exception as e:
        print(f"Error: {e}")
        return []

# ================== منوها ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "🔍 جستجوی محصول")
    markup.add("📞 پشتیبانی و تماس", "📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.add("🛠 پنل مدیریت")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id)
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور\nنام محصول مورد نظرتان را بنویسید تا تمام موارد موجود را نمایش دهم:", 
                     reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔍 جستجوی محصول")
def search_hint(message):
    bot.send_message(message.chat.id, "🔎 اسم محصول را تایپ کنید (مثلاً: ال جی، بوش، سرخ کن...)")

# ================== مدیریت هوشمند پیام‌ها و نمایش نتایج ==================
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    # لاجیک دکمه‌های ادمین
    if message.from_user.id == ADMIN_ID:
        if message.text == "🛠 پنل مدیریت":
            u_count = len(get_all_users())
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("📣 ارسال همگانی", "📊 آمار")
            markup.add("🔙 بازگشت")
            bot.send_message(ADMIN_ID, f"🛠 پنل مدیریت | کاربران: {u_count}", reply_markup=markup)
            return
        elif message.text == "📊 آمار":
            bot.send_message(ADMIN_ID, f"👥 تعداد کل اعضا: {len(get_all_users())}")
            return
        elif message.text == "📣 ارسال همگانی":
            msg = bot.send_message(ADMIN_ID, "پیام خود را بفرستید:")
            bot.register_next_step_handler(msg, do_broadcast)
            return
        elif message.text == "🔙 بازگشت":
            bot.send_message(ADMIN_ID, "منوی اصلی:", reply_markup=get_main_keyboard(ADMIN_ID))
            return

    # سیستم جستجو برای همه کاربران
    query = message.text
    if len(query) < 2: return 

    bot.send_chat_action(message.chat.id, 'typing')
    results = search_in_site(query)
    
    if results:
        # چیدمان دو ستونه برای دکمه‌ها (row_width=2)
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_list = []
        for res in results:
            btn_list.append(types.InlineKeyboardButton(res['title'], url=res['url']))
        
        markup.add(*btn_list) # اضافه کردن تمام دکمه‌ها به صورت یکجا
        
        bot.send_message(message.chat.id, f"✅ تعداد {len(results)} مورد برای '{query}' پیدا شد:", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌐 جستجوی مستقیم در سایت", url=f"https://banehstoore.ir/search?q={query}"))
        bot.send_message(message.chat.id, f"❌ محصولی با نام '{query}' در لیست سریع پیدا نشد. می‌توانید در سایت جستجو کنید:", reply_markup=markup)

def do_broadcast(message):
    users = get_all_users()
    for u in users:
        try: bot.copy_message(u, message.chat.id, message.message_id)
        except: pass
    bot.send_message(ADMIN_ID, "✅ ارسال همگانی با موفقیت انجام شد.")

# ================== اجرای سرور ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Baneh Stoore Search is Active!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
