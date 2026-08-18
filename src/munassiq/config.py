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


# النموذج الافتراضي هو الأقوى المتاح على الحساب؛ MUNASSIQ_MODEL يسمح بالتحويل
# المؤقت إلى نموذج شقيق بميزانية tokens مستقلة عند بلوغ سقف Groq اليومي
# (حدود Groq تُحسب لكل نموذج على حدة).
DEFAULT_MODEL = "openai/gpt-oss-120b"


def get_llm() -> ChatGroq:
    """يبني عميل ChatGroq المشترك بالمواصفات الموحّدة لكل وكلاء المشروع."""
    return ChatGroq(
        model=os.environ.get("MUNASSIQ_MODEL", DEFAULT_MODEL),
        temperature=0,
        max_retries=2,
        timeout=60,
    )
