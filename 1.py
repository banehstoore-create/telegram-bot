import telebot
from telebot import types
import os
import re
import html
import sqlite3
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ================== مدیریت دیتابیس ==================
def get_db_connection():
    # استفاده از مسیر ثابت برای پایداری دیتابیس در Render
    conn = sqlite3.connect('baneh_orders.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id TEXT PRIMARY KEY, 
                  details TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ================== استخراج‌گر هوشمند متن ==================
def extract_info_from_text(raw_text):
    """این تابع متن کپی شده از صفحه سفارش را تحلیل و تمیز می‌کند"""
    try:
        # پیدا کردن شماره سفارش از لابلای متن
        order_id_match = re.search(r'(?:سفارش|شماره)\s*#?(\d+)', raw_text)
        if not order_id_match:
            return None, "❌ شماره سفارش در متن یافت نشد."
        
        order_id = order_id_match.group(1)

        # استخراج فیلدها با عبارات منظم (Regex)
        def find_match(pattern):
            match = re.search(pattern, raw_text)
            return match.group(1).strip() if match else "ثبت نشده"

        receiver = find_match(r"تحویل گیرنده\s*[:：]\s*([^👤📍🛒💰🚩\n]+)")
        address = find_match(r"ارسال به\s*[:：]\s*([^👤📍🛒💰🚩\n]+)")
        total = find_match(r"مبلغ کل\s*[:：]\s*([\d,]+)")
        status = find_match(r"وضعیت\s*[:：]\s*([^👤📍🛒💰🚩\n]+)")

        formatted_details = (
            f"👤 **تحویل گیرنده:** {receiver}\n"
            f"📍 **آدرس:** {address}\n"
            f"💰 **مبلغ کل:** {total} تومان\n"
            f"🚩 **وضعیت:** {status}"
        )

        # ذخیره در دیتابیس
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO orders (order_id, details) VALUES (?, ?)", (order_id, formatted_details))
        conn.commit()
        conn.close()
        
        return order_id, formatted_details
    except Exception as e:
        return None, f"خطا در پردازش: {str(e)}"

# ================== هندلرها (حفظ موارد قبلی) ==================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    if user_id == ADMIN_ID:
        markup.row("📥 ثبت فاکتور (کپی متن)")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 خوش آمدید ادمین عزیز. تمام موارد قبلی حفظ شده است.", reply_markup=main_menu(message.from_user.id))

# --- بخش ادمین: ثبت سفارش بدون نیاز به لینک مستقیم ---
@bot.message_handler(func=lambda m: m.text == "📥 ثبت فاکتور (کپی متن)" and m.from_user.id == ADMIN_ID)
def ask_for_text(message):
    msg = bot.send_message(message.chat.id, "📑 کافیست کل متن صفحه سفارش مشتری را کپی کرده و اینجا بفرستید.\n(ربات خودش شماره سفارش و جزئیات را استخراج و در دیتابیس ذخیره می‌کند)")
    bot.register_next_step_handler(msg, process_raw_text)

def process_raw_text(message):
    bot.send_message(message.chat.id, "⏳ در حال پردازش و ذخیره در دیتابیس...")
    oid, res = extract_info_from_text(message.text)
    if oid:
        bot.send_message(message.chat.id, f"✅ فاکتور شماره {oid} با موفقیت در دیتابیس ثبت شد.\n\n{res}", parse_mode="Markdown", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, res, reply_markup=main_menu(message.from_user.id))

# --- بخش مشتری: پیگیری از دیتابیس ---
@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track(message):
    msg = bot.send_message(message.chat.id, "🔢 شماره سفارش را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, show_from_db)

def show_from_db(message):
    oid = message.text.strip()
    conn = get_db_connection()
    row = conn.execute("SELECT details FROM orders WHERE order_id = ?", (oid,)).fetchone()
    conn.close()

    if row:
        bot.send_message(message.chat.id, f"📑 **جزئیات فاکتور {oid}:**\n\n{row['details']}\n\n✅ بانه استور", parse_mode="Markdown", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ شماره سفارش یافت نشد. ادمین باید ابتدا آن را ثبت کند.", reply_markup=main_menu(message.from_user.id))

# سایر بخش‌ها (محصولات و...)
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def p(m): bot.send_message(m.chat.id, "🛒 لیست محصولات: https://banehstoore.ir/products")

# ================== وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Manual Database Mode Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
