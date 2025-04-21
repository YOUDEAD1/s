# توثيق إصلاح مشكلة انتهاء صلاحية رمز التحقق

## المشكلة

كان المستخدمون يواجهون خطأ عند محاولة تسجيل الدخول باستخدام رمز التحقق:

```
❌ حدث خطأ أثناء تسجيل الدخول: The confirmation code has expired (caused by SignInRequest)
```

هذه المشكلة تحدث لأن رموز التحقق التي يرسلها تيليجرام لها فترة صلاحية محدودة (عادة حوالي 5 دقائق)، وعندما ينتهي وقت الصلاحية، يظهر هذا الخطأ. الكود السابق لم يكن يتعامل بشكل فعال مع هذه المشكلة.

## الحل المنفذ

تم تنفيذ التعديلات التالية لحل المشكلة:

### 1. إضافة نظام لتتبع عدد محاولات إعادة إرسال الرمز

تم إضافة متغير `max_code_resend_attempts` في كلاس `AuthService` لتحديد الحد الأقصى لعدد محاولات إعادة إرسال الرمز (3 محاولات).

```python
def __init__(self):
    self.db = Database()
    self.users_collection = self.db.get_collection('users')
    self.logger = logging.getLogger(__name__)
    # تعريف الحد الأقصى لعدد محاولات إعادة إرسال الرمز
    self.max_code_resend_attempts = 3
```

### 2. تخزين عدد محاولات إعادة الإرسال في قاعدة البيانات

تم إضافة حقل `code_resend_attempts` في قاعدة البيانات لتتبع عدد المحاولات:

```python
# Save phone_code_hash in database for this user
self.users_collection.update_one(
    {'user_id': user_id},
    {'$set': {
        'phone_code_hash': phone_code_hash,
        'api_id': api_id,
        'api_hash': api_hash,
        'phone_number': phone_number,
        'code_request_time': datetime.now(),
        'code_resend_attempts': 0,  # إضافة عداد لمحاولات إعادة إرسال الرمز
        'updated_at': datetime.now()
    }}
)
```

### 3. تحسين التعامل مع استثناء PhoneCodeExpiredError

تم تحسين التعامل مع حالة انتهاء صلاحية الرمز من خلال:
- التحقق من عدد محاولات إعادة الإرسال
- إضافة تأخير قصير قبل طلب رمز جديد
- تحديث رسائل الخطأ لتكون أكثر وضوحاً

```python
except PhoneCodeExpiredError:
    self.logger.error("Phone code expired")
    
    # تحقق من عدد محاولات إعادة إرسال الرمز
    user_data = self.users_collection.find_one({'user_id': user_id})
    resend_attempts = user_data.get('code_resend_attempts', 0) if user_data else 0
    
    # إذا تجاوزنا الحد الأقصى لمحاولات إعادة الإرسال، نطلب من المستخدم البدء من جديد
    if resend_attempts >= self.max_code_resend_attempts:
        return (False, "لقد تجاوزت الحد الأقصى لمحاولات إعادة إرسال الرمز. يرجى استخدام الأمر /login للبدء من جديد.", None, None)
    
    # Request a new code automatically
    try:
        # إضافة تأخير قصير قبل طلب رمز جديد لتجنب قيود معدل الاستخدام
        await asyncio.sleep(2)
        result = await client.send_code_request(phone_number)
        new_phone_code_hash = result.phone_code_hash
        
        # Update phone_code_hash in database and increment resend attempts
        self.users_collection.update_one(
            {'user_id': user_id},
            {'$set': {
                'phone_code_hash': new_phone_code_hash,
                'code_request_time': datetime.now()
            },
            '$inc': {
                'code_resend_attempts': 1
            }}
        )
        
        return (False, "❌ حدث خطأ أثناء تسجيل الدخول: انتهت صلاحية رمز التحقق.\n\nتم إرسال رمز جديد إلى هاتفك. يرجى إدخال الرمز الجديد:", None, new_phone_code_hash)
    except Exception as e:
        self.logger.error(f"Error requesting new code: {str(e)}")
        return (False, f"❌ حدث خطأ أثناء تسجيل الدخول: انتهت صلاحية رمز التحقق.\n\nحدث خطأ أثناء طلب رمز جديد: {str(e)}\n\nيرجى استخدام الأمر /login للمحاولة مرة أخرى.", None, phone_code_hash)
```

### 4. تنظيف قاعدة البيانات بعد تسجيل الدخول بنجاح

تم تحسين عملية تنظيف البيانات المؤقتة بعد تسجيل الدخول بنجاح:

```python
# Save user credentials in database
self.users_collection.update_one(
    {'user_id': user_id},
    {'$set': {
        'api_id': api_id,
        'api_hash': api_hash,
        'phone_number': phone_number,
        'session_string': session_string,
        'updated_at': datetime.now()
    },
    '$unset': {
        'phone_code_hash': "",  # Remove phone_code_hash after successful login
        'code_request_time': "",
        'code_resend_attempts': ""  # إزالة عداد محاولات إعادة الإرسال بعد تسجيل الدخول بنجاح
    }}
)
```

### 5. تحسين رسائل الخطأ

تم تحسين رسائل الخطأ لتكون أكثر وضوحاً وتوفر معلومات أفضل للمستخدم:

```python
except PhoneCodeInvalidError:
    self.logger.error(f"Invalid phone code: {code}")
    return (False, "❌ حدث خطأ أثناء تسجيل الدخول: رمز التحقق غير صحيح.\n\nيرجى التأكد من الرمز وإدخاله مرة أخرى:", None, phone_code_hash)
```

## كيفية استخدام الكود المعدل

1. قم بتحميل الملفات المعدلة واستبدالها بالملفات الحالية
2. أعد تشغيل البوت باستخدام الأمر `python main.py`
3. عند تسجيل الدخول، إذا انتهت صلاحية الرمز، سيقوم البوت تلقائياً بطلب رمز جديد وإخبار المستخدم بذلك
4. يمكن للمستخدم إدخال الرمز الجديد مباشرة دون الحاجة لبدء عملية تسجيل الدخول من جديد

## ملاحظات إضافية

- تم تحديد الحد الأقصى لمحاولات إعادة إرسال الرمز بـ 3 محاولات، يمكن تعديل هذه القيمة حسب الحاجة
- تم إضافة تأخير قصير (2 ثانية) قبل طلب رمز جديد لتجنب قيود معدل الاستخدام من تيليجرام
- تم تحسين التعامل مع الأخطاء في جميع أنحاء الكود للتعامل بشكل أفضل مع حالات الفشل المختلفة
