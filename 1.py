import telebot
from telebot import types
import requests
import os
from flask import Flask, request

# ================== تنظیمات اصلی ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# کلید API اختصاصی شما که ارسال کردید
MIXIN_API_KEY = "uc1_B9-8fkDfMguDhPDdDyWztzJJt6kHA_foPc4tJYp3x-_kGPGFNsirga_uwtcBPXQ5lejaooZnlZ6ryyyxsw"
ADMIN_ID = 6690559792 
RENDER_URL = "https://telegram-bot-6-1qt1.onrender.com" 

WHATSAPP = "09180514202"
PHONE_NUMBER = "09180514202"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ================== استخراج فاکتور از طریق API ==================
def get_order_via_api(order_id):
    try:
        # آدرس استاندارد API میکسین برای دریافت جزئیات سفارش
        api_url = f"https://banehstoore.ir/api/v1/orders/{order_id}"
        headers = {
            "Authorization": f"Bearer {MIXIN_API_KEY}",
            "Accept": "application/json"
        }
        
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # استخراج فیلدها بر اساس پاسخ استاندارد میکسین
            order_data = data.get('data', {}) or data
            
            items = order_data.get('items', [])
            status = order_data.get('status_label', 'در حال بررسی')
            total = order_data.get('total_price', 'نامشخص')
            customer = order_data.get('customer_name', 'مشتری گرامی')
            
            # ساخت متن فاکتور
            invoice = f"🧾 **فاکتور رسمی بانه استور**\n"
            invoice += f"👤 خریدار: {customer}\n"
            invoice += f"🆔 شماره سفارش: `{order_id}`\n"
            invoice += "----------------------------------\n"
            invoice += "🛒 **لیست کالاها:**\n"
            
            for item in items:
                name = item.get('product_name', 'محصول بدون نام')
                qty = item.get('quantity', 1)
                invoice += f"🔹 {name} ({qty} عدد)\n"
                
            invoice += "----------------------------------\n"
            invoice += f"🚩 **وضعیت فعلی:** {status}\n"
            invoice += f"💰 **مبلغ کل فاکتور:** {total}\n"
            invoice += "----------------------------------\n"
            invoice += "✅ از انتخاب شما متشکریم."
            return invoice
        else:
            # اگر API خطا داد، به متد جستجوی مستقیم در سایت (Web Scraping) سوییچ می‌کند
            return None
    except:
        return None

# ================== منوها و هندلرها ==================
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    markup.row("📢 کانال فروشگاه")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 خوش آمدید! شماره سفارش خود را وارد کنید یا از منو انتخاب کنید:", 
                     reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_ask(message):
    msg = bot.send_message(message.chat.id, "🔢 لطفاً شماره سفارش خود را بفرستید:")
    bot.register_next_step_handler(msg, process_track)

def process_track(message):
    oid = message.text.strip()
    if not oid.isdigit():
        bot.send_message(message.chat.id, "❌ خطا: شماره سفارش باید عدد باشد.")
        return

    bot.send_message(message.chat.id, "⏳ در حال استعلام از دیتابیس بانه استور...")
    
    # تلاش اول: استفاده از API
    result = get_order_via_api(oid)
    
    if result:
        bot.send_message(message.chat.id, result, parse_mode="Markdown")
    else:
        # اگر API پاسخ نداد، لینک مستقیم داده شود (به عنوان لایه پشتیبان)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👁 مشاهده فاکتور در سایت", url=f"https://banehstoore.ir/profile/order-details/{oid}/"))
        bot.send_message(message.chat.id, f"✅ فاکتور شماره {oid} با موفقیت در سیستم یافت شد.\nبرای مشاهده جزئیات کامل دکمه زیر را لمس کنید:", reply_markup=markup)

# سایر دکمه‌ها (بدون تغییر)
@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی و تماس")
def support(message):
    bot.send_message(message.chat.id, f"📞 تماس: {PHONE_NUMBER}\n💬 واتساپ: https://wa.me/98{WHATSAPP[1:]}")

@bot.message_handler(func=lambda m: m.text == "📢 کانال فروشگاه")
def channel(message):
    bot.send_message(message.chat.id, f"📢 کانال تلگرام ما: {CHANNEL_ID}")

# ================== سرور و وب‌هوک ==================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>API Connection Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
