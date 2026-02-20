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
# حتما بررسی کنید که این آدرس در Render دقیقاً همین باشد
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}

# ================== مدیریت دیتابیس ==================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def save_user(user_id):
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)')
        cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING', (user_id,))
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(f"DB Error: {e}")

def get_all_users():
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('SELECT user_id FROM users')
        users = [row[0] for row in cur.fetchall()]
        cur.close(); conn.close()
        return users
    except: return []

# ================== منوها ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

# ================== هندلرهای اصلی ==================

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id)
    bot.send_message(message.chat.id, "👋 سلام! به ربات بانه استور خوش آمدید.\nچطور می‌توانم کمکتان کنم؟", 
                     reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products_btn(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛍 مشاهده همه محصولات", url="https://banehstoore.ir/products"))
    bot.send_message(message.chat.id, "🛒 لیست محصولات در سایت بانه استور:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_start(message):
    msg = bot.send_message(message.chat.id, "🔢 شماره سفارش خود را وارد کنید:")
    bot.register_next_step_handler(msg, track_process)

def track_process(message):
    order_id = message.text.strip()
    if order_id.isdigit():
        track_url = f"https://banehstoore.ir/profile/order-details/{order_id}/"
        bot.send_message(message.chat.id, f"📑 برای مشاهده فاکتور و جزئیات سفارش شماره {order_id} روی لینک زیر کلیک کنید:\n\n🌐 {track_url}")
    else:
        bot.send_message(message.chat.id, "❌ لطفا فقط عدد وارد کنید.")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support_btn(message):
    bot.send_message(message.chat.id, f"📞 شماره تماس: {PHONE_NUMBER}\n💬 واتساپ: https://wa.me/98{WHATSAPP[1:]}")

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def channel_btn(message):
    bot.send_message(message.chat.id, f"📢 کانال تلگرام ما:\n{CHANNEL_ID}")

# ================== وب‌هوک و مدیریت Flask ==================

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    else:
        return "Error", 403

@app.route("/")
def webhook():
    # این بخش به محض باز شدن آدرس سایت در مرورگر، اتصال تلگرام را ریست می‌کند
    bot.remove_webhook()
    status = bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    if status:
        return f"<h1>Bot is Active!</h1><p>Webhook set to: {RENDER_URL}</p>", 200
    else:
        return "<h1>Webhook Failed!</h1>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
