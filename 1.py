import os
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = '8583608724:AAEeqgf5ki7fp_OuA07HZD2J0pVdWFONeSY'
CHANNEL_ID = '@banehstoore'
SITE_URL = 'https://banehstoore.ir'

async def check_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Membership error: {e}")
        return False

def search_products(query):
    """جستجو در سایت بانه استور و استخراج نام و لینک محصولات"""
    search_url = f"{SITE_URL}/?s={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # پیدا کردن محصولات (با توجه به ساختار ووکامرس)
        products = []
        # این بخش نام و لینک محصول را از تگ‌های سایت شما استخراج می‌کند
        items = soup.select('.product-title a') or soup.select('h2.woocommerce-loop-product__title a') or soup.select('.entry-title a')
        
        for item in items[:8]: # نمایش حداکثر 8 نتیجه اول
            name = item.get_text().strip()
            link = item.get('href')
            if name and link:
                products.append({'name': name, 'link': link})
        return products
    except Exception as e:
        logging.error(f"Search error: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_member = await check_membership(context, user.id)
    
    if is_member:
        await update.message.reply_text(
            f"🛍 به بخش جستجوی محصولات **بانه استور** خوش آمدید!\n\n"
            "لطفاً نام محصول مورد نظر خود را تایپ و ارسال کنید (مثلاً: تلویزیون سامسونگ)"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/banehstoore")],
            [InlineKeyboardButton("✅ تایید عضویت", callback_data='verify_join')]
        ]
        await update.message.reply_text(
            "لطفاً ابتدا در کانال عضو شوید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت متن‌های ارسالی کاربر برای جستجو"""
    user_id = update.effective_user.id
    if not await check_membership(context, user_id):
        await start(update, context)
        return

    query = update.message.text
    if len(query) < 2:
        await update.message.reply_text("لطفاً عبارت طولانی‌تری برای جستجو وارد کنید.")
        return

    wait_msg = await update.message.reply_text("🔍 در حال جستجو در سایت بانه استور...")
    
    results = search_products(query)
    
    if results:
        keyboard = []
        for res in results:
            keyboard.append([InlineKeyboardButton(res['name'], url=res['link'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await wait_msg.edit_text(
            f"✅ نتایج یافت شده برای «{query}»:\nبرای مشاهده و خرید روی محصول کلیک کنید:",
            reply_markup=reply_markup
        )
    else:
        await wait_msg.edit_text("😔 متاسفانه محصولی با این نام در سایت پیدا نشد.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'verify_join' and await check_membership(context, query.from_user.id):
        await query.edit_message_text("عضویت تایید شد! حالا نام محصول را بفرستید.")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    # هندلر برای دریافت متن جستجو از کاربر
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("--- ربات بانه استور فعال شد ---")
    application.run_polling()

if __name__ == '__main__':
    main()
