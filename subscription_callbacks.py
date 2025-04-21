import logging
from telegram.ext import Application, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# إعداد التسجيل
logger = logging.getLogger(__name__)

async def subscription_check_callback(update: Update, context: CallbackContext):
    """Handle callback when user clicks 'Check Subscription' button"""
    query = update.callback_query
    user_id = update.effective_user.id

    # Answer callback query to stop loading animation
    await query.answer()

    # Get the channel subscription instance
    from channel_subscription import subscription_manager

    # Check if user is subscribed to the channel
    required_channel = subscription_manager.get_required_channel()
    is_subscribed = await subscription_manager.check_user_subscription(user_id, context.bot)

    if is_subscribed:
        # User is subscribed, show success message
        await query.edit_message_text(
            text=f"✅ تم التحقق من اشتراكك في القناة {required_channel} بنجاح!\n\n"
                 f"يمكنك الآن استخدام جميع ميزات البوت."
        )
    else:
        # User is still not subscribed, show error message
        keyboard = [
            [InlineKeyboardButton("✅ اشترك في القناة", url=f"https://t.me/{required_channel[1:]}")],
            [InlineKeyboardButton("🔄 تحقق مرة أخرى", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=f"❌ لم يتم العثور على اشتراكك في القناة {required_channel}.\n\n"
                 f"يرجى الاشتراك في القناة ثم الضغط على زر 'تحقق مرة أخرى'.",
            reply_markup=reply_markup
        )

def register_subscription_callbacks(application: Application):
    """Register callback handlers for subscription functionality"""
    # Register callback query handler for subscription check button
    application.add_handler(
        CallbackQueryHandler(subscription_check_callback, pattern='^check_subscription$')
    )

    logger.info("تم تسجيل معالجات استدعاء التحقق من الاشتراك")
