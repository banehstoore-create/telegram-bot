import telebot
from telebot import types
import os
import psycopg2 # کتابخانه اتصال به دیتابیس
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
WHATSAPP = "09180514202"

# لینک دیتابیس که از Supabase گرفتید را اینجا قرار دهید یا در Render ست کنید
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:[*Sirvan3840361915#]@db.zluohfoxkpeusmtjvsoo.supabase.co:5432/postgres")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ================== مدیریت دیتابیس (ضد پاک شدن) ==================
def init_db():
    """ساخت جدول کاربران در صورت عدم وجود"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            name TEXT,
            phone TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def is_user_registered(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

def save_user_to_db(user_id, name, phone):
    if not is_user_registered(user_id):
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO users (user_id, name, phone) VALUES (%s, %s, %s)", (user_id, name, phone))
        conn.commit()
        cur.close()
        conn.close()

# اجرای اولیه برای ساخت جدول
try:
    init_db()
except Exception as e:
    print(f"Database Error: {e}")

# ================== بخش مدیریت پیام‌ها (بدون تغییر در منطق) ==================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if is_user_registered(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🛒 محصولات", "📞 پشتیبانی")
        bot.send_message(message.chat.id, "👋 خوش آمدید مجدد به بانه استور!", reply_markup=markup)
    else:
        msg = bot.send_message(message.chat.id, "👋 خوش آمدید! لطفا نام و نام خانوادگی خود را وارد کنید:")
        bot.register_next_step_handler(msg, get_name)

def get_name(message):
    user_full_name = message.text
    if not user_full_name or len(user_full_name) < 3:
        msg = bot.send_message(message.chat.id, "❌ نام معتبر نیست. مجددا بفرستید:")
        bot.register_next_step_handler(msg, get_name)
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 اشتراک‌گذاری شماره موبایل", request_contact=True))
    msg = bot.send_message(message.chat.id, f"ممنون {user_full_name}. شماره خود را تایید کنید:", reply_markup=markup)
    bot.register_next_step_handler(msg, get_phone, user_full_name)

def get_phone(message, user_full_name):
    user_id = message.from_user.id
    phone = message.contact.phone_number if message.contact else message.text
    save_user_to_db(user_id, user_full_name, phone)
    bot.send_message(ADMIN_ID, f"👤 **مشتری جدید!**\n📝 نام: {user_full_name}\n📞 شماره: {phone}")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "📞 پشتیبانی")
    bot.send_message(message.chat.id, "✅ ثبت‌نام شما با موفقیت انجام شد.", reply_markup=markup)

# ================== بخش پشتیبانی و محصولات (ثابت) ==================
@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📲 واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"))
    bot.send_message(message.chat.id, "پشتیبانی بانه استور:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer")
    )
    bot.send_message(message.chat.id, "🛒 محصولات بانه استور:", reply_markup=markup)

# ================== وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://telegram-bot-5-qw7c.onrender.com/' + BOT_TOKEN)
    return "<h1>Bot is Running with Supabase!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
