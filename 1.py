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

# ================== استخراج مستقیم جزئیات سفارش از میکسین ==================
def fetch_order_details(order_id):
    try:
        # آدرس مستقیم جزئیات سفارش طبق اعلام شما
        order_url = f"https://banehstoore.ir/profile/order-details/{order_id}/"
        r = requests.get(order_url, headers=HEADERS, timeout=15)
        
        if r.status_code != 200:
            return "❌ سفارش یافت نشد یا دسترسی مقدور نیست. لطفاً شماره سفارش را بررسی کنید."

        soup = BeautifulSoup(r.text, "html.parser")
        
        # استخراج اطلاعات (با توجه به ساختار میکسین)
        # تلاش برای پیدا کردن آیتم‌های سفارش
        products = []
        # معمولا در میکسین نام محصول در کلاس‌های مخصوص یا تگ‌های a داخل جدول سفارش است
        items = soup.find_all(class_=re.compile("product|item-name|title", re.I))
        for item in items[:5]: # حداکثر ۵ آیتم اول
            name = item.get_text(strip=True)
            if len(name) > 10: products.append(f"🔹 {name}")

        # استخراج وضعیت و مبلغ کل
        status = "نامشخص"
        status_tag = soup.find(class_=re.compile("status|step-active|order-state", re.I))
        if status_tag: status = status_tag.get_text(strip=True)

        total_price = "نامشخص"
        price_tag = soup.find(class_=re.compile("total|price|amount", re.I))
        if price_tag: total_price = price_tag.get_text(strip=True)

        # ساخت متن فاکتور
        order_text = f"📦 **جزئیات سفارش شماره {order_id}**\n\n"
        if products:
            order_text += "🛒 **محصولات:**\n" + "\n".join(set(products)) + "\n\n"
        
        order_text += f"🚩 **وضعیت فعلی:** {status}\n"
        order_text += f"💰 **مبلغ کل:** {total_price}\n\n"
        order_text += f"🌐 [مشاهده در سایت]({order_url})"
        
        return order_text
    except Exception as e:
        return f"⚠️ سیستم در حال حاضر قادر به خواندن جزئیات نیست.\n🔗 لطفاً از لینک زیر استفاده کنید:\nhttps://banehstoore.ir/profile/order-details/{order_id}/"

# ================== منوی اصلی ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

# ================== هندلرهای دکمه‌ها ==================
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id)
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور\nاز منوی زیر استفاده کنید:", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products_btn(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/category/espresso-maker"),
               types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/category/air-fryer"),
               types.InlineKeyboardButton("🛍 همه محصولات", url="https://banehstoore.ir/products"))
    bot.send_message(message.chat.id, "🛒 دسته‌بندی محصولات:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_start(message):
    msg = bot.send_message(message.chat.id, "🔢 لطفاً شماره سفارش خود را وارد کنید:")
    bot.register_next_step_handler(msg, track_process)

def track_process(message):
    order_id = message.text.strip()
    # جلوگیری از تداخل با دکمه‌ها
    if order_id in ["🛒 محصولات", "🔍 جستجوی محصول", "📦 پیگیری سفارش", "📞 پشتیبانی و تماس", "📢 کانال فروشگاه"]:
        return

    if order_id.isdigit():
        bot.send_chat_action(message.chat.id, 'typing')
        result = fetch_order_details(order_id)
        bot.send_message(message.chat.id, result, parse_mode="Markdown", disable_web_page_preview=False)
    else:
        bot.send_message(message.chat.id, "❌ لطفا فقط شماره سفارش را به صورت عدد وارد کنید.")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support_btn(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 پیام در واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"))
    bot.send_message(message.chat.id, "📞 برای پشتیبانی با ما در ارتباط باشید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def channel_btn(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 ورود به کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"))
    bot.send_message(message.chat.id, f"📢 کانال تلگرام ما: {CHANNEL_ID}", reply_markup=markup)

# ================== مدیریت و جستجو ==================
@bot.message_handler(func=lambda m: m.text == "🛠 پنل مدیریت" and m.from_user.id == ADMIN_ID)
def admin_p(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📣 ارسال همگانی", "📊 آمار", "🔙 بازگشت")
    bot.send_message(ADMIN_ID, "🛠 پنل مدیریت:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def search_handler(message):
    query = message.text
    if len(query) < 2: return
    r = requests.get(f"https://banehstoore.ir/search?q={query.replace(' ', '+')}", headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    products = []
    for link in soup.find_all('a', href=re.compile(r'/product/')):
        title = link.get_text(strip=True)
        url = link.get('href')
        if url.startswith('/'): url = f"https://banehstoore.ir{url}"
        if title and not any(p['url'] == url for p in products): products.append({"title": title, "url": url})
    
    if products:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for p in products[:10]: markup.add(types.InlineKeyboardButton(p['title'], url=p['url']))
        bot.send_message(message.chat.id, f"✅ نتایج یافت شده برای '{query}':", reply_markup=markup)

# ================== وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Order Details Integrated!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
