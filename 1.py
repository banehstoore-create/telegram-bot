import os
import logging
import requests
import threading
from flask import Flask
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# لاگ برای دیباگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# تنظیمات
TOKEN = '8583608724:AAEeqgf5ki7fp_OuA07HZD2J0pVdWFONeSY'
CHANNEL_ID = '@banehstoore'
SITE_URL = 'https://banehstoore.ir'

# --- بخش وب‌سرور برای جلوگیری از خطای Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running..."

def run_flask():
    # Render پورت را در متغیر PORT قرار می‌دهد، اگر نبود روی 10000 اجرا می‌شود
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- بخش منطق ربات ---

async def check_membership(context, user_id):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def search_products(query):
    search_url = f"{SITE_URL}/?s={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        items = soup.select('.product-title a') or soup.select('h2.woocommerce-loop-product__title a') or soup.select('.entry-title a')
        for item in items[:8]:
            products.append({'name': item.get_text().strip(), 'link': item.get('href')})
        return products
    except:
        return []

async def start(update, context):
    user = update.effective_user
    if await check_membership(context, user.id):
        await update.message.reply_text(f"🛍 سلام {user.first_name}! نام محصول مورد نظر را بفرست تا در سایت بانه استور جستجو کنم.")
    else:
        kb = [[InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/banehstoore")],
              [InlineKeyboardButton("✅ تایید عضویت", callback_data='verify')]]
        await update.message.reply_text("برای استفاده، ابتدا عضو شوید:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_message(update, context):
    if not await check_membership(context, update.effective_user.id):
        await start(update, context)
        return
    
    query = update.message.text
    wait = await update.message.reply_text("🔍 در حال جستجو...")
    results = search_products(query)
    
    if results:
        kb = [[InlineKeyboardButton(r['name'], url=r['link'])] for r in results]
        await wait.edit_text(f"✅ نتایج برای «{query}»:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await wait.edit_text("😔 محصولی یافت نشد.")

async def button(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == 'verify' and await check_membership(context, query.from_user.id):
        await query.edit_message_text("تایید شد! حالا نام محصول را بفرستید.")

def main():
    # ۱. اجرای وب‌سرور در یک ترد جداگانه
    threading.Thread(target=run_flask, daemon=True).start()

    # ۲. اجرای ربات
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("--- Bot & Server started ---")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
