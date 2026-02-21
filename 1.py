import telebot
from telebot import types
import os
import re
import sqlite3
import time
import requests
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://telegram-bot-6-1qt1.onrender.com")
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ================== مدیریت دیتابیس ==================
def get_db_connection():
    db_path = os.path.join(os.getcwd(), 'baneh_orders.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db_connection()
        conn.execute('CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, details TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

init_db()

def add_user(user_id):
    try:
        conn = get_db_connection()
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except: pass

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
        total_price = fetch(r"مبلغ کل\s*[:：]\s*([\d٬,]+)")
        status = fetch(r"وضعیت\s*[:：]\s*([^👤📍📞💰🚩\n]+)").replace("پرداخت شده", "").strip()

        formatted_details = (
            f"👤 **خریدار:** {receiver}\n📞 **تماس:** <code>{phone}</code>\n📍 **نشانی:** {address}\n"
            f"━━━━━━━━━━━━━━━\n💰 **مبلغ کل:** {total_price} تومان\n🚩 **وضعیت:** {status}"
        )
        
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO orders (order_id, details) VALUES (?, ?)", (order_id, formatted_details))
        conn.commit()
        conn.close()
        return order_id, formatted_details
    except Exception as e: return None, f"⚠️ خطا: {str(e)}"

# ================== دریافت قیمت دلار (منابع چندگانه) ==================
def get_usd_price():
    sources = [
        {"name": "نوبیتکس", "url": "https://api.nobitex.ir/v2/orderbook/USDTIRT"},
        {"name": "والکس", "url": "https://api.wallex.ir/v1/markets"}
    ]
    for src in sources:
        try:
            res = requests.get(src["url"], timeout=5).json()
            if "nobitex" in src["url"]:
                price = int(res['lastTradePrice']) / 10
            else:
                price = int(res['result']['symbols']['USDTIRT']['stats']['lastPrice']) / 10
            
            return (f"💵 **قیمت لحظه‌ای دلار (تومان):**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"💰 قیمت: **{int(price):,} تومان**\n"
                    f"🏦 منبع: {src['name']}\n"
                    f"⏰ بروزرسانی: {time.strftime('%H:%M')}\n"
                    f"✅ بانه استور")
        except: continue
    return "⚠️ منابع قیمت‌دهی موقتاً در دسترس نیستند. لطفاً دقایقی دیگر تلاش کنید."

# ================== منوها و کیبوردها ==================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "💰 قیمت لحظه‌ای دلار")
    markup.row("📞 پشتیبانی و تماس")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

def admin_panel():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📥 ثبت سریع فاکتور", "📊 آمار ربات")
    markup.row("📢 ارسال پیام همگانی")
    markup.row("🔙 بازگشت به منوی اصلی")
    return markup

# ================== هندلرهای تلگرام ==================
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    bot.send_message(message.chat.id, "👋 به ربات بانه استور خوش آمدید", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "💰 قیمت لحظه‌ای دلار")
def usd_handler(message):
    bot.send_message(message.chat.id, "⏳ در حال دریافت قیمت...")
    bot.send_message(message.chat.id, get_usd_price(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛠 پنل مدیریت" and m.from_user.id == ADMIN_ID)
def open_admin(message):
    bot.send_message(message.chat.id, "🚩 منوی مدیریت فعال شد:", reply_markup=admin_panel())

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منوی اصلی")
def back_home(message):
    bot.send_message(message.chat.id, "🏠 منوی اصلی:", reply_markup=main_menu(message.from_user.id))

# --- بخش پیگیری سفارش (درخواست شماره تلفن و سپس سفارش) ---
@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_1(message):
    msg = bot.send_message(message.chat.id, "📞 لطفاً شماره تماسی که با آن ثبت‌نام کرده‌اید را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, track_2)

def track_2(message):
    u_phone = message.text.strip()
    msg = bot.send_message(message.chat.id, f"✅ شماره {u_phone} ثبت شد. حالا شماره سفارش خود را وارد کنید:")
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

# --- بخش آمار و پیام همگانی ---
@bot.message_handler(func=lambda m: m.text == "📊 آمار ربات" and m.from_user.id == ADMIN_ID)
def stats(message):
    conn = get_db_connection()
    u = conn.execute("SELECT count(*) FROM users").fetchone()[0]
    o = conn.execute("SELECT count(*) FROM orders").fetchone()[0]
    conn.close()
    bot.send_message(message.chat.id, f"📈 **آمار فعلی:**\n\n👥 کاربران: {u}\n📦 فاکتورها: {o}")

@bot.message_handler(func=lambda m: m.text == "📢 ارسال پیام همگانی" and m.from_user.id == ADMIN_ID)
def broad_req(message):
    msg = bot.send_message(message.chat.id, "📝 پیام خود را بنویسید:")
    bot.register_next_step_handler(msg, start_broad)

def start_broad(message):
    conn = get_db_connection()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    count = 0
    for u in users:
        try:
            bot.send_message(u['user_id'], message.text)
            count += 1
            time.sleep(0.1)
        except: pass
    bot.send_message(message.chat.id, f"✅ پیام به {count} نفر ارسال شد.")

@bot.message_handler(func=lambda m: m.text == "📥 ثبت سریع فاکتور" and m.from_user.id == ADMIN_ID)
def admin_cap(message):
    msg = bot.send_message(message.chat.id, "📑 متن کپی شده از سایت را بفرستید:")
    bot.register_next_step_handler(msg, proc_admin)

def proc_admin(message):
    oid, res = smart_extract(message.text)
    bot.send_message(message.chat.id, f"✅ ثبت شد:\n\n{res}" if oid else res, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def p(m): bot.send_message(m.chat.id, "🛒 https://banehstoore.ir/products")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def s(m): bot.send_message(m.chat.id, f"📞 {PHONE_NUMBER}\n💬 {WHATSAPP}\n📢 {CHANNEL_ID}")

# ================== تنظیمات وب‌هوک و Flask ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot is Active</h1>", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
