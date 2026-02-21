import telebot
from telebot import types
import os
import re
import sqlite3
import time
import requests # برای دریافت قیمت‌ها
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# (بخش‌های دیتابیس و استخراج هوشمند دقیقاً مطابق قبل حفظ شده‌اند)
# [بخش‌های تکراری برای کوتاه شدن پاسخ در اینجا نوشته نشده اما در فایل نهایی شما وجود دارد]

# ================== تابع دریافت قیمت لحظه‌ای ==================
def get_live_prices():
    try:
        # استفاده از یک منبع تست (در نسخه نهایی می‌توانید توکن navasan تهیه کنید)
        url = "https://api.tala.ir/v1/live" # نمونه فرضی
        # برای سادگی و سرعت، از یک وب‌سرویس عمومی استفاده می‌کنیم
        res = requests.get("https://brsapi.ir/FreeTalaGold/api/get_stats").json()
        
        gold = res['gold'][0]['price'] # طلای ۱۸ عیار
        usd = res['currency'][0]['price'] # دلار
        eur = res['currency'][1]['price'] # یورو
        aed = res['currency'][2]['price'] # درهم
        
        text = "💰 **قیمت لحظه‌ای بازار (تومان):**\n"
        text += "━━━━━━━━━━━━━━━\n"
        text += f"🇺🇸 دلار: {usd:,}\n"
        text += f"🇪🇺 یورو: {eur:,}\n"
        text += f"🇦🇪 درهم: {aed:,}\n"
        text += f"⚜️ طلای ۱۸ عیار: {gold:,}\n"
        text += "━━━━━━━━━━━━━━━\n"
        text += f"⏰ بروزرسانی: {res['date']}\n"
        return text
    except:
        return "⚠️ در حال حاضر سرویس قیمت‌دهی در دسترس نیست. لطفاً دقایقی دیگر امتحان کنید."

# ================== اصلاح کیبورد اصلی ==================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "💰 قیمت ارز و طلا") # دکمه جدید
    markup.row("📞 پشتیبانی و تماس")
    if user_id == ADMIN_ID:
        markup.row("🛠 پنل مدیریت")
    return markup

# ================== هندلرهای جدید ==================
@bot.message_handler(func=lambda m: m.text == "💰 قیمت ارز و طلا")
def price_handler(message):
    bot.send_message(message.chat.id, "⏳ در حال دریافت قیمت‌های لحظه‌ای...")
    price_text = get_live_prices()
    bot.send_message(message.chat.id, price_text, parse_mode="Markdown")

# [بقیه کدهای قبلی (ثبت فاکتور، پیگیری سفارش، پنل مدیریت) بدون تغییر باقی می‌مانند]
