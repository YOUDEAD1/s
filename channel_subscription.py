from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ContextTypes, MessageHandler, filters
import asyncio
import logging
import json
import os
import datetime
import threading

# إنشاء متغير عام للتحكم في الوصول إلى قاعدة البيانات
channel_lock = threading.Lock()

logger = logging.getLogger(__name__)

class EnhancedChannelSubscription:
    def __init__(self):
        self.required_channel = None
        self.middleware_handler = None
        self.is_mandatory = False
        self.expiry_date = None
        self.settings_file = os.path.join(os.path.dirname(__file__), 'channel_settings.json')
        self.load_settings()

    def set_required_channel(self, channel, duration_days=None):
        """تعيين القناة المطلوبة للاشتراك الإجباري مع إمكانية تحديد المدة بالأيام"""
        if channel and not channel.startswith('@'):
            channel = f'@{channel}'
        self.required_channel = channel
        self.is_mandatory = bool(channel)

        # تعيين تاريخ انتهاء الاشتراك الإجباري إذا تم تحديد المدة
        if duration_days is not None and duration_days > 0:
            self.expiry_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days)).isoformat()
        else:
            # إذا كانت المدة صفر أو سالبة، يكون الاشتراك دائماً
            self.expiry_date = None

        logger.info(f"تم تعيين القناة المطلوبة للاشتراك الإجباري: {channel}, المدة: {duration_days} يوم")

        # حفظ الإعدادات
        self.save_settings()

        return True

    def get_required_channel(self):
        """الحصول على القناة المطلوبة للاشتراك الإجباري"""
        # التحقق من انتهاء صلاحية الاشتراك الإجباري
        if self.expiry_date:
            try:
                expiry = datetime.datetime.fromisoformat(self.expiry_date)
                if datetime.datetime.now() > expiry:
                    logger.info("انتهت صلاحية الاشتراك الإجباري")
                    self.required_channel = None
                    self.is_mandatory = False
                    self.expiry_date = None
                    self.save_settings()
            except Exception as e:
                logger.error(f"خطأ أثناء التحقق من تاريخ انتهاء الصلاحية: {str(e)}")

        return self.required_channel

    def is_mandatory_subscription(self):
        """التحقق مما إذا كان الاشتراك الإجباري مفعل"""
        # التحقق من انتهاء صلاحية الاشتراك الإجباري
        if self.expiry_date:
            try:
                expiry = datetime.datetime.fromisoformat(self.expiry_date)
                if datetime.datetime.now() > expiry:
                    logger.info("انتهت صلاحية الاشتراك الإجباري")
                    self.required_channel = None
                    self.is_mandatory = False
                    self.expiry_date = None
                    self.save_settings()
            except Exception as e:
                logger.error(f"خطأ أثناء التحقق من تاريخ انتهاء الصلاحية: {str(e)}")

        return self.is_mandatory and self.required_channel is not None

    def get_subscription_info(self):
        """الحصول على معلومات الاشتراك الإجباري"""
        info = {
            "channel": self.required_channel,
            "is_mandatory": self.is_mandatory,
            "expiry_date": self.expiry_date
        }

        # إضافة معلومات المدة المتبقية إذا كان هناك تاريخ انتهاء
        if self.expiry_date:
            try:
                expiry = datetime.datetime.fromisoformat(self.expiry_date)
                remaining = expiry - datetime.datetime.now()
                info["remaining_days"] = max(0, remaining.days)
                info["is_expired"] = datetime.datetime.now() > expiry
            except Exception as e:
                logger.error(f"خطأ أثناء حساب المدة المتبقية: {str(e)}")
                info["remaining_days"] = "غير معروف"
                info["is_expired"] = False
        else:
            info["remaining_days"] = "دائم"
            info["is_expired"] = False

        return info

    def save_settings(self):
        """حفظ إعدادات الاشتراك الإجباري في ملف"""
        settings = {
            "required_channel": self.required_channel,
            "is_mandatory": self.is_mandatory,
            "expiry_date": self.expiry_date
        }

        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            logger.info("تم حفظ إعدادات الاشتراك الإجباري بنجاح")
        except Exception as e:
            logger.error(f"خطأ أثناء حفظ إعدادات الاشتراك الإجباري: {str(e)}")

    def load_settings(self):
        """تحميل إعدادات الاشتراك الإجباري من ملف"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                self.required_channel = settings.get("required_channel")
                self.is_mandatory = settings.get("is_mandatory", False)
                self.expiry_date = settings.get("expiry_date")

                # التحقق من انتهاء صلاحية الاشتراك الإجباري
                if self.expiry_date:
                    try:
                        expiry = datetime.datetime.fromisoformat(self.expiry_date)
                        if datetime.datetime.now() > expiry:
                            logger.info("انتهت صلاحية الاشتراك الإجباري")
                            self.required_channel = None
                            self.is_mandatory = False
                            self.expiry_date = None
                            self.save_settings()
                    except Exception as e:
                        logger.error(f"خطأ أثناء التحقق من تاريخ انتهاء الصلاحية: {str(e)}")

                logger.info(f"تم تحميل إعدادات الاشتراك الإجباري: القناة={self.required_channel}, إجباري={self.is_mandatory}, تاريخ الانتهاء={self.expiry_date}")
        except Exception as e:
            logger.error(f"خطأ أثناء تحميل إعدادات الاشتراك الإجباري: {str(e)}")

    async def check_user_subscription(self, user_id, bot):
        """التحقق من اشتراك المستخدم في القناة المطلوبة"""
        if not self.is_mandatory_subscription():
            return True

        try:
            with channel_lock:
                # التحقق من نوع bot وإنشاء كائن Bot إذا كان رقمًا أو نصًا
                if isinstance(bot, (int, str)):
                    # إذا كان bot عبارة عن رقم أو نص، قم بإنشاء كائن bot جديد
                    from telegram import Bot
                    temp_bot = Bot(token=str(bot))
                    chat_member = await temp_bot.get_chat_member(chat_id=self.required_channel, user_id=user_id)
                else:
                    chat_member = await bot.get_chat_member(chat_id=self.required_channel, user_id=user_id)
                    
                # التحقق من حالة العضوية
                status = chat_member.status
                # المستخدم مشترك إذا كان عضواً أو مشرفاً أو مالكاً
                is_subscribed = status in ['member', 'administrator', 'creator']
                return is_subscribed
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق من اشتراك المستخدم {user_id}: {str(e)}")
            # في حالة حدوث خطأ، نفترض أن المستخدم غير مشترك
            return False

    async def check_bot_is_admin(self, bot):
        """التحقق مما إذا كان البوت مشرفاً في القناة المطلوبة"""
        if not self.is_mandatory_subscription():
            return True, "لم يتم تعيين قناة للاشتراك الإجباري"

        try:
            # التحقق من نوع bot وإنشاء كائن Bot إذا كان رقمًا أو نصًا
            if isinstance(bot, (int, str)):
                # إذا كان bot عبارة عن رقم أو نص، قم بإنشاء كائن bot جديد
                from telegram import Bot
                temp_bot = Bot(token=str(bot))
                # الحصول على معرف البوت
                bot_info = await temp_bot.get_me()
                bot_id = bot_info.id
                # التحقق من صلاحيات البوت في القناة
                chat_member = await temp_bot.get_chat_member(chat_id=self.required_channel, user_id=bot_id)
            else:
                # الحصول على معرف البوت
                bot_info = await bot.get_me()
                bot_id = bot_info.id
                # التحقق من صلاحيات البوت في القناة
                chat_member = await bot.get_chat_member(chat_id=self.required_channel, user_id=bot_id)
            
            status = chat_member.status

            # التحقق مما إذا كان البوت مشرفاً
            if status == 'administrator':
                return True, f"البوت مشرف في القناة {self.required_channel}"
            else:
                return False, f"البوت ليس مشرفاً في القناة {self.required_channel}. الرجاء ترقية البوت إلى مشرف."
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق من صلاحيات البوت: {str(e)}")
            return False, f"حدث خطأ أثناء التحقق من صلاحيات البوت: {str(e)}"

    async def subscription_middleware(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """وسيط للتحقق من اشتراك المستخدم قبل معالجة الرسائل"""
        # تجاهل التحديثات التي ليست رسائل أو أوامر
        if not update.effective_message:
            return

        # تجاهل التحديثات من المحادثات الجماعية
        if update.effective_chat.type != "private":
            return

        # تجاهل التحقق إذا كان الاشتراك غير إجباري
        if not self.is_mandatory_subscription():
            return

        # الحصول على معرف المستخدم
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            return

        # التحقق من المشرف (المشرفون معفون من التحقق)
        try:
            from subscription_service import SubscriptionService
            subscription_service = SubscriptionService()
            db_user = subscription_service.get_user(user_id)
            is_admin = db_user and db_user.is_admin
            if is_admin:
                return
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق من حالة المشرف: {str(e)}")
            # في حالة حدوث خطأ، نفترض أن المستخدم ليس مشرفاً

        # التحقق من اشتراك المستخدم
        is_subscribed = await self.check_user_subscription(user_id, context.bot)
        
        # إذا كان المستخدم غير مشترك، منعه من استخدام البوت إلا لأمر /start
        if not is_subscribed:
            # السماح فقط بأمر /start
            if update.message and update.message.text and update.message.text.startswith('/start'):
                # السماح بأمر /start
                return
            
            # منع جميع الأوامر والرسائل الأخرى
            channel = self.get_required_channel()

            # إنشاء زر للاشتراك في القناة
            keyboard = [
                [InlineKeyboardButton("🔔 الاشتراك في القناة", url=f"https://t.me/{channel[1:]}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.effective_message.reply_text(
                f"⚠️ يجب عليك الاشتراك في {channel} للاستمرار.\n\n"
                "اضغط على الزر أدناه للاشتراك في القناة. سيتم التحقق تلقائياً من اشتراكك.",
                reply_markup=reply_markup
            )

            # منع معالجة الرسالة
            raise asyncio.CancelledError("تم إلغاء معالجة الرسالة بسبب عدم الاشتراك في القناة")

# إنشاء كائن واحد للاستخدام في جميع أنحاء التطبيق
subscription_manager = EnhancedChannelSubscription()

# إضافة متغيرات متوافقة مع الاسم القديم للتوافق مع الكود القديم
channel_subscription = subscription_manager
# تعريف enhanced_channel_subscription للتوافق مع bot.py
enhanced_channel_subscription = subscription_manager

# تعريف وسيط auto_channel_subscription_required كدالة بدلاً من None
def auto_channel_subscription_required(func):
    """وسيط للتحقق من اشتراك المستخدم في القناة المطلوبة"""
    from functools import wraps
    from telegram import Update
    from telegram.ext import CallbackContext

    @wraps(func)
    async def wrapped(self, update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id

        # التحقق من المشرف (المشرفون معفون من التحقق)
        try:
            from subscription_service import SubscriptionService
            subscription_service = SubscriptionService()
            db_user = subscription_service.get_user(user_id)
            is_admin = db_user and db_user.is_admin

            if is_admin:
                return await func(self, update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق من حالة المشرف: {str(e)}")
            # في حالة حدوث خطأ، نفترض أن المستخدم ليس مشرفاً

        # التحقق من اشتراك المستخدم
        if subscription_manager.is_mandatory_subscription():
            is_subscribed = await subscription_manager.check_user_subscription(user_id, context.bot)
            if not is_subscribed:
                # السماح فقط بأمر /start
                if update.message and update.message.text and update.message.text.startswith('/start'):
                    # السماح بأمر /start
                    return await func(self, update, context, *args, **kwargs)
                
                # منع جميع الأوامر والرسائل الأخرى
                channel = subscription_manager.get_required_channel()

                # إنشاء زر للاشتراك في القناة
                keyboard = [
                    [InlineKeyboardButton("🔔 الاشتراك في القناة", url=f"https://t.me/{channel[1:]}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.effective_message.reply_text(
                    f"⚠️ يجب عليك الاشتراك في {channel} للاستمرار.\n\n"
                    "اضغط على الزر أدناه للاشتراك في القناة. سيتم التحقق تلقائياً من اشتراكك.",
                    reply_markup=reply_markup
                )

                return None

        return await func(self, update, context, *args, **kwargs)

    return wrapped

def setup_enhanced_subscription(application):
    """إعداد وسيط التحقق من الاشتراك"""
    # إضافة وسيط للتحقق من الاشتراك لجميع الرسائل
    application.add_handler(
        MessageHandler(filters.ALL, subscription_manager.subscription_middleware),
        group=-1  # أولوية عالية لضمان تنفيذ الوسيط قبل معالجة الرسائل
    )

    return subscription_manager
