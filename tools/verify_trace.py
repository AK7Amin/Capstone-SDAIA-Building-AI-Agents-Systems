"""سكربت يدوي: يثبت أن تتبع LangSmith مضبوط وأن الـruns تصل فعلًا.

يُشغَّل من جذر المشروع::

    .venv\\Scripts\\python.exe tools\\verify_trace.py

ولا يستهلك حصة نموذج: يقرأ إعداد البيئة ثم يستعلم عن runs موجودة أصلًا.
مخرَجه سطورٌ قصيرة تصلح للصق في النوتبوك أو عرضها على الشاشة.

**لا يطبع قيمة أي مفتاح ولا جزءًا منها** — عن المفتاح إقرارٌ بالوجود فقط، وعن
كل run معرّفُه واسمُه ووقتُ بدئه؛ لا مدخلات ولا مخرجات ولا روابط موقّعة.
"""

import sys
from pathlib import Path

# تشغيل مباشر من مجلد tools/: الحزمة تسكن في src/ فتُضاف إلى مسار الاستيراد.
# مشتقّ من موقع هذا الملف لا مسارًا مطلقًا مزروعًا، كما في config.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from munassiq.tracing import (  # noqa: E402  بعد ضبط sys.path
    TracingNotConfigured,
    assert_tracing_configured,
    list_recent_runs,
)

RECENT_LIMIT = 3


def main() -> int:
    # سطر أوامر ويندوز يفتح افتراضيًا بترميز لا يسع العربية؛ التحويل هنا لأن
    # PYTHONIOENCODING المضبوط في config.py يأتي بعد إقلاع المفسّر فلا يؤثر.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")

    try:
        summary = assert_tracing_configured()
    except TracingNotConfigured as error:
        print(f"[x] التتبع غير مضبوط: {error}")
        return 1

    print("[✓] إعداد التتبع:")
    print(f"    {summary['flag']} = true")
    print(f"    LANGCHAIN_PROJECT = {summary['project']}")
    print("    LANGSMITH_API_KEY = موجود (القيمة لا تُطبع)")

    try:
        runs = list_recent_runs(limit=RECENT_LIMIT)
    except Exception as error:  # الشبكة أو المصادقة — النوع والرسالة فقط
        print(f"[x] تعذّر الاستعلام عن الـruns: {type(error).__name__}: {error}")
        return 1

    if not runs:
        print(f"[!] لا توجد runs بعد في مشروع «{summary['project']}» — شغّل الوكيل مرة")
        return 1

    print(f"[✓] آخر {len(runs)} من الـruns:")
    for run in runs:
        print(f"    {run['id']}  {run['name']}  {run['started_at']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
