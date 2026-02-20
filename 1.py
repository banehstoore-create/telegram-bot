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

# هدر پیشرفته برای شبیه‌سازی دقیق مرورگر
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive"
}

# ================== استخراج عمیق اطلاعات فاکتور ==================
def fetch_order_full_details(order_id):
    try:
        # آدرس مستقیم رهگیری در میکسین
        url = f"https://banehstoore.ir/order-tracking/?order_id={order_id}"
        session = requests.Session()
        r = session.get(url, headers=HEADERS, timeout=25)
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # ۱. حذف منوها و فوتر برای جلوگیری از استخراج کلمات اشتباه
        for element in soup(['header', 'footer', 'nav', 'script', 'style']):
            element.decompose()

        # ۲. استخراج تمام متن‌های باقی‌مانده در بدنه اصلی سایت
        content_text = soup.get_text(" ", strip=True)

        # ۳. استخراج اقلام سفارش (جستجوی الگوهای متنی محصول در میکسین)
        # معمولا در میکسین نام محصولات در جداول یا لیست‌های تگ <li> یا <td> هستند
        potential_items = []
        for tag in soup.find_all(['td', 'h3', 'div', 'span']):
            text = tag.get_text(strip=True)
            # فیلتر کردن متون خیلی کوتاه یا خیلی بلند یا منوها
            if 15 < len(text) < 100 and not any(x in text for x in ["تماس", "درباره", "قوانین", "حساب"]):
                potential_items.append(f"📦 {text}")

        # ۴. تحلیل وضعیت سفارش
        status = "ثبت شده (در حال بررسی)"
        if "ارسال شده" in content_text: status = "🚚 ارسال شده (تحویل پست)"
        elif "پردازش" in content_text: status = "⏳ در حال آماده‌سازی"
        elif "تکمیل" in content_text: status = "✅ تکمیل شده"
        elif "لغو" in content_text: status = "❌ لغو شده"

        # ۵. استخراج مبلغ با دقت بالا
        price = "نامشخص (تماس بگیرید)"
        # جستجوی اعداد همراه با جداکننده هزارگان و کلمه تومان
        price_search = re.findall(r'([\d,/]+)\s*(?:تومان|ریال)', content_text)
        if price_search:
            price = f"{price_search[-1]} تومان" # معمولا آخرین مبلغ در فاکتور مبلغ کل است

        # ۶. ساختار نهایی پیام
        res = f"📑 **فاکتور دیجیتال بانه استور**\n"
        res += f"🆔 شماره سفارش: `{order_id}`\n"
        res += "--------------------------------------\n"
        
        items = list(dict.fromkeys(potential_items)) # حذف تکراری‌ها
        if items:
            res += "🛒 **لیست کالاها:**\n" + "\n".join(items[:8]) + "\n"
        else:
            res += "🛒 **لیست کالاها:** جهت مشاهده ریز اقلام به سایت مراجعه کنید.\n"

        res += "--------------------------------------\n"
        res += f"🚩 **وضعیت فاکتور:** {status}\n"
        res += f"💰 **مبلغ قابل پرداخت:** {price}\n"
        res += "--------------------------------------\n"
        res += "👤 مشتری گرامی، از اعتماد شما سپاسگزاریم.\n"
        res += f"🌐 [لینک مستقیم فاکتور](https://banehstoore.ir/profile/order-details/{order_id}/)"

        return res

    except Exception as e:
        return f"⚠️ خطای سیستمی در بازخوانی فاکتور {order_id}. لطفا با پشتیبانی تماس بگیرید."

# ================== هندلرهای تلگرام (بدون تغییر در دکمه‌ها) ==================

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_cmd(message):
    msg = bot.send_message(message.chat.id, "🔢 لطفاً شماره سفارش عددی خود را وارد کنید:")
    bot.register_next_step_handler(msg, process_order)

def process_order(message):
    order_id = message.text.strip()
    if order_id.isdigit():
        bot.send_message(message.chat.id, "🔍 در حال استخراج اطلاعات از دیتابیس سایت...")
        result = fetch_order_full_details(order_id)
        bot.send_message(message.chat.id, result, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ ورودی باید فقط عدد باشد.")

# بقیه دکمه‌های محصولات، پشتیبانی و غیره طبق تنظیمات قبلی شما...
# (کد قبلی دکمه‌ها را در اینجا قرار دهید)

if __name__ == "__main__":
    # اجرای Flask و Bot
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
