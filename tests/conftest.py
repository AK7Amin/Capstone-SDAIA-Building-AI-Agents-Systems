"""جلسة pytest — يتأكد أن مفاتيح البيئة محمّلة قبل أي اختبار.

استيراد ``munassiq.config`` يحمّل ``.env`` عبر python-dotenv. إن غاب أي من
GROQ_API_KEY أو LANGSMITH_API_KEY بعد ذلك، فهذا عطل بيئة (مفتاح غير مضبوط
على هذا الجهاز) لا غياب ميزة — نوقف الجلسة برسالة مميزة عن xfail بدل أن
تُقرأ عشرات أخطاء الاختبارات المرتبطة بمفتاح واحد غائب.
"""

import os

import pytest


def pytest_configure(config):
    from munassiq import config as _munassiq_config  # noqa: F401  يحمّل .env

    missing = [
        key for key in ("GROQ_API_KEY", "LANGSMITH_API_KEY") if not os.environ.get(key)
    ]
    if missing:
        pytest.exit("مفاتيح البيئة غائبة — هذا عطل بيئة لا غياب ميزة")
