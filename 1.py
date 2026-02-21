import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# تنظیمات لاگ برای مشاهده خطاها در پنل Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# توکن و اطلاعات کانال
# اگر در Render متغیر محیطی ست کردید، از خط پایین استفاده کنید:
# TOKEN = os.getenv('BOT_TOKEN') 
TOKEN = '8583608724:AAEeqgf5ki7fp_OuA07HZD2J0pVdWFONeSY'
CHANNEL_ID = '@banehstoore'

async def check_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """بررسی وضعیت عضویت کاربر در کانال"""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        allowed_statuses = ['member', 'administrator', 'creator']
        return member.status in allowed_statuses
    except Exception as e:
        logging.error(f"Membership check error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فرمان شروع ربات"""
    user = update.effective_user
    is_member = await check_membership(context, user.id)
    
    if is_member:
        await update.message.reply_text(
            f"🎉 خوش آمدید {user.first_name} عزیز!\n\n"
            f"عضویت شما در کانال {CHANNEL_ID} تایید شده است.\n"
            "به زودی منوی محصولات و دسته‌بندی‌های فروشگاه بانه استور در اینجا نمایش داده می‌شود."
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/banehstoore")],
            [InlineKeyboardButton("✅ تایید عضویت", callback_data='verify_join')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"سلام {user.first_name}! 😊\n"
            f"برای استفاده از خدمات ربات بانه استور، ابتدا باید در کانال ما عضو شوید:",
            reply_markup=reply_markup
        )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه تایید عضویت"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer() # برای از بین بردن حالت در حال بارگذاری دکمه

    if query.data == 'verify_join':
        is_member = await check_membership(context, user_id)
        if is_member:
            await query.edit_message_text(
                "✅ تایید شد! حالا می‌توانید از تمامی امکانات فروشگاه استفاده کنید.\n"
                "برای مشاهده منو، دوباره دستور /start را بزنید."
            )
        else:
            await query.answer("❌ شما هنوز عضو کانال نشده‌اید!", show_alert=True)

def main():
    """اجرای ربات"""
    # ساخت اپلیکیشن
    application = Application.builder().token(TOKEN).build()

    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))

    # شروع به کار ربات
    print("--- Robot is Online (Baneh Store) ---")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
