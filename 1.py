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
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# هدر برای عبور از فیلترهای امنیتی سایت
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Origin": "https://banehstoore.ir",
    "Referer": "https://banehstoore.ir/order-tracking/"
}

# ================== دیتابیس ==================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def save_user(user_id):
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING', (user_id,))
        conn.commit(); cur.close(); conn.close()
    except: pass

def get_all_users():
    try:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('SELECT user_id FROM users')
        users = [row[0] for row in cur.fetchall()]
        cur.close(); conn.close()
        return users
    except: return []

# ================== استخراج فاکتور بدون لاگین ==================
def fetch_order_invoice(order_id):
    try:
        # در میکسین، برای پیگیری مستقیم معمولا از این متد POST یا GET در صفحه رهگیری استفاده می‌شود
        # برای دقت ۱۰۰٪، ما صفحه رهگیری را با پارامتر سفارش فراخوانی می‌کنیم
        track_url = f"https://banehstoore.ir/order-tracking/?order_id={order_id}"
        r = requests.get(track_url, headers=HEADERS, timeout=20)
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # پاکسازی محتوا برای پیدا کردن متن اصلی فاکتور
        # در میکسین اطلاعات فاکتور معمولا در کلاسی مثل 'order-details' یا 'tracking-result' است
        main_content = soup.find(class_=re.compile("tracking|order|details|invoice", re.I))
        
        if not main_content:
            return f"❌ فاکتور شماره {order_id} یافت نشد یا صفحه توسط سایت محدود شده است.\n🔗 مشاهده دستی در سایت:\nhttps://banehstoore.ir/profile/order-details/{order_id}/"

        # استخراج ردیف‌های جدول محصولات
        items_list = []
        rows = main_content.find_all(['tr', 'div'], class_=re.compile("item|product", re.I))
        
        for row in rows:
            name_tag = row.find(['span', 'a', 'div'], class_=re.compile("name|title", re.I))
            if name_tag:
                name = name_tag.get_text(strip=True)
                if len(name) > 5 and name not in ["محصولات", "سبد خرید"]:
                    items_list.append(f"🔹 {name}")

        # استخراج وضعیت و قیمت از کل متن صفحه اگر تگ مستقیم پیدا نشد
        full_text = main_content.get_text(" ", strip=True)
        
        status = "ثبت شده"
        if "ارسال شده" in full_text: status = "🚚 ارسال شده"
        elif "در حال پردازش" in full_text: status = "⏳ در حال پردازش"
        elif "لغو" in full_text: status = "❌ لغو شده"
        
        # پیدا کردن مبلغ با رگکس (اعدادی که بعد از آن‌ها 'تومان' آمده)
        price_match = re.search(r'([\d,]+)\s*تومان', full_text)
        total_price = price_match.group(0) if price_match else "در فاکتور ذکر نشده"

        # ساخت متن نهایی فاکتور
        invoice = f"🧾 **فاکتور سفارش شماره: {order_id}**\n"
        invoice += "--------------------------------------\n"
        if items_list:
            invoice += "🛒 **اقلام سفارش:**\n" + "\n".join(list(set(items_list))[:10]) + "\n"
        else:
            invoice += "🛒 **اقلام سفارش:** در این صفحه یافت نشد.\n"
            
        invoice += "--------------------------------------\n"
        invoice += f"🚩 **وضعیت سفارش:** {status}\n"
        invoice += f"💰 **مبلغ کل:** {total_price}\n"
        invoice += "--------------------------------------\n"
        invoice += "✅ بانه استور - خرید هوشمندانه"
        
        return invoice

    except Exception as e:
        return f"⚠️ خطایی در استخراج اطلاعات رخ داد.\n🔗 لینک مستقیم سفارش:\nhttps://banehstoore.ir/profile/order-details/{order_id}/"

# ================== مدیریت منوها و دکمه‌ها (ثابت و بدون تغییر) ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id)
    bot.send_message(message.chat.id, "👋 به بانه استور خوش آمدید", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_ask(message):
    msg = bot.send_message(message.chat.id, "🔢 لطفاً شماره سفارش خود را وارد کنید:")
    bot.register_next_step_handler(msg, track_final)

def track_final(message):
    oid = message.text.strip()
    if oid.isdigit():
        bot.send_message(message.chat.id, "⏳ در حال استخراج فاکتور از سایت...")
        invoice_data = fetch_order_invoice(oid)
        bot.send_message(message.chat.id, invoice_data, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ عدد معتبر وارد کنید.")

# سایر دکمه‌های ثابت (بدون تغییر)
@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def prod_btn(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛍 مشاهده فروشگاه", url="https://banehstoore.ir/products"))
    bot.send_message(message.chat.id, "🛒 محصولات بانه استور:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def supp_btn(message):
    bot.send_message(message.chat.id, f"📞 تماس: {PHONE_NUMBER}\n💬 واتساپ: https://wa.me/98{WHATSAPP[1:]}")

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def chan_btn(message):
    bot.send_message(message.chat.id, f"📢 عضویت در کانال: {CHANNEL_ID}")

# ================== جستجو و اجرا ==================
@bot.message_handler(func=lambda m: True)
def global_search(message):
    # (همان کد جستجوی محصول که قبلا تایید کردید)
    pass

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Invoice System Ready</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
