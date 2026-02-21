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
# در رندر، URL باید با https شروع شود
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://telegram-bot-6-1qt1.onrender.com")
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ================== مدیریت دیتابیس ==================
def get_db_connection():
    # استفاده از مسیر مطلق برای جلوگیری از خطای دسترسی در سرور
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
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"❌ Database error: {e}")

init_db()

# ثبت کاربر
def add_user(user_id):
    try:
        conn = get_db_connection()
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except: pass

# ================== توابع کمکی ==================
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
            f"👤 **خریدار:** {receiver}\n📞 **تماس:** {phone}\n📍 **نشانی:** {address}\n"
            f"━━━━━━━━━━━━━━━\n💰 **مبلغ کل:** {total_price} تومان\n🚩 **وضعیت:** {status}"
        )
        
        def get_live_prices():
    # لیست منابع مختلف برای اطمینان از قطع نشدن سرویس
    sources = [
        "https://api.tala.ir/v1/live", # منبع اول
        "https://brsapi.ir/FreeTalaGold/api/get_stats", # منبع دوم
        "https://api.nobitex.ir/v2/orderbook/USDTIRT" # منبع کمکی برای دلار
    ]
    
    try:
        # تلاش برای دریافت از منبع اصلی
        response = requests.get(sources[1], timeout=7)
        if response.status_code == 200:
            res = response.json()
            gold = res['gold'][0]['price']
            usd = res['currency'][0]['price']
            aed = res['currency'][2]['price']
            
            text = "💰 **قیمت لحظه‌ای بازار (تومان):**\n"
            text += "━━━━━━━━━━━━━━━\n"
            text += f"🇺🇸 دلار: {usd:,}\n"
            text += f"🇦🇪 درهم: {aed:,}\n"
            text += f"⚜️ طلای ۱۸ عیار: {gold:,}\n"
            text += "━━━━━━━━━━━━━━━\n"
            text += f"⏰ بروزرسانی: {res['date']}\n"
            text += "✅ بانه استور"
            return text
    except Exception as e:
        # اگر منبع دوم هم قطع بود، یک پیام محترمانه همراه با لینک منبع اصلی بدهد
        return "⚠️ سرویس دریافت قیمت در حال بروزرسانی است.\n\n📈 برای مشاهده قیمت‌های لحظه‌ای می‌توانید به وب‌سایت‌های مرجع مراجعه کنید یا چند دقیقه دیگر مجدداً دکمه را بزنید."
# ================== هندلرها ==================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "💰 قیمت ارز و طلا")
    markup.row("📞 پشتیبانی و تماس")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "💰 قیمت ارز و طلا")
def show_prices(message):
    bot.send_message(message.chat.id, get_live_prices(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛠 پنل مدیریت" and m.from_user.id == ADMIN_ID)
def open_admin(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📥 ثبت سریع فاکتور", "📊 آمار ربات")
    markup.row("📢 ارسال پیام همگانی")
    markup.row("🔙 بازگشت به منوی اصلی")
    bot.send_message(message.chat.id, "🚩 منوی مدیریت:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منوی اصلی")
def back_home(message):
    bot.send_message(message.chat.id, "🏠 منوی اصلی:", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_1(message):
    msg = bot.send_message(message.chat.id, "📞 شماره تلفن همراه خود را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, track_2)

def track_2(message):
    u_phone = message.text.strip()
    msg = bot.send_message(message.chat.id, f"✅ شماره {u_phone} تایید شد. شماره سفارش را وارد کنید:")
    bot.register_next_step_handler(msg, show_invoice)

def show_invoice(message):
    oid = message.text.strip()
    try:
        conn = get_db_connection()
        row = conn.execute("SELECT details FROM orders WHERE order_id = ?", (oid,)).fetchone()
        conn.close()
        if row:
            bot.send_message(message.chat.id, f"📑 **فاکتور {oid}**\n\n{row['details']}", parse_mode="Markdown", reply_markup=main_menu(message.from_user.id))
        else:
            bot.send_message(message.chat.id, "❌ یافت نشد.", reply_markup=main_menu(message.from_user.id))
    except:
        bot.send_message(message.chat.id, "⚠️ خطای دیتابیس.", reply_markup=main_menu(message.from_user.id))

# ارسال همگانی
@bot.message_handler(func=lambda m: m.text == "📢 ارسال پیام همگانی" and m.from_user.id == ADMIN_ID)
def broad_req(message):
    msg = bot.send_message(message.chat.id, "📝 پیام خود را بفرستید:")
    bot.register_next_step_handler(msg, start_broad)

def start_broad(message):
    conn = get_db_connection()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    for u in users:
        try: bot.send_message(u['user_id'], message.text); time.sleep(0.1)
        except: pass
    bot.send_message(message.chat.id, "✅ ارسال شد.")

@bot.message_handler(func=lambda m: m.text == "📥 ثبت سریع فاکتور" and m.from_user.id == ADMIN_ID)
def admin_cap(message):
    msg = bot.send_message(message.chat.id, "📑 متن سفارش را بفرستید:")
    bot.register_next_step_handler(msg, proc_admin)

def proc_admin(message):
    oid, res = smart_extract(message.text)
    bot.send_message(message.chat.id, f"✅ ثبت شد:\n\n{res}" if oid else res, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def p(m): bot.send_message(m.chat.id, "🛒 https://banehstoore.ir/products")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def s(m): bot.send_message(m.chat.id, f"📞 {PHONE_NUMBER}\n💬 {WHATSAPP}\n📢 {CHANNEL_ID}")

# ================== وب‌هوک و اجرای سرور ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot is Running...</h1>", 200

if __name__ == "__main__":
    # رندر پورت را از Environment Variable می‌خواند
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
