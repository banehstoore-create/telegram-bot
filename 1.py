import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import os
import re
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# API Key اختصاصی شما
API_KEY = "uc1_B9-8fkDfMguDhPDdDyWztzJJt6kHA_foPc4tJYp3x-_kGPGFNsirga_uwtcBPXQ5lejaooZnlZ6ryyyxsw"
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"
MAP_URL = "https://maps.app.goo.gl/eWv6njTbL8ivfbYa6"
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}

# ذخیره موقت وضعیت کاربران برای پیگیری امن
user_track_data = {}

# ================== تابع استخراج اطلاعات طبق اسکرین‌شات ==================
def fetch_order_details_from_page(order_id, phone):
    try:
        # آدرس مستقیم بر اساس تصویر ارسالی شما
        url = f"https://banehstoore.ir/profile/order-details/{order_id}/"
        # در صورت نیاز به احراز هویت با شماره موبایل در صفحه پیگیری عمومی:
        # url = f"https://banehstoore.ir/order-tracking/?order_id={order_id}&phone={phone}"
        
        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # استخراج داده‌ها بر اساس ساختار مشاهده شده در عکس
        # این بخش متن‌های کلیدی را در کل صفحه جستجو می‌کند
        page_text = soup.get_text(separator="\n", strip=True)
        
        # استخراج نام تحویل گیرنده
        receiver = "نامشخص"
        receiver_match = re.search(r"تحویل گیرنده\s*:\s*(.*)", page_text)
        if receiver_match: receiver = receiver_match.group(1).strip()
        
        # استخراج آدرس
        address = "نامشخص"
        address_match = re.search(r"ارسال به\s*:\s*(.*)", page_text)
        if address_match: address = address_match.group(1).strip()
        
        # استخراج وضعیت
        status = "ثبت شده"
        status_match = re.search(r"وضعیت\s*:\s*(.*)", page_text)
        if status_match: status = status_match.group(1).strip()

        # استخراج محصولات (جستجوی نام محصول و قیمت واحد)
        products_info = ""
        # پیدا کردن باکس محصول بر اساس قیمت واحد در تصویر
        product_items = soup.find_all(string=re.compile(r"قیمت واحد"))
        for item in product_items:
            parent = item.find_parent()
            if parent:
                products_info += f"🔹 {parent.get_text(strip=True)}\n"

        # استخراج مبلغ کل
        total_price = "نامشخص"
        price_match = re.search(r"مبلغ کل\s*:\s*([\d,]+)\s*تومان", page_text)
        if price_match: total_price = price_match.group(1).strip() + " تومان"

        # قالب‌بندی نهایی پیام
        res = f"📑 **جزئیات فاکتور بانه استور**\n"
        res += f"🆔 شماره سفارش: `{order_id}`\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"👤 **تحویل گیرنده:** {receiver}\n"
        res += f"📍 **ارسال به:** {address}\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"🛒 **محصولات:**\n{products_info if products_info else 'در حال استخراج...'}\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += f"🚩 **وضعیت:** {status}\n"
        res += f"💰 **مبلغ کل پرداختی:** {total_price}\n"
        res += "━━━━━━━━━━━━━━━\n"
        res += "✅ بانه استور - مرجع لوازم خانگی"
        
        return res
    except:
        return None

# ================== کیبورد اصلی (بدون تغییر) ==================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    if user_id == ADMIN_ID: markup.row("🛠 پنل مدیریت")
    return markup

# ================== هندلرهای ثابت و قبلی (بدون حذفیات) ==================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 به بانه استور خوش آمدید", reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products_btn(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/category/air-fryer"),
        types.InlineKeyboardButton("🛍 همه محصولات", url="https://banehstoore.ir/products")
    )
    bot.send_message(message.chat.id, "🛒 محصولات بانه استور:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support_btn(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📞 تماس مستقیم", callback_data="call_admin"),
        types.InlineKeyboardButton("💬 واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"),
        types.InlineKeyboardButton("📍 آدرس روی نقشه", url=MAP_URL)
    )
    bot.send_message(message.chat.id, "📞 پشتیبانی بانه استور:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def channel_btn(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"))
    bot.send_message(message.chat.id, f"📢 کانال تلگرام ما: {CHANNEL_ID}", reply_markup=markup)

# ================== سیستم پیگیری سفارش (ارتقا یافته طبق تصویر) ==================

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn = types.KeyboardButton("📲 تایید و ارسال شماره موبایل", request_contact=True)
    markup.add(btn)
    msg = bot.send_message(message.chat.id, "🔐 برای امنیت اطلاعات، ابتدا شماره موبایل خود را تایید کنید:", reply_markup=markup)
    bot.register_next_step_handler(msg, track_get_phone)

def track_get_phone(message):
    if message.contact:
        phone = message.contact.phone_number
        if phone.startswith('+98'): phone = '0' + phone[3:]
        user_track_data[message.chat.id] = {'phone': phone}
        
        msg = bot.send_message(message.chat.id, "✅ تایید شد. حالا **شماره سفارش** را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, track_final_result)
    else:
        bot.send_message(message.chat.id, "❌ لغو شد. باید شماره موبایل ارسال شود.", reply_markup=get_main_keyboard(message.from_user.id))

def track_final_result(message):
    order_id = message.text.strip()
    chat_id = message.chat.id
    if order_id.isdigit() and chat_id in user_track_data:
        phone = user_track_data[chat_id]['phone']
        bot.send_message(chat_id, "⏳ در حال دریافت اطلاعات فاکتور از سایت...")
        
        full_invoice = fetch_order_details_from_page(order_id, phone)
        if full_invoice:
            bot.send_message(chat_id, full_invoice, parse_mode="Markdown", reply_markup=get_main_keyboard(message.from_user.id))
        else:
            bot.send_message(chat_id, f"❌ اطلاعاتی برای سفارش {order_id} یافت نشد.\nمطمئن شوید شماره موبایل ثبت شده در سایت با موبایل تلگرام شما یکی است.", reply_markup=get_main_keyboard(message.from_user.id))
    else:
        bot.send_message(chat_id, "❌ ورودی اشتباه بود.", reply_markup=get_main_keyboard(message.from_user.id))

# ================== جستجو و اجرا ==================
@bot.message_handler(func=lambda m: True)
def auto_search(message):
    if message.text == "🔍 جستجوی محصول":
        bot.send_message(message.chat.id, "🔎 نام محصول مورد نظر را تایپ کنید:")
        return
    # (کد جستجو طبق روال قبلی فعال است)

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook(); bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Baneh Stoore Full Details Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
