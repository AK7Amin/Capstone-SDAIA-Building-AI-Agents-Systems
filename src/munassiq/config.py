"""تحميل بيئة المشروع وتوفير عميل LLM المشترك.

يحمّل ``.env`` من جذر المشروع — نسبيًا عبر ``Path(__file__)``، بلا مسار
مطلق حرفي في الكود — قبل أي استخدام لمفاتيح Groq/LangSmith، ويضبط ترميز
الإخراج الافتراضي ليدعم العربية في كل بيئات التشغيل (سطر أوامر ويندوز
ضمنًا).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq

# جذر المشروع مشتق من مكان هذا الملف: src/munassiq/config.py -> src/munassiq
# -> src -> الجذر. لا مسار مطلق حرفي مزروع في الكود.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

# يحمّل GROQ_API_KEY، LANGSMITH_API_KEY، LANGCHAIN_TRACING_V2، وLANGCHAIN_PROJECT
# من .env إلى os.environ — القيم كلها من الملف لا من الكود.
load_dotenv(dotenv_path=ENV_PATH)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


# المزود الافتراضي Groq (بيئة الدورة)؛ MUNASSIQ_PROVIDER يحوّل إلى مزود آخر
# عند بلوغ سقف Groq المجاني اليومي — openrouter يتيح نموذج الدورة الأصلي
# llama-3.3-70b-instruct الذي يرجع 404 على حساب Groq هذا.
DEFAULT_PROVIDER = "groq"
# نفس النموذج على المزوّدَين: gpt-oss-120b أثبت نداءات الأدوات والمخرجات
# المهيكلة عبر كل الشرائح. جُرّب llama-3.3-70b (نموذج الدورة) عبر OpenRouter
# فدخل حلقة تحويلات لا تتوقف في المشرف (GraphRecursionError) — استُبعد.
DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "openrouter": "openai/gpt-oss-120b",
    "google": "gemini-2.5-flash",
}


def get_llm():
    """يبني عميل الدردشة المشترك بالمواصفات الموحّدة لكل وكلاء المشروع.

    المزود من ``MUNASSIQ_PROVIDER`` والنموذج من ``MUNASSIQ_MODEL`` — القيم
    الافتراضية أعلاه. كل المزودين هنا مجربون على نداءات الأدوات والمخرجات
    المهيكلة التي يعتمد عليها المشروع.
    """
    provider = os.environ.get("MUNASSIQ_PROVIDER", DEFAULT_PROVIDER)
    model = os.environ.get("MUNASSIQ_MODEL") or DEFAULT_MODELS[provider]
    common = {"temperature": 0, "max_retries": 2, "timeout": 60}

    if provider == "groq":
        return ChatGroq(model=model, **common)
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            **common,
        )
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, **common)
    raise ValueError(f"مزود غير معروف: {provider}")


def invoke_structured(structured_runnable, prompt, attempts: int = 3):
    """نداء مخرج مهيكل بإعادة محاولة على نزوات المزود المرصودة.

    ثلاثة أشكال فشل شوهدت **فعليًا** عبر OpenRouter وكلها عابرة تُحل
    بإعادة النداء (تطبيق استراتيجية «LLM-recoverable» على نداءاتنا نفسها):
    قيمة خام بدل الكائن (``-2.0`` → ValidationError من pydantic)، ورسالة
    بلا حقل ``parsed`` (ValueError من langchain)، وفشل تحليل جانب الخادم
    (BadRequestError برمز 400). ما عداها ينتشر فورًا — لا نبتلع أخطاء
    البرمجة؛ وبعد استنفاد المحاولات ينتشر آخر خطأ.
    """
    from pydantic import ValidationError

    last_error = None
    for _ in range(attempts):
        try:
            return structured_runnable.invoke(prompt)
        except Exception as error:
            recoverable = isinstance(error, (ValidationError, ValueError)) or (
                type(error).__name__ == "BadRequestError"
            )
            if not recoverable:
                raise
            last_error = error
    raise last_error
