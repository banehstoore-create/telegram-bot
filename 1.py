import telebot
from telebot import types
import os
import re
import requests
import sqlite3
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
# توکن API میکسین خود را اینجا یا در متغیرهای Render قرار دهید
MIXIN_API_KEY = os.environ.get("MIXIN_API_KEY", "YOUR_TOKEN_HERE") 
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
                 (order_id TEXT PRIMARY KEY, details TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ================== توابع بخش مشتریان (Mixin API) ==================
def fetch_mixin_customers():
    """دریافت لیست مشتریان با آدرس اصلاح شده"""
    # نکته: آدرس زیر را بر اساس دامنه اصلی سایت خودتان تغییر دهید
    # اگر آدرس سایت شما مثلا banehstoore.ir است، از آن استفاده کنید
    BASE_URL = "https://banehstoore.ir" # یا آدرسی که میکسین به شما داده
    url = f"{BASE_URL}/api/management/v1/customers/"
    
    headers = {
        'Authorization': f'Api-Key {MIXIN_API_KEY}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        # لاگ برای دیباگ در کنسول رندر
        print(f"Requesting to: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # طبق مستندات تصویر ۳، نتایج در فیلد results هستند
            customers = data.get('results', [])
            
            if not customers:
                return "📭 لیست مشتریان در حال حاضر خالی است."
            
            report = f"👥 **لیست مشتریان (بروزرسانی شده)**\n"
            report += "━━━━━━━━━━━━━━━\n"
            
            for person in customers[:10]: # نمایش ۱۰ نفر آخر
                # نام فیلدها را بر اساس خروجی JSON (تصویر ۳) تنظیم کنید
                name = person.get('first_name', 'کاربر')
                last_name = person.get('last_name', '')
                username = person.get('username', '---')
                report += f"👤 {name} {last_name}\n🆔 @{username}\n\n"
            
            return report
        elif response.status_code == 404:
            return "❌ **خطای 404:** آدرس API پیدا نشد. لطفاً آدرس سایت (BASE_URL) را در کد چک کنید."
        elif response.status_code == 401:
            return "❌ **خطای 401:** توکن API معتبر نیست."
        else:
            return f"❌ خطا با کد: {response.status_code}"
    except Exception as e:
        return f"⚠️ خطای ارتباطی: {str(e)}"
# ================== استخراج‌گر هوشمند فاکتور (حفظ شده از قبل) ==================
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

# ================== منوها و هندلرها ==================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    if user_id == ADMIN_ID:
        markup.row("📥 ثبت سریع فاکتور (ادمین)")
        markup.row("👥 لیست مشتریان (Mixin)") # دکمه جدید
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 خوش آمدید", reply_markup=main_menu(message.from_user.id))

# --- هندلر لیست مشتریان ---
@bot.message_handler(func=lambda m: m.text == "👥 لیست مشتریان (Mixin)" and m.from_user.id == ADMIN_ID)
def show_mixin_customers(message):
    bot.send_message(message.chat.id, "⏳ در حال استعلام از پنل میکسین...")
    result = fetch_mixin_customers()
    bot.send_message(message.chat.id, result, parse_mode="Markdown")

# --- سایر هندلرها (حفظ شده) ---
@bot.message_handler(func=lambda m: m.text == "📥 ثبت سریع فاکتور (ادمین)" and m.from_user.id == ADMIN_ID)
def start_capture(message):
    msg = bot.send_message(message.chat.id, "📑 متن کپی شده از سایت را اینجا بفرستید:")
    bot.register_next_step_handler(msg, process_capture)

def process_capture(message):
    oid, res = smart_extract(message.text)
    bot.send_message(message.chat.id, f"✅ فاکتور {oid} ذخیره شد:\n\n{res}" if oid else res, parse_mode="Markdown")

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
        bot.send_message(message.chat.id, f"📑 **فاکتور {oid}**\n\n{row['details']}", parse_mode="Markdown", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ یافت نشد.", reply_markup=main_menu(message.from_user.id))

# وب‌هوک
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Bot is Active with Mixin API</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
