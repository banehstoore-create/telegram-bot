import telebot
from telebot import types
import os
import re
import sqlite3
import time
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
    # جدول سفارشات
    conn.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id TEXT PRIMARY KEY, details TEXT)''')
    # جدول کاربران برای آمار و پیام همگانی
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

def add_user(user_id):
    conn = get_db_connection()
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# ================== استخراج‌گر هوشمند (ادمین) ==================
def smart_extract(raw_text):
    try:
        order_id_match = re.search(r'سفارش\s*[:：]?\s*(\d+)', raw_text)
        if not order_id_match: return None, "❌ شماره سفارش پیدا نشد."
        order_id = order_id_match.group(1)

        def fetch(pattern):
            match = re.search(pattern, raw_text, re.DOTALL)
            return match.group(1).strip() if match else "ثبت نشده"

        receiver = fetch(r"تحویل گیرنده\s*[:：]\s*([^👤📍📞💰🚩\n]+)")
        phone = fetch(r"شماره تماس\s*[:：]\s*([\d\s]+)")
        address = fetch(r"ارسال به\s*[:：]\s*([^👤📍📞💰🚩\n]+)")
        total_price = fetch(r"مبلغ کل\s*[:：]\s*([\d٬,]+)\s*تومان")
        status = fetch(r"وضعیت\s*[:：]\s*([^👤📍📞💰🚩\n]+)").replace("پرداخت شده", "").strip()

        formatted_details = (
            f"👤 **خریدار:** {receiver}\n📞 **تماس:** {phone}\n📍 **نشانی:** {address}\n"
            f"━━━━━━━━━━━━━━━\n💰 **مبلغ کل:** {total_price} تومان\n🚩 **وضعیت:** {status}"
        )
        
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO orders (order_id, details) VALUES (?, ?)", (order_id, formatted_details))
        conn.commit()
        conn.close()
        return order_id, formatted_details
    except Exception as e: return None, f"⚠️ خطا: {str(e)}"

# ================== کیبوردها ==================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    if user_id == ADMIN_ID:
        markup.row("🛠 پنل مدیریت")
    return markup

def admin_panel():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📥 ثبت سریع فاکتور", "📊 آمار ربات")
    markup.row("📢 ارسال پیام همگانی")
    markup.row("🔙 بازگشت به منوی اصلی")
    return markup

# ================== هندلرهای اصلی ==================
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🛠 پنل مدیریت" and m.from_user.id == ADMIN_ID)
def open_admin(message):
    bot.send_message(message.chat.id, "🚩 به پنل مدیریت خوش آمدید:", reply_markup=admin_panel())

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منوی اصلی")
def back_home(message):
    bot.send_message(message.chat.id, "🏠 منوی اصلی:", reply_markup=main_menu(message.from_user.id))

# --- بخش آمار ---
@bot.message_handler(func=lambda m: m.text == "📊 آمار ربات" and m.from_user.id == ADMIN_ID)
def show_stats(message):
    conn = get_db_connection()
    user_count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
    order_count = conn.execute("SELECT count(*) FROM orders").fetchone()[0]
    conn.close()
    bot.send_message(message.chat.id, f"📈 **آمار ربات بانه استور:**\n\n👥 تعداد کاربران: {user_count}\n📦 تعداد فاکتورهای ثبت شده: {order_count}", parse_mode="Markdown")

# --- بخش ارسال پیام همگانی ---
@bot.message_handler(func=lambda m: m.text == "📢 ارسال پیام همگانی" and m.from_user.id == ADMIN_ID)
def broadcast_req(message):
    msg = bot.send_message(message.chat.id, "📝 لطفا پیامی که می‌خواهید به همه کاربران ارسال شود را بفرستید:")
    bot.register_next_step_handler(msg, start_broadcast)

def start_broadcast(message):
    text = message.text
    conn = get_db_connection()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    
    count = 0
    bot.send_message(message.chat.id, "⏳ در حال ارسال پیام...")
    for user in users:
        try:
            bot.send_message(user['user_id'], text)
            count += 1
            time.sleep(0.1) # جلوگیری از اسپم تلگرام
        except: pass
    bot.send_message(message.chat.id, f"✅ پیام شما با موفقیت به {count} کاربر ارسال شد.")

# --- بخش ثبت فاکتور (ادمین) ---
@bot.message_handler(func=lambda m: m.text == "📥 ثبت سریع فاکتور" and m.from_user.id == ADMIN_ID)
def admin_capture(message):
    msg = bot.send_message(message.chat.id, "📑 متن کپی شده از سایت را بفرستید:")
    bot.register_next_step_handler(msg, process_admin_text)

def process_admin_text(message):
    oid, res = smart_extract(message.text)
    bot.send_message(message.chat.id, f"✅ فاکتور شماره {oid} ذخیره شد:\n\n{res}" if oid else res, parse_mode="Markdown")

# --- بخش پیگیری سفارش (مشتری) ---
@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_1(message):
    msg = bot.send_message(message.chat.id, "📞 لطفاً شماره تلفنی که با آن ثبت‌نام کرده‌اید را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, track_2)

def track_2(message):
    u_phone = message.text.strip()
    msg = bot.send_message(message.chat.id, f"🔢 شماره تلفن {u_phone} تایید شد. حالا شماره سفارش خود را وارد کنید:")
    bot.register_next_step_handler(msg, show_invoice)

def show_invoice(message):
    oid = message.text.strip()
    conn = get_db_connection()
    row = conn.execute("SELECT details FROM orders WHERE order_id = ?", (oid,)).fetchone()
    conn.close()
    if row:
        bot.send_message(message.chat.id, f"📑 **فاکتور شماره {oid}**\n\n{row['details']}", parse_mode="Markdown", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ فاکتوری با این شماره یافت نشد.", reply_markup=main_menu(message.from_user.id))

# سایر دکمه‌ها
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def p(m): bot.send_message(m.chat.id, "🛒 https://banehstoore.ir/products")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def s(m): bot.send_message(m.chat.id, f"📞 {PHONE_NUMBER}\n💬 {WHATSAPP}\n📢 {CHANNEL_ID}")

# ================== وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot is Active with Admin Panel</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
