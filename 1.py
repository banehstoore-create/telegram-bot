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
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================== مدیریت دیتابیس Neon ==================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error initializing database: {e}")

def save_user(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING', (user_id,))
        conn.commit()
        cur.close()
        conn.close()
    except: pass

def get_all_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT user_id FROM users')
        users = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return users
    except: return []

# ایجاد جدول در دیتابیس هنگام شروع
init_db()

# ================== توابع محصول ==================
def fetch_product(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "محصول بانه استور"
        image = soup.find("meta", property="og:image")["content"] if soup.find("meta", property="og:image") else None
        price_tag = soup.find("p", class_="price")
        price = price_tag.get_text(strip=True) if price_tag else "تماس بگیرید"
        stock = "✅ موجود" if "موجود" in soup.text and "ناموجود" not in soup.text else "❌ ناموجود"
        return title, image, price, stock
    except: return None

# ================== مدیریت پیام‌ها ==================

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id) # ذخیره کاربر در Neon
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "📞 پشتیبانی و تماس")
    markup.add("📢 کانال فروشگاه")
    
    bot.send_message(
        message.chat.id,
        "👋 به ربات بانه استور خوش آمدید\nبرای مشاهده محصولات یا ارتباط با ما از منوی زیر استفاده کنید:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker/"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer/"),
        types.InlineKeyboardButton("🧹 جاروبرقی", url="https://banehstoore.ir/product-category/vacuum-cleaner/"),
        types.InlineKeyboardButton("🍲 غذاساز و خردکن", url="https://banehstoore.ir/product-category/food-processor/"),
        types.InlineKeyboardButton("🍳 لوازم پخت و پز", url="https://banehstoore.ir/product-category/cookware/"),
        types.InlineKeyboardButton("🍹 آبمیوه‌گیری", url="https://banehstoore.ir/product-category/appliance/juicer/"),
        types.InlineKeyboardButton("📺 صوتی و تصویری", url="https://banehstoore.ir/product-category/video-audio/"),
        types.InlineKeyboardButton("🧺 شستشو و نظافت", url="https://banehstoore.ir/product-category/washing-machine-dishwasher/"),
        types.InlineKeyboardButton("🧊 یخچال فریزر", url="https://banehstoore.ir/product-category/refrigerator-freezer/"),
        types.InlineKeyboardButton("🛍 مشاهده همه محصولات", url="https://banehstoore.ir/shop/")
    )
    bot.send_message(message.chat.id, "🛒 **دسته‌بندی‌های محصولات:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📞 تماس مستقیم", callback_data="call_us"),
        types.InlineKeyboardButton("💬 پیام در واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"),
        types.InlineKeyboardButton("📍 آدرس فروشگاه (روی نقشه)", url=MAP_URL)
    )
    bot.send_message(message.chat.id, "📞 راه‌های ارتباطی با بانه استور:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "call_us")
def call_contact(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"📱 شماره تماس:\n`{PHONE_NUMBER}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def channel_info(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"))
    bot.send_message(message.chat.id, f"📢 کانال تلگرام ما:\n{CHANNEL_ID}", reply_markup=markup)

# ================== پنل مدیریت اختصاصی ادمین ==================

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        users = get_all_users()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📣 ارسال پیام همگانی", "📊 آمار کاربران")
        markup.add("🔙 بازگشت به منوی اصلی")
        bot.send_message(message.chat.id, f"🛠 **پنل مدیریت**\nتعداد کاربران در دیتابیس: `{len(users)}`", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 آمار کاربران" and m.from_user.id == ADMIN_ID)
def stats(message):
    users = get_all_users()
    bot.send_message(message.chat.id, f"👥 تعداد کل کاربران ثبت شده: `{len(users)}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📣 ارسال پیام همگانی" and m.from_user.id == ADMIN_ID)
def broadcast_prompt(message):
    msg = bot.send_message(message.chat.id, "لطفاً پیام خود را (متن، عکس، فایل یا کد تخفیف) بفرستید:")
    bot.register_next_step_handler(msg, do_broadcast)

def do_broadcast(message):
    users = get_all_users()
    success = 0
    for uid in users:
        try:
            bot.copy_message(uid, message.chat.id, message.message_id)
            success += 1
        except: pass
    bot.send_message(ADMIN_ID, f"✅ پیام شما با موفقیت برای {success} نفر ارسال شد.")

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منوی اصلی")
def back_home(message):
    start(message)

# ================== ارسال محصول به کانال (هوشمند) ==================

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and "banehstoore.ir" in (m.text or ""))
def admin_post_product(message):
    bot.send_message(message.chat.id, "⏳ در حال استخراج و ارسال به کانال...")
    try:
        url = re.search(r'(https?://[^\s]+)', message.text).group(0)
        data = fetch_product(url)
        if data:
            title, image, price, stock = data
            caption = f"🛍 **{title}**\n\n💰 قیمت: {price}\n📦 وضعیت: {stock}\n\n✅ ضمانت اصالت کالا\n🚚 ارسال به سراسر کشور\n🤝 خرید مطمئن از بانه استور\n\n🆔 {CHANNEL_ID}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🛒 خرید از سایت", url=url),
                       types.InlineKeyboardButton("📲 مشاوره و سفارش", url=f"https://wa.me/98{WHATSAPP[1:]}"))
            if image:
                bot.send_photo(CHANNEL_ID, image, caption=caption, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(CHANNEL_ID, caption, parse_mode="Markdown", reply_markup=markup)
            bot.send_message(message.chat.id, "✅ محصول در کانال منتشر شد.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")

# ================== تنظیمات وب‌هوک و سرور ==================

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Baneh Stoore Bot is LIVE with Neon DB!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
