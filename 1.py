import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import os
import re
import html
import sqlite3
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

# هدرها برای شبیه‌سازی مرورگر جهت دور زدن محدودیت سایت
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Cookie": MY_COOKIE,
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8",
    "Referer": "https://banehstoore.ir/profile/orders/"
}

# ================== مدیریت دیتابیس SQLITE ==================
def get_db_connection():
    conn = sqlite3.connect('baneh_orders.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id TEXT PRIMARY KEY, 
                  details TEXT, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# ================== تابع هوشمند استخراج و ذخیره ==================
def scrape_and_save_to_db(url):
    try:
        # استخراج شماره سفارش از لینک (مثلاً 49111)
        order_id_match = re.search(r'order-details/(\d+)', url)
        if not order_id_match:
            return False, "❌ لینک ارسالی حاوی شماره سفارش معتبر نیست."
        
        order_id = order_id_match.group(1)
        
        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            return False, f"❌ خطا در دسترسی به سایت (Status: {response.status_code})"
        
        if "login" in response.url or "ورود" in response.text:
            return False, "❌ کوکی منقضی شده! لطفاً کوکی جدید را در Render ست کنید."

        soup = BeautifulSoup(response.text, "html.parser")
        
        # استخراج فیلدها با دقت بالا بر اساس ساختار سایت
        def find_field(text_query):
            element = soup.find(string=re.compile(text_query))
            if element:
                # تلاش برای یافتن مقدار در تگ‌های مجاور
                return element.parent.get_text().replace(text_query, "").replace(":", "").strip()
            return "یافت نشد"

        data = {
            "receiver": find_field("تحویل گیرنده"),
            "address": find_field("ارسال به"),
            "total": find_field("مبلغ کل"),
            "status": find_field("وضعیت"),
            "phone": find_field("شماره تماس")
        }

        # فرمت نهایی برای ذخیره در دیتابیس
        final_text = (
            f"👤 **تحویل گیرنده:** {data['receiver']}\n"
            f"📞 **شماره تماس:** {data['phone']}\n"
            f"📍 **آدرس:** {data['address']}\n"
            f"💰 **مبلغ کل:** {data['total']}\n"
            f"🚩 **وضعیت سفارش:** {data['status']}"
        )

        # ذخیره در دیتابیس
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO orders (order_id, details) VALUES (?, ?)", 
                     (order_id, final_text))
        conn.commit()
        conn.close()
        
        return order_id, final_text

    except Exception as e:
        return False, f"⚠️ خطای سیستمی: {str(e)}"

# ================== هندلرها (حفظ تمام موارد قبلی) ==================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    if user_id == ADMIN_ID:
        markup.row("📥 ثبت فاکتور جدید (ارسال لینک)")
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "👋 به ربات بانه استور خوش آمدید.", reply_markup=main_menu(message.from_user.id))

# --- بخش ادمین: ثبت لینک ---
@bot.message_handler(func=lambda m: m.text == "📥 ثبت فاکتور جدید (ارسال لینک)" and m.from_user.id == ADMIN_ID)
def ask_for_link(message):
    msg = bot.send_message(message.chat.id, "🔗 لطفاً لینک صفحه سفارش مشتری را بفرستید:")
    bot.register_next_step_handler(msg, process_link_and_save)

def process_link_and_save(message):
    url = message.text.strip()
    if "banehstoore.ir" not in url:
        bot.send_message(message.chat.id, "❌ لینک نامعتبر است. باید لینک سایت بانه استور باشد.")
        return

    bot.send_message(message.chat.id, "⏳ در حال استخراج اطلاعات و ذخیره در دیتابیس...")
    order_id, result = scrape_and_save_to_db(url)
    
    if order_id:
        bot.send_message(message.chat.id, f"✅ فاکتور شماره **{order_id}** با موفقیت ذخیره شد.\n\n{result}", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, result)

# --- بخش مشتری: پیگیری ---
@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_order(message):
    msg = bot.send_message(message.chat.id, "🔢 لطفاً شماره سفارش خود را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, fetch_from_db)

def fetch_from_db(message):
    order_id = message.text.strip()
    conn = get_db_connection()
    row = conn.execute("SELECT details FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()

    if row:
        bot.send_message(message.chat.id, f"📑 **جزئیات فاکتور {order_id}:**\n\n{row['details']}\n\n✅ بانه استور", 
                         parse_mode="Markdown", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ متأسفانه فاکتوری با این شماره در سیستم یافت نشد.", 
                         reply_markup=main_menu(message.from_user.id))

# (سایر هندلرهای محصولات و پشتیبانی همانند قبل...)
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def p_list(m): bot.send_message(m.chat.id, "🛒 لیست محصولات: https://banehstoore.ir/products")

# ================== اجرای وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot Status: Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
