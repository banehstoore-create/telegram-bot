import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask, request

# ================== تنظیمات ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = "uc1_B9-8fkDfMguDhPDdDyWztzJJt6kHA_foPc4tJYp3x-_kGPGFNsirga_uwtcBPXQ5lejaooZnlZ6ryyyxsw"
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ذخیره موقت وضعیت کاربران (در دیتابیس واقعی بهتر است)
user_data = {}

# ================== تابع اصلی استخراج فاکتور ==================
def get_full_invoice_details(order_id, phone):
    try:
        # آدرس پیگیری مستقیم با پارامترهای شناسایی
        url = f"https://banehstoore.ir/order-tracking/?order_id={order_id}&phone={phone}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # استخراج متن اصلی فاکتور
        # در اینجا ربات تمام متن‌های داخل باکس فاکتور را جارو می‌کند
        invoice_box = soup.find(class_=lambda x: x and ('order' in x or 'tracking' in x or 'invoice' in x))
        
        if not invoice_box:
            return "❌ متأسفانه فاکتوری با این مشخصات یافت نشد. لطفاً شماره سفارش یا شماره موبایل را بررسی کنید."

        # تمیز کردن متن برای نمایش شکیل
        raw_text = invoice_box.get_text(separator="\n", strip=True)
        
        # ساخت فاکتور نهایی
        report = f"🧾 **فاکتور کامل بانه استور (تأیید شده)**\n"
        report += "━━━━━━━━━━━━━━━\n"
        report += raw_text
        report += "\n━━━━━━━━━━━━━━━\n"
        report += "✅ این اطلاعات مستقیماً از سایت فراخوانی شده است."
        
        return report

    except Exception as e:
        return "⚠️ در حال حاضر ارتباط با سایت برقرار نشد. لطفاً لحظاتی دیگر تلاش کنید."

# ================== مراحل پیگیری سفارش (تأیید شماره موبایل) ==================

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def ask_phone(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    # ایجاد دکمه ارسال شماره موبایل
    btn = types.KeyboardButton("📲 ارسال و تأیید شماره موبایل", request_contact=True)
    markup.add(btn)
    
    msg = bot.send_message(message.chat.id, 
                           "🔐 برای مشاهده جزئیات فاکتور، ابتدا باید شماره موبایل خود را تأیید کنید.\n\nلطفاً روی دکمه زیر کلیک کنید:", 
                           reply_markup=markup)
    bot.register_next_step_handler(msg, get_phone_and_ask_order)

def get_phone_and_ask_order(message):
    if message.contact:
        phone = message.contact.phone_number
        # حذف +98 یا 0098 از ابتدای شماره برای هماهنگی با سایت
        if phone.startswith('+98'): phone = '0' + phone[3:]
        if phone.startswith('98'): phone = '0' + phone[2:]
        
        user_data[message.chat.id] = {'phone': phone}
        
        # حذف کیبورد قبلی و پرسیدن شماره سفارش
        markup = types.ReplyKeyboardRemove()
        msg = bot.send_message(message.chat.id, 
                               f"✅ شماره `{phone}` تأیید شد.\n\n🔢 حالا لطفاً **شماره سفارش** خود را وارد کنید:", 
                               reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, final_invoice_step)
    else:
        # اگر کاربر دکمه را نزد و متن فرستاد
        bot.send_message(message.chat.id, "❌ خطا! شما باید حتماً روی دکمه 'ارسال شماره موبایل' کلیک کنید.", reply_markup=get_main_keyboard())

def final_invoice_step(message):
    order_id = message.text.strip()
    chat_id = message.chat.id
    
    if order_id.isdigit() and chat_id in user_data:
        phone = user_data[chat_id]['phone']
        bot.send_message(chat_id, "⏳ در حال استعلام فاکتور و تطبیق اطلاعات...")
        
        invoice_content = get_full_invoice_details(order_id, phone)
        bot.send_message(chat_id, invoice_content, parse_mode="Markdown", reply_markup=get_main_keyboard())
    else:
        bot.send_message(chat_id, "❌ شماره سفارش نامعتبر است.", reply_markup=get_main_keyboard())

# ================== منوی اصلی ==================
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 خوش آمدید به بانه استور.\nگزینه مورد نظر را انتخاب کنید:", 
                     reply_markup=get_main_keyboard())

# بقیه هندلرها (پشتیبانی و محصولات) ...

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Security System Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
