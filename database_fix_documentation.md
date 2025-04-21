# إصلاح مشكلة قاعدة البيانات في بوت تيليجرام

## المشكلة
عند محاولة تسجيل الخروج من البوت، تظهر رسالة خطأ:
```
sqlite3.OperationalError: no such column: code_input_attempts
```

## سبب المشكلة
في التحديث السابق، تمت إضافة عمود `code_input_attempts` في كود الخدمة (`auth_service.py`) لتتبع عدد محاولات إدخال رمز التحقق، لكن لم يتم إضافة هذا العمود إلى هيكل قاعدة البيانات في ملف `db.py`.

## الحل
تم إجراء التعديلات التالية:

1. إضافة عمود `code_input_attempts` إلى جدول المستخدمين في هيكل قاعدة البيانات:
   ```sql
   CREATE TABLE IF NOT EXISTS users (
       ...
       code_resend_attempts INTEGER DEFAULT 0,
       code_input_attempts INTEGER DEFAULT 0,
       ...
   )
   ```

2. إضافة فحص للتحقق من وجود العمود في قواعد البيانات الموجودة، وإضافته إذا لم يكن موجوداً:
   ```python
   # Check if code_input_attempts column exists in users table, add it if not
   try:
       self.cursor.execute("SELECT code_input_attempts FROM users LIMIT 1")
   except sqlite3.OperationalError:
       # Column doesn't exist, add it
       self.cursor.execute("ALTER TABLE users ADD COLUMN code_input_attempts INTEGER DEFAULT 0")
       print("Added code_input_attempts column to users table")
   ```

## كيفية تطبيق الحل
1. قم بفك ضغط الملف المرفق
2. استبدل ملف `database/db.py` الموجود في البوت الحالي بالملف المحدث
3. أعد تشغيل البوت

بعد تطبيق هذه التغييرات، يجب أن تعمل وظيفة تسجيل الخروج بشكل صحيح دون ظهور أي أخطاء.
