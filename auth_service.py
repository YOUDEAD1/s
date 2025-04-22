import logging
import os
import json
import asyncio
from telethon.sessions import StringSession
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
    PhoneNumberBannedError,
    PhoneNumberInvalidError
)

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.users_collection = {}
        self.sessions_file = os.path.join(os.path.dirname(__file__), 'user_sessions.json')
        self.load_sessions()

    def load_sessions(self):
        """تحميل جلسات المستخدمين من ملف"""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    self.users_collection = json.load(f)
                logger.info(f"تم تحميل {len(self.users_collection)} جلسة مستخدم")
            else:
                logger.info("ملف الجلسات غير موجود، سيتم إنشاء ملف جديد")
                self.users_collection = {}
                self.save_sessions()
        except Exception as e:
            logger.error(f"خطأ أثناء تحميل جلسات المستخدمين: {str(e)}")
            self.users_collection = {}

    def save_sessions(self):
        """حفظ جلسات المستخدمين في ملف"""
        try:
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self.users_collection, f, ensure_ascii=False, indent=4)
            logger.info("تم حفظ جلسات المستخدمين بنجاح")
        except Exception as e:
            logger.error(f"خطأ أثناء حفظ جلسات المستخدمين: {str(e)}")

    def get_user_session(self, user_id):
        """الحصول على جلسة المستخدم"""
        user_id_str = str(user_id)
        return self.users_collection.get(user_id_str)

    def set_user_session(self, user_id, session_string):
        """تعيين جلسة المستخدم"""
        user_id_str = str(user_id)
        self.users_collection[user_id_str] = session_string
        self.save_sessions()

    def clear_user_session(self, user_id):
        """حذف جلسة المستخدم"""
        user_id_str = str(user_id)
        if user_id_str in self.users_collection:
            del self.users_collection[user_id_str]
            self.save_sessions()
            return True
        return False

    async def check_session_validity(self, session_string, proxy=None):
        """التحقق من صلاحية جلسة المستخدم"""
        client = None
        try:
            # إنشاء عميل Telethon باستخدام جلسة المستخدم
            client = TelegramClient(
                StringSession(session_string),
                api_id=1,  # سيتم تجاهل هذه القيم لأننا نستخدم جلسة موجودة
                api_hash="1"
            )

            # إعداد البروكسي إذا تم توفيره
            if proxy:
                proxy_parts = proxy.split(':')
                proxy_type = proxy_parts[0]
                proxy_host = proxy_parts[1]
                proxy_port = int(proxy_parts[2])
                proxy_username = proxy_parts[3] if len(proxy_parts) > 3 else None
                proxy_password = proxy_parts[4] if len(proxy_parts) > 4 else None

                if proxy_type in ['socks4', 'socks5', 'http']:
                    await client.start(
                        proxy=(proxy_type, proxy_host, proxy_port, proxy_username, proxy_password)
                    )
                else:
                    await client.start()
            else:
                await client.start()

            # التحقق من الاتصال
            if await client.is_user_authorized():
                # الحصول على معلومات المستخدم
                me = await client.get_me()
                await client.disconnect()
                return True, me
            else:
                await client.disconnect()
                return False, None
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق من صلاحية الجلسة: {str(e)}")
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
            return False, None

    async def login_with_session_string(self, user_id, session_string, proxy=None):
        """تسجيل الدخول باستخدام جلسة المستخدم"""
        try:
            # التحقق من صلاحية الجلسة
            is_valid, me = await self.check_session_validity(session_string, proxy)
            if is_valid and me:
                # حفظ الجلسة
                self.set_user_session(user_id, session_string)
                return True, f"تم تسجيل الدخول بنجاح كـ {me.first_name}"
            else:
                return False, "فشل تسجيل الدخول: الجلسة غير صالحة"
        except Exception as e:
            logger.error(f"خطأ أثناء تسجيل الدخول باستخدام جلسة المستخدم: {str(e)}")
            return False, f"فشل تسجيل الدخول: {str(e)}"

    async def login_with_api_credentials(self, user_id, api_id, api_hash, phone_number, code=None, password=None, phone_code_hash=None, proxy=None):
        """تسجيل الدخول باستخدام بيانات API"""
        client = None
        try:
            # إنشاء عميل Telethon
            client = TelegramClient(
                StringSession(),
                api_id=api_id,
                api_hash=api_hash
            )

            # إعداد البروكسي إذا تم توفيره
            if proxy:
                proxy_parts = proxy.split(':')
                proxy_type = proxy_parts[0]
                proxy_host = proxy_parts[1]
                proxy_port = int(proxy_parts[2])
                proxy_username = proxy_parts[3] if len(proxy_parts) > 3 else None
                proxy_password = proxy_parts[4] if len(proxy_parts) > 4 else None

                if proxy_type in ['socks4', 'socks5', 'http']:
                    await client.connect(
                        proxy=(proxy_type, proxy_host, proxy_port, proxy_username, proxy_password)
                    )
                else:
                    await client.connect()
            else:
                await client.connect()

            # التحقق مما إذا كان المستخدم مسجل الدخول بالفعل
            if await client.is_user_authorized():
                # الحصول على معلومات المستخدم
                me = await client.get_me()
                session_string = client.session.save()
                await client.disconnect()
                
                # حفظ الجلسة
                self.set_user_session(user_id, session_string)
                
                return True, f"تم تسجيل الدخول بنجاح كـ {me.first_name}", session_string, None
            
            # إذا لم يتم توفير رمز التحقق، أرسل رمز تحقق
            if not code:
                try:
                    result = await client.send_code_request(phone_number)
                    phone_code_hash = result.phone_code_hash
                    await client.disconnect()
                    return False, "تم إرسال رمز التحقق إلى هاتفك. يرجى إدخال الرمز بالصيغة التالية: 1 2 3 4 5", None, phone_code_hash
                except FloodWaitError as e:
                    await client.disconnect()
                    return False, f"يرجى الانتظار {e.seconds} ثانية قبل المحاولة مرة أخرى", None, None
                except PhoneNumberBannedError:
                    await client.disconnect()
                    return False, "تم حظر رقم الهاتف من قبل Telegram", None, None
                except PhoneNumberInvalidError:
                    await client.disconnect()
                    return False, "رقم الهاتف غير صالح", None, None
                except Exception as e:
                    await client.disconnect()
                    return False, f"حدث خطأ: {str(e)}", None, None
            
            # إذا تم توفير رمز التحقق، حاول تسجيل الدخول
            try:
                if password:
                    # تسجيل الدخول باستخدام كلمة المرور (للتحقق بخطوتين)
                    await client.sign_in(phone=phone_number, password=password)
                else:
                    # تسجيل الدخول باستخدام رمز التحقق
                    await client.sign_in(phone=phone_number, code=code, phone_code_hash=phone_code_hash)
                
                # الحصول على معلومات المستخدم
                me = await client.get_me()
                session_string = client.session.save()
                await client.disconnect()
                
                # حفظ الجلسة
                self.set_user_session(user_id, session_string)
                
                return True, f"تم تسجيل الدخول بنجاح كـ {me.first_name}", session_string, None
            except SessionPasswordNeededError:
                await client.disconnect()
                return False, "هذا الحساب محمي بكلمة مرور. يرجى إدخال كلمة المرور.", None, phone_code_hash
            except PhoneCodeInvalidError:
                await client.disconnect()
                return False, "رمز التحقق غير صحيح. يرجى إدخال الرمز مرة أخرى بالصيغة التالية: 1 2 3 4 5", None, phone_code_hash
            except PhoneCodeExpiredError:
                # إذا انتهت صلاحية الرمز، أرسل رمز جديد
                try:
                    result = await client.send_code_request(phone_number)
                    new_phone_code_hash = result.phone_code_hash
                    await client.disconnect()
                    return False, "انتهت صلاحية رمز التحقق. تم إرسال رمز جديد إلى هاتفك. يرجى إدخال الرمز بالصيغة التالية: 1 2 3 4 5", None, new_phone_code_hash
                except Exception as e:
                    await client.disconnect()
                    return False, f"حدث خطأ أثناء إرسال رمز جديد: {str(e)}", None, None
            except FloodWaitError as e:
                await client.disconnect()
                return False, f"يرجى الانتظار {e.seconds} ثانية قبل المحاولة مرة أخرى", None, None
            except Exception as e:
                await client.disconnect()
                return False, f"حدث خطأ: {str(e)}", None, phone_code_hash
        except Exception as e:
            logger.error(f"خطأ أثناء تسجيل الدخول باستخدام بيانات API: {str(e)}")
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
            return False, f"فشل تسجيل الدخول: {str(e)}", None, None
