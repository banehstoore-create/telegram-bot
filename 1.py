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

# ================== استخراج‌گر فوق هوشمند ==================
def smart_extract(raw_text):
    try:
        # ۱. استخراج شماره سفارش (مثلاً 49111)
        order_id_match = re.search(r'سفارش\s*[:：]?\s*(\d+)', raw_text)
        if not order_id_match:
            return None, "❌ شماره سفارش در متن پیدا نشد."
        
        order_id = order_id_match.group(1)

        # ۲. تابع کمکی برای یافتن مقادیر با الگوهای منعطف
        def fetch(pattern):
            match = re.search(pattern, raw_text, re.DOTALL)
            return match.group(1).strip() if match else "ثبت نشده"

        # استخراج فیلدها
        receiver = fetch(r"تحویل گیرنده\s*[:：]\s*([^👤📍📞💰🚩\n]+)")
        phone = fetch(r"شماره تماس\s*[:：]\s*([\d\s]+)")
        address = fetch(r"ارسال به\s*[:：]\s*([^👤📍📞💰🚩\n]+)")
        total_price = fetch(r"مبلغ کل\s*[:：]\s*([\d٬,]+)\s*تومان")
        
        # استخراج وضعیت (پاکسازی کلمه "پرداخت شده" از انتهای آن)
        status_raw = fetch(r"وضعیت\s*[:：]\s*([^👤📍📞💰🚩\n]+)")
        status = status_raw.replace("پرداخت شده", "").strip()

        # استخراج نام محصول (معمولاً بعد از کلمه وضعیت یا در انتهای متن)
        product = "نامشخص"
        # جستجو برای محصولاتی مثل سرخ کن، اسپرسو و...
        product_match = re.search(r'([^\n]*(?:سرخ کن|اسپرسو|یونی|مدل|تعداد)[^\n]*)', raw_text)
        if product_match:
            product = product_match.group(1).split("تعداد")[0].strip()

        # ۳. ساخت فاکتور نهایی و شکیل
        formatted_details = (
            f"👤 **خریدار:** {receiver}\n"
            f"📞 **تماس:** <code>{phone}</code>\n"
            f"📍 **نشانی:** {address}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🛒 **محصول:** {product}\n"
            f"💰 **مبلغ کل:** {total_price} تومان\n"
            f"🚩 **وضعیت:** {status}\n"
            f"💳 **وضعیت پرداخت:** تایید شده"
        )

        # ۴. ذخیره در دیتابیس
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO orders (order_id, details) VALUES (?, ?)", (order_id, formatted_details))
        conn.commit()
        conn.close()
        
        return order_id, formatted_details
    except Exception as e:
        return None, f"⚠️ خطای تحلیل متن: {str(e)}"

# ================== هندلرها (حفظ تمام موارد قبلی) ==================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    if user_id == ADMIN_ID:
        markup.row("📥 ثبت سریع فاکتور (ادمین)")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور", reply_markup=main_menu(message.from_user.id))

# --- بخش ادمین: ثبت هوشمند ---
@bot.message_handler(func=lambda m: m.text == "📥 ثبت سریع فاکتور (ادمین)" and m.from_user.id == ADMIN_ID)
def start_capture(message):
    msg = bot.send_message(message.chat.id, "📑 متن کپی شده از سایت را اینجا بفرستید تا هوشمندانه ذخیره شود:")
    bot.register_next_step_handler(msg, process_capture)

def process_capture(message):
    bot.send_message(message.chat.id, "⏳ در حال پردازش...")
    oid, res = smart_extract(message.text)
    if oid:
        bot.send_message(message.chat.id, f"✅ فاکتور شماره {oid} ذخیره شد:\n\n{res}", parse_mode="Markdown", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, res, reply_markup=main_menu(message.from_user.id))

# --- بخش مشتری: پیگیری ---
@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track(message):
    msg = bot.send_message(message.chat.id, "🔢 شماره سفارش را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, show_invoice)

def show_invoice(message):
    oid = message.text.strip()
    conn = get_db_connection()
    row = conn.execute("SELECT details FROM orders WHERE order_id = ?", (oid,)).fetchone()
    conn.close()

    if row:
        bot.send_message(message.chat.id, f"📑 **فاکتور شماره {oid}**\n\n{row['details']}\n\n✅ بانه استور", parse_mode="Markdown", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ فاکتوری با این شماره یافت نشد. لطفاً از صحت شماره اطمینان حاصل کنید.", reply_markup=main_menu(message.from_user.id))

# (بخش‌های محصولات و پشتیبانی بدون تغییر باقی می‌مانند)
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def p(m): bot.send_message(m.chat.id, "🛒 لیست محصولات ما در سایت:\nhttps://banehstoore.ir/products")

# ================== وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Smart Database Mode Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
