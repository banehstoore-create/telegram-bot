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
ADMIN_ID = 6690559792

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ================== تابع استخراج کامل جزئیات فاکتور ==================
def get_full_invoice_details(order_id):
    try:
        # آدرس مستقیم فاکتور در سایت شما
        url = f"https://banehstoore.ir/profile/order-details/{order_id}/"
        
        # استفاده از API Key برای احراز هویت در صورت پشتیبانی سایت، 
        # یا شبیه‌سازی دسترسی مدیریت برای خواندن محتوا
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return "❌ متأسفانه امکان دسترسی مستقیم به این فاکتور وجود ندارد."

        soup = BeautifulSoup(response.text, "html.parser")
        
        # --- استخراج اطلاعات مشتری ---
        customer_info = ""
        # در میکسین معمولا اطلاعات در کلاس order-details-customer یا مشابه قرار دارد
        customer_div = soup.find(class_=lambda x: x and 'customer' in x)
        if customer_div:
            customer_info = customer_div.get_text(strip=True, separator=" ")

        # --- استخراج لیست محصولات و قیمت‌ها ---
        items_text = ""
        # یافتن جدول محصولات
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:] # نادیده گرفتن سرتیتر جدول
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    p_name = cols[0].get_text(strip=True)
                    p_price = cols[-1].get_text(strip=True)
                    items_text += f"🛍 **{p_name}**\n💰 قیمت: {p_price}\n\n"
        
        # --- استخراج وضعیت و جمع کل ---
        summary_text = ""
        summary_div = soup.find(class_=lambda x: x and 'summary' in x)
        if summary_div:
            summary_text = summary_div.get_text(strip=True, separator="\n")

        # --- ساخت پیام نهایی ---
        report = f"📑 **فاکتور کامل سفارش شماره {order_id}**\n"
        report += "━━━━━━━━━━━━━━━\n"
        if customer_info:
            report += f"👤 **مشخصات خریدار:**\n{customer_info}\n\n"
        
        report += "🛒 **لیست اقلام سفارش:**\n"
        report += items_text if items_text else "اطلاعات محصولات یافت نشد.\n"
        
        report += "━━━━━━━━━━━━━━━\n"
        if summary_text:
            report += f"📊 **خلاصه وضعیت و پرداخت:**\n{summary_text}\n"
        else:
            # تلاش ثانویه برای یافتن قیمت کل در صورت نبود جدول خلاصه
            total_price = soup.find(string=lambda x: x and 'تومان' in x)
            if total_price:
                report += f"💰 **مبلغ کل:** {total_price.strip()}\n"

        report += "\n✅ **بانه استور - خرید بدون واسطه**"
        return report

    except Exception as e:
        return f"⚠️ خطا در پردازش اطلاعات. لطفا از لینک زیر استفاده کنید:\n{url}"

# ================== هندلر پیگیری سفارش ==================
@bot.message_handler(func=lambda m: m.text == "📦 پیگیری سفارش")
def track_start(message):
    msg = bot.send_message(message.chat.id, "🔢 لطفاً شماره سفارش خود را وارد کنید تا فاکتور کامل نمایش داده شود:")
    bot.register_next_step_handler(msg, process_full_invoice)

def process_full_invoice(message):
    order_id = message.text.strip()
    if order_id.isdigit():
        bot.send_message(message.chat.id, "⏳ در حال استخراج تمام جزئیات فاکتور از سایت... لطفاً شکیبا باشید.")
        
        invoice_content = get_full_invoice_details(order_id)
        bot.send_message(message.chat.id, invoice_content, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ خطا! شماره سفارش باید فقط عدد باشد.")

# ================== سایر بخش‌ها (بدون تغییر) ==================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 محصولات", "🔍 جستجوی محصول")
    markup.row("📦 پیگیری سفارش", "📞 پشتیبانی و تماس")
    bot.send_message(message.chat.id, "👋 خوش آمدید. گزینه مورد نظر را انتخاب کنید:", reply_markup=markup)

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "<h1>Full Invoice System Active</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
