import telebot
from telebot import types
import os
import re
import sqlite3
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"

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

# ================== استخراج‌گر هوشمند (بخش ادمین) ==================
def smart_extract(raw_text):
    try:
        order_id_match = re.search(r'سفارش\s*[:：]?\s*(\d+)', raw_text)
        if not order_id_match:
            return None, "❌ شماره سفارش در متن پیدا نشد."
        
        order_id = order_id_match.group(1)

        def fetch(pattern):
            match = re.search(pattern, raw_text, re.DOTALL)
            return match.group(1).strip() if match else "ثبت نشده"

        receiver = fetch(r"تحویل گیرنده\s*[:：]\s*([^👤📍📞💰🚩\n]+)")
        phone = fetch(r"شماره تماس\s*[:：]\s*([\d\s]+)")
        address = fetch(r"ارسال به\s*[:：]\s*([^👤📍📞💰🚩\n]+)")
        total_price = fetch(r"مبلغ کل\s*[:：]\s*([\d٬,]+)\s*تومان")
        status_raw = fetch(r"وضعیت\s*[:：]\s*([^👤📍📞💰🚩\n]+)")
        status = status_raw.replace("پرداخت شده", "").strip()

        product = "نامشخص"
        product_match = re.search(r'([^\n]*(?:سرخ کن|اسپرسو|یونی|مدل|تعداد)[^\n]*)', raw_text)
        if product_match:
            product = product_match.group(1).split("تعداد")[0].strip()

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

        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO orders (order_id, details) VALUES (?, ?)", (order_id, formatted_details))
        conn.commit()
        conn.close()
        
        return order_id, formatted_details
    except Exception as e:
        return None, f"⚠️ خطای تحلیل متن: {str(e)}"

# ================== هندلرها و منوها ==================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    if user_id == ADMIN_ID:
        markup.row("📥 ثبت سریع فاکتور (ادمین)")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 به ربات بانه استور خوش آمدید.", reply_markup=main_menu(message.from_user.id))

# --- بخش ادمین ---
@bot.message_handler(func=lambda m: m.text == "📥 ثبت سریع فاکتور (ادمین)" and m.from_user.id == ADMIN_ID)
def admin_capture(message):
    msg = bot.send_message(message.chat.id, "📑 متن کپی شده از سایت را بفرستید:")
    bot.register_next_step_handler(msg, process_admin_text)

def process_admin_text(message):
    oid, res = smart_extract(message.text)
    if oid:
        bot.send_message(message.chat.id, f"✅ فاکتور شماره {oid} ذخیره شد:\n\n{res}", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, res)

# --- بخش پیگیری سفارش (اصلاح شده: درخواست شماره تماس) ---
@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_step_1(message):
    msg = bot.send_message(message.chat.id, "📞 لطفاً شماره تلفنی که با آن ثبت‌نام کرده‌اید را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, track_step_2)

def track_step_2(message):
    user_phone = message.text.strip()
    msg = bot.send_message(message.chat.id, f"🔢 شماره تلفن {user_phone} ثبت شد. حالا شماره سفارش خود را وارد کنید:")
    bot.register_next_step_handler(msg, show_final_invoice, user_phone)

def show_final_invoice(message, user_phone):
    order_id = message.text.strip()
    conn = get_db_connection()
    row = conn.execute("SELECT details FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()

    if row:
        # اینجا می‌توان چک کرد که آیا شماره تلفن در متن فاکتور هست یا خیر (اختیاری)
        bot.send_message(message.chat.id, f"📑 **فاکتور شماره {order_id}**\n\n{row['details']}\n\n✅ بانه استور", 
                         parse_mode="Markdown", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ فاکتوری با این شماره یافت نشد.", reply_markup=main_menu(message.from_user.id))

# --- سایر دکمه‌ها ---
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products(m):
    bot.send_message(m.chat.id, "🛒 لیست محصولات در سایت:\nhttps://banehstoore.ir/products")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support(m):
    text = f"📞 شماره تماس: {PHONE_NUMBER}\n💬 واتساپ: {WHATSAPP}\n📢 کانال: {CHANNEL_ID}"
    bot.send_message(m.chat.id, text)

# ================== اجرای وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Baneh Store Bot: Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
