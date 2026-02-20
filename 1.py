import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import os
import re
import html
import sqlite3 # یا کتابخانه دیتابیس مورد نظر شما
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_COOKIE = os.environ.get("MY_COOKIE", "") 
ADMIN_ID = 6690559792 
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# هدر برای استخراج اطلاعات (فقط هنگام ثبت توسط ادمین استفاده می‌شود)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Cookie": MY_COOKIE
}

# ================== مدیریت دیتابیس ==================
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id TEXT PRIMARY KEY, content TEXT)''')
    conn.commit()
    conn.close()

def save_order_to_db(order_id, content):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO orders (order_id, content) VALUES (?, ?)", (order_id, content))
    conn.commit()
    conn.close()

def get_order_from_db(order_id):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT content FROM orders WHERE order_id=?", (order_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

init_db()

# ================== تابع استخراج اطلاعات از لینک ==================
def scrape_and_store(url):
    try:
        # استخراج شماره سفارش از انتهای لینک
        order_id = url.strip().split('/')[-2]
        if not order_id.isdigit():
            order_id = url.strip().split('/')[-1]

        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            return None, "❌ خطا در اتصال به سایت (کد وضعیت: {})".format(response.status_code)

        soup = BeautifulSoup(response.text, "html.parser")
        
        # استخراج داده‌ها بر اساس ساختار سایت شما
        def get_text(label):
            target = soup.find(string=re.compile(label))
            return target.parent.get_text().replace(label, "").replace(":", "").strip() if target else "یافت نشد"

        receiver = get_text("تحویل گیرنده")
        address = get_text("ارسال به")
        price = get_text("مبلغ کل")
        status = get_text("وضعیت")

        invoice_content = f"👤 **تحویل گیرنده:** {receiver}\n📍 **آدرس:** {address}\n💰 **مبلغ:** {price}\n🚩 **وضعیت:** {status}"
        
        save_order_to_db(order_id, invoice_content)
        return order_id, invoice_content
    except Exception as e:
        return None, str(e)

# ================== کیبورد و هندلرها ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("📥 ثبت لینک سفارش (ادمین)")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 به ربات بانه استور خوش آمدید", reply_markup=get_main_keyboard(message.from_user.id))

# --- بخش ادمین (ثبت با لینک) ---
@bot.message_handler(func=lambda m: m.text == "📥 ثبت لینک سفارش (ادمین)" and m.from_user.id == ADMIN_ID)
def admin_link_req(message):
    msg = bot.send_message(message.chat.id, "🔗 لطفاً لینک کامل صفحه سفارش را بفرستید:")
    bot.register_next_step_handler(msg, process_admin_link)

def process_admin_link(message):
    url = message.text.strip()
    if "banehstoore.ir" in url:
        bot.send_message(message.chat.id, "⏳ در حال استخراج و ذخیره در دیتابیس...")
        oid, res = scrape_and_store(url)
        if oid:
            bot.send_message(message.chat.id, f"✅ سفارش شماره {oid} با موفقیت در دیتابیس ذخیره شد.")
        else:
            bot.send_message(message.chat.id, f"❌ خطا: {res}")
    else:
        bot.send_message(message.chat.id, "❌ لینک معتبر نیست.")

# --- بخش مشتری (مشاهده از دیتابیس) ---
@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_start(message):
    msg = bot.send_message(message.chat.id, "🔢 شماره سفارش خود را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, show_order_details)

def show_order_details(message):
    oid = message.text.strip()
    content = get_order_from_db(oid)
    if content:
        bot.send_message(message.chat.id, f"📑 **فاکتور شماره {oid}**\n\n{content}\n\n✅ بانه استور", reply_markup=get_main_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ این سفارش هنوز ثبت نشده است. لطفاً با پشتیبانی تماس بگیرید.", reply_markup=get_main_keyboard(message.from_user.id))

# سایر دکمه‌ها (بدون تغییر)
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def p(m): bot.send_message(m.chat.id, "🛒 https://banehstoore.ir/products")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def s(m): bot.send_message(m.chat.id, f"📞 {PHONE_NUMBER}\n💬 {WHATSAPP}")

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def c(m): bot.send_message(m.chat.id, f"📢 {CHANNEL_ID}")

# وب‌هوک
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Database Sync Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
