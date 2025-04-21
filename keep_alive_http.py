from flask import Flask
from threading import Thread
import logging

# تعطيل سجلات Flask غير الضرورية
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    return "البوت يعمل!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """تشغيل خادم ويب بسيط للحفاظ على البوت نشطًا"""
    t = Thread(target=run)
    t.daemon = True  # جعل الخيط daemon لإيقافه عند إيقاف البرنامج الرئيسي
    t.start()
    print("تم تشغيل خادم الويب للحفاظ على البوت نشطًا")
