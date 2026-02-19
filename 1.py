import telebot
from telebot import types
import os
import json
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6690559792 
CHANNEL_ID = "@banehstoore"
WHATSAPP = "09180514202"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# فایل ذخیره آیدی کاربران ثبت‌نام شده
USERS_FILE = "registered_users.json"

# بارگذاری لیست کاربران از فایل
if os.path.exists(USERS_FILE):
    try:
        with open(USERS_FILE, "r") as f:
            registered_users = json.load(f)
    except:
        registered_users = []
else:
    registered_users = []

def save_user(user_id):
    """ذخیره آیدی کاربر جدید در لیست و فایل"""
    if user_id not in registered_users:
        registered_users.append(user_id)
        with open(USERS_FILE, "w") as f:
            json.dump(registered_users, f)

# ================== توابع کمکی منو ==================
def main_menu():
    """ایجاد منوی اصلی ربات"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 محصولات", "📞 پشتیبانی")
    return markup

# ================== بخش مدیریت پیام‌ها ==================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # بررسی اینکه آیا کاربر قبلاً ثبت‌نام کرده است یا خیر
    if user_id in registered_users:
        bot.send_message(
            message.chat.id, 
            "👋 خوش آمدید مجدد به بانه استور!\nمی‌توانید از منوی زیر استفاده کنید:", 
            reply_markup=main_menu()
        )
    else:
        # شروع پروسه ثبت‌نام برای بار اول
        msg = bot.send_message(
            message.chat.id, 
            "👋 به ربات بانه استور خوش آمدید!\n\nلطفاً جهت ثبت‌نام و دسترسی به منو، **نام و نام خانوادگی** خود را وارد کنید:"
        )
        bot.register_next_step_handler(msg, get_name)

def get_name(message):
    user_full_name = message.text
    if not user_full_name or len(user_full_name) < 3:
        msg = bot.send_message(message.chat.id, "❌ نام معتبر نیست. لطفاً مجدداً نام خود را بفرستید:")
        bot.register_next_step_handler(msg, get_name)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 اشتراک‌گذاری شماره موبایل", request_contact=True))
    
    msg = bot.send_message(
        message.chat.id, 
        f"ممنون {user_full_name} عزیز. حالا برای تکمیل ثبت‌نام، دکمه **اشتراک‌گذاری شماره** را لمس کنید:", 
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, get_phone, user_full_name)

def get_phone(message, user_full_name):
    user_id = message.from_user.id
    
    # دریافت شماره (چه از طریق دکمه چه دستی)
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    # ذخیره کاربر در دیتابیس (فایل)
    save_user(user_id)
    
    # اطلاع‌رسانی به ادمین
    bot.send_message(
        ADMIN_ID, 
        f"👤 **مشتری جدید در ربات!**\n\n📝 نام: {user_full_name}\n📞 شماره: {phone}\n🆔 آیدی: `{user_id}`",
        parse_mode="Markdown"
    )
    
    bot.send_message(
        message.chat.id, 
        "✅ ثبت‌نام شما با موفقیت انجام شد و اطلاعات شما ذخیره گردید.", 
        reply_markup=main_menu()
    )

# ================== دکمه‌های منوی اصلی ==================

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📲 واتساپ", url=f"https://wa.me/98{WHATSAPP[1:]}"))
    bot.send_message(message.chat.id, "📞 جهت ارتباط با واحد فروش و پشتیبانی، روی دکمه زیر بزنید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def products(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("☕ اسپرسوساز", url="https://banehstoore.ir/product-category/espresso-maker"),
        types.InlineKeyboardButton("🍟 سرخ‌کن", url="https://banehstoore.ir/product-category/air-fryer"),
        types.InlineKeyboardButton("🛍 مشاهده همه محصولات", url="https://banehstoore.ir")
    )
    bot.send_message(message.chat.id, "🛒 لیست دسته‌بندی محصولات بانه استور:", reply_markup=markup)

# ================== وب‌هوک و تنظیمات فلکسا ==================

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://telegram-bot-5-qw7c.onrender.com/' + BOT_TOKEN)
    return "<h1>Bot is Running Successfully!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
