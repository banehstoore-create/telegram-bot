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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Cookie": MY_COOKIE,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8",
    "Referer": "https://banehstoore.ir/profile/orders/"
}

# ================== مدیریت دیتابیس ==================
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id TEXT PRIMARY KEY, content TEXT)''')
    conn.commit()
    conn.close()

def save_order_to_db(order_id, content):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO orders (order_id, content) VALUES (?, ?)", (order_id, content))
    conn.commit()
    conn.close()

def get_order_from_db(order_id):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT content FROM orders WHERE order_id=?", (order_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

init_db()

# ================== تابع استخراج دقیق اطلاعات ==================
def scrape_and_store(url):
    try:
        # استخراج شماره سفارش از لینک
        match = re.search(r'order-details/(\d+)', url)
        order_id = match.group(1) if match else url.strip().split('/')[-1]

        response = requests.get(url, headers=HEADERS, timeout=25)
        if "login" in response.url or response.status_code != 200:
            return None, "❌ عدم دسترسی (کوکی منقضی شده یا اشتباه است)"

        soup = BeautifulSoup(response.text, "html.parser")
        
        # متد جدید برای پیدا کردن مقدار بر اساس لایبل در سایت‌های Django/WP
        def find_value(label_text):
            # پیدا کردن تگی که شامل متن لایبل است
            element = soup.find(string=re.compile(label_text))
            if element:
                # معمولاً مقدار در تگ والد یا تگ بعدی است
                parent_text = element.parent.get_text(strip=True)
                # حذف خود لایبل از متن برای رسیدن به مقدار
                value = parent_text.replace(label_text, "").replace(":", "").replace("：", "").strip()
                if value: return html.escape(value)
                
                # اگر در تگ والد نبود، تگ بعدی را چک کن
                nxt = element.find_next()
                if nxt: return html.escape(nxt.get_text(strip=True))
            return "یافت نشد"

        receiver = find_value("تحویل گیرنده")
        phone = find_value("شماره تماس")
        address = find_value("ارسال به")
        price = find_value("مبلغ کل")
        status = find_value("وضعیت")

        # اگر همه یافت نشد شدند، احتمالاً ساختار عوض شده یا دسترسی نیست
        if receiver == "یافت نشد" and price == "یافت نشد":
            return None, "❌ اطلاعات در صفحه یافت نشد. ساختار سایت تغییر کرده است."

        invoice_content = (
            f"👤 **تحویل گیرنده:** {receiver}\n"
            f"📞 **شماره تماس:** {phone}\n"
            f"📍 **آدرس:** {address}\n"
            f"💰 **مبلغ کل:** {price}\n"
            f"🚩 **وضعیت:** {status}"
        )
        
        save_order_to_db(order_id, invoice_content)
        return order_id, invoice_content
    except Exception as e:
        return None, f"خطای فنی: {str(e)}"

# ================== هندلرها و کیبورد ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("📥 ثبت لینک سفارش (ادمین)")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📥 ثبت لینک سفارش (ادمین)" and m.from_user.id == ADMIN_ID)
def admin_ask_link(message):
    msg = bot.send_message(message.chat.id, "🔗 لینک سفارش را بفرستید تا در دیتابیس ذخیره شود:")
    bot.register_next_step_handler(msg, process_admin_link)

def process_admin_link(message):
    url = message.text.strip()
    if "banehstoore.ir" in url:
        bot.send_message(message.chat.id, "⏳ در حال استخراج و ذخیره...")
        oid, res = scrape_and_store(url)
        if oid:
            bot.send_message(message.chat.id, f"✅ سفارش {oid} ذخیره شد:\n\n{res}", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, res)
    else:
        bot.send_message(message.chat.id, "❌ لینک اشتباه است.")

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_input(message):
    msg = bot.send_message(message.chat.id, "🔢 شماره سفارش را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, show_invoice)

def show_invoice(message):
    oid = message.text.strip()
    content = get_order_from_db(oid)
    if content:
        bot.send_message(message.chat.id, f"📑 **فاکتور شماره {oid}**\n\n{content}\n\n✅ بانه استور", parse_mode="Markdown", reply_markup=get_main_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ این شماره سفارش در دیتابیس ما ثبت نشده است.", reply_markup=get_main_keyboard(message.from_user.id))

# سایر دکمه‌ها
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def p(m): bot.send_message(m.chat.id, "🛒 https://banehstoore.ir/products")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def s(m): bot.send_message(m.chat.id, f"📞 {PHONE_NUMBER}\n💬 {WHATSAPP}")

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def c(m): bot.send_message(m.chat.id, f"📢 {CHANNEL_ID}")

# وب‌هوک
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot is Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
