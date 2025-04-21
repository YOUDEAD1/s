import logging
import threading
from telegram import Bot

# إنشاء متغير عام للتحكم في الوصول إلى قاعدة البيانات
channel_lock = threading.Lock()

# تكوين التسجيل
logger = logging.getLogger(__name__)

async def check_user_subscription(bot, user_id, channel_id):
    """
    التحقق من اشتراك المستخدم في القناة
    
    Args:
        bot: كائن البوت أو توكن البوت
        user_id: معرف المستخدم
        channel_id: معرف القناة
        
    Returns:
        bool: True إذا كان المستخدم مشتركًا، False إذا لم يكن مشتركًا
    """
    try:
        with channel_lock:
            # التحقق من نوع bot وإنشاء كائن Bot إذا كان رقمًا أو نصًا
            if isinstance(bot, (int, str)):
                # إذا كان bot عبارة عن رقم أو نص، قم بإنشاء كائن bot جديد
                from telegram import Bot
                temp_bot = Bot(token=str(bot))
                chat_member = await temp_bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            else:
                chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                
            # التحقق من حالة العضوية
            status = chat_member.status
            is_member = status in ['member', 'administrator', 'creator']
            
            return is_member
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من اشتراك المستخدم {user_id} في القناة {channel_id}: {str(e)}")
        return False
