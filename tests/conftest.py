"""جلسة pytest — تحميل البيئة، وتخطٍّ رشيق لما يحتاج مفاتيح عند غيابها.

استيراد ``munassiq.config`` يحمّل ``.env`` عبر python-dotenv. ثلاث طبقات
اختبار (ملاحظة مراجعة خارجية 20 أغسطس — قابلية إعادة التشغيل بلا مفاتيح):

* بلا وسم — محلي صرف، يعمل على جهاز بلا أي مفتاح.
* ``langsmith`` — يستعلم LangSmith API (شبكة، بلا استهلاك نموذج).
* ``api`` — يستدعي نموذج LLM الحقيقي.

غياب مفتاحٍ لم يعد يوقف الجلسة: تُتخطى الاختبارات المحتاجة إليه برسالة
مميزة، ويُزرع للبقية مفتاحٌ دمية يكفي بناء العملاء بلا أي نداء شبكة —
فيبقى المحلي قابلًا للتشغيل في أي بيئة.
"""

import os

import pytest

# تُحسب في configure قبل زرع الدمى، ويقرؤها modifyitems — لو قرأنا البيئة
# هناك مباشرة لخدعتنا الدمية وظننا المفاتيح الحقيقية حاضرة.
_MISSING_LLM_KEY = False
_MISSING_LANGSMITH_KEY = False


def pytest_configure(config):
    from munassiq import config as _munassiq_config  # noqa: F401  يحمّل .env

    global _MISSING_LLM_KEY, _MISSING_LANGSMITH_KEY
    _MISSING_LLM_KEY = not (
        os.environ.get("GROQ_API_KEY") and os.environ.get("OPENROUTER_API_KEY")
    )
    _MISSING_LANGSMITH_KEY = not os.environ.get("LANGSMITH_API_KEY")

    # لا مفتاح LangSmith ⇒ لا تتبع: وإلا أغرقت محاولاتُ الإرسال الفاشلة (401)
    # مخرجَ الاختبارات المحلية على جهاز بلا مفاتيح.
    if _MISSING_LANGSMITH_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

    # مفاتيح دمية للاختبارات المحلية الصرفة: بناءُ عميل (ChatOpenAI مثلًا)
    # يرفض مفتاحًا غائبًا حتى بلا أي نداء شبكة. الاختبارات الشبكية تُتخطى
    # قبل أن تلمس هذه القيم، والعلم يسمح لاختبار البيئة في test_scaffold
    # أن يميز الدمية عن مفتاح حقيقي.
    if _MISSING_LLM_KEY:
        os.environ["MUNASSIQ_DUMMY_KEYS"] = "1"
        # تعيين مباشر لا setdefault: المتغير الموجود بقيمة فارغة غائبٌ عمليًا.
        if not os.environ.get("GROQ_API_KEY"):
            os.environ["GROQ_API_KEY"] = "dummy-key-offline-construction"
        if not os.environ.get("OPENROUTER_API_KEY"):
            os.environ["OPENROUTER_API_KEY"] = "dummy-key-offline-construction"


def pytest_collection_modifyitems(config, items):
    skip_api = pytest.mark.skip(
        reason="مفتاح النموذج غائب — عطل بيئة لا غياب ميزة (اختبار يستدعي نموذجًا)"
    )
    skip_ls = pytest.mark.skip(
        reason="LANGSMITH_API_KEY غائب — عطل بيئة لا غياب ميزة (اختبار يخص LangSmith)"
    )
    for item in items:
        if _MISSING_LLM_KEY and "api" in item.keywords:
            item.add_marker(skip_api)
        if _MISSING_LANGSMITH_KEY and (
            "langsmith" in item.keywords or "api" in item.keywords
        ):
            item.add_marker(skip_ls)
