"""تتبع LangSmith — فحص الإعداد، وانتظار وصول الـrun، وقراءة منقّحة له.

**الفخ الذي تحرسه هذه الوحدة**: LangChain تقرأ ``LANGCHAIN_TRACING_V2``
حرفيًا. الاسم ``LANGSMITH_TRACING_V2`` يبدو صحيحًا تمامًا ولا يشتكي منه أحد —
لا LangChain ولا LangSmith ولا مفسّر بايثون — لكن التتبع حينها **مطفأ**، ولا
يصل أي trace، ولا يظهر شيء على اللوحة. الفشل صامت: لا استثناء ولا تحذير، فقط
مشروعٌ فارغ يُكتشف متأخرًا. لذلك يوجد :func:`assert_tracing_configured` أصلًا،
ولذلك تسمّي رسالتُه الاسمَ الصحيح والخاطئ معًا بدل أن تقول «التتبع غير مضبوط».

**واجهة الاستعلام المثبَّتة: ``Client.list_runs``** — وهي مُهلَكة (deprecation)
والبديل المعلَن ``client.runs.query()`` بعد 31 يناير 2027. جُرّب البديل في هذه
النسخة (langsmith 0.11) فعمل، ومع ذلك بقي القديم مثبَّتًا لأربعة أسباب مقيسة:

1. ``client.runs`` في هذه النسخة ``AsyncRunsResource`` — غير متزامن. تغليفه
   بـ``asyncio.run`` داخل دالة متزامنة يعمل في السكربت **ويسقط في النوتبوك**
   (حلقة أحداث تعمل أصلًا في نواة Jupyter)، والنوتبوك أحد موضعَي الاستعمال
   المقصودَين هنا.
2. لا يقبل ``project_name`` بل ``project_ids`` — فيلزم نداء إضافي لترجمة
   الاسم إلى UUID، ونقطةُ فشلٍ زائدة في مسارٍ كل غرضه إثبات أن التتبع يعمل.
3. ``min_start_time`` في المستقبل يعيد ``400 Bad Request`` بدل نتيجة فارغة —
   وهذا بالضبط ما يفعله polling يبدأ من ``since=now``.
4. المهلة المعلنة (2027) أبعد بكثير من عمر هذا المشروع، والتحذير مكتومٌ عند
   نقطة النداء وحدها ومشروحٌ هنا — لا مكتوم عالميًا.

**قرار الأمن**: لا يخرج من هذه الوحدة إلا بيانٌ منقّح للـrun — معرّف واسم
وحالة (ووقت بدء في القائمة اليدوية). لا ``dict(run)`` كامل، ولا مدخلات ولا
مخرجات (فيها نصوص الأعضاء والمراسلات)، ولا روابط موقّعة. ولا تُطبع قيمة أي
مفتاح ولا جزء منها في أي حال.
"""

from __future__ import annotations

import datetime as dt
import os
import time
import warnings
from typing import Any

from munassiq import config as _config  # noqa: F401  يحمّل .env قبل أي قراءة

# الاسم الذي تقرؤه LangChain فعلًا، ومقابله الخاطئ الذي يفشل بصمت.
TRACING_FLAG = "LANGCHAIN_TRACING_V2"
WRONG_TRACING_FLAG = "LANGSMITH_TRACING_V2"
PROJECT_VAR = "LANGCHAIN_PROJECT"
API_KEY_VAR = "LANGSMITH_API_KEY"

# الحقول المطلوبة من الخادم — تضييقٌ متعمّد: ما لا يُطلب لا يصل الذاكرة أصلًا،
# فتبقى المدخلات والمخرجات (نصوص المراسلات) خارج العملية لا مُرشَّحة داخلها.
_SELECTED_FIELDS = ("name", "status", "start_time")

# هامش لانحراف ساعة الجهاز عن ساعة خادم LangSmith. بلا هذا الهامش قد يُحسب
# run وُلد بعد ``since`` وكأنه قبله فتنقضي المهلة على تتبعٍ سليم.
CLOCK_SKEW_ALLOWANCE = dt.timedelta(seconds=5)


class TracingNotConfigured(RuntimeError):
    """إعداد التتبع ناقص أو مكتوب باسم خاطئ — استثناء مميَّز ليُلتقط وحده."""


def _as_utc(moment: dt.datetime) -> dt.datetime:
    """يوحّد أي لحظة إلى UTC؛ اللحظة بلا منطقة زمنية تُقرأ على أنها UTC."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=dt.timezone.utc)
    return moment.astimezone(dt.timezone.utc)


def assert_tracing_configured() -> dict[str, Any]:
    """يتحقق أن تتبع LangSmith مضبوط فعلًا، ويعيد ملخّصًا بلا أي قيمة مفتاح.

    يفحص ثلاثة أشياء بالترتيب: قيمة ``LANGCHAIN_TRACING_V2`` بعد التصغير
    ``"true"``، ووجود ``LANGCHAIN_PROJECT``، ووجود ``LANGSMITH_API_KEY``.

    يرفع :class:`TracingNotConfigured` (وهو ``RuntimeError``) برسالة تسمّي
    المتغيّر الناقص، وتنبّه إلى الاسم الخاطئ ``LANGSMITH_TRACING_V2`` حين
    يكون هو الموجود — لأن ذلك الفخ لا يُكتشف بغير تنبيه.

    الملخّص العائد يصلح للطباعة كما هو: اسم المشروع ليس سرًّا، أما المفتاح
    فلا يعود منه إلا إقرارٌ بالوجود.
    """
    tracing_value = os.environ.get(TRACING_FLAG)

    if tracing_value is None:
        hint = ""
        if os.environ.get(WRONG_TRACING_FLAG) is not None:
            hint = (
                f" — الموجود في البيئة هو {WRONG_TRACING_FLAG}، وهو اسم خاطئ "
                "لا تقرؤه LangChain: التتبع يبقى مطفأً ولا يصل أي trace، "
                "والفشل صامت بلا خطأ ولا تحذير. غيّر الاسم فقط"
            )
        raise TracingNotConfigured(
            f"متغيّر التتبع {TRACING_FLAG} غير مضبوط في البيئة{hint}. "
            f"الصحيح حرفيًا: {TRACING_FLAG}=true في ملف ‎.env"
        )

    if tracing_value.strip().lower() != "true":
        raise TracingNotConfigured(
            f"{TRACING_FLAG} قيمته «{tracing_value}» لا «true» — التتبع مطفأ. "
            f"وتنبيه: {WRONG_TRACING_FLAG} اسم خاطئ يفشل بصمت، فتأكد أن "
            f"الاسم {TRACING_FLAG} حرفيًا"
        )

    project_name = (os.environ.get(PROJECT_VAR) or "").strip()
    if not project_name:
        raise TracingNotConfigured(
            f"{PROJECT_VAR} غير مضبوط — الـruns ستذهب إلى مشروع افتراضي "
            "لا تجده في اللوحة. اضبطه في ملف ‎.env"
        )

    if not (os.environ.get(API_KEY_VAR) or "").strip():
        raise TracingNotConfigured(
            f"{API_KEY_VAR} غير موجود في البيئة — لا يمكن إرسال trace ولا "
            "الاستعلام عنه. اضبطه في ملف ‎.env (ولا يُطبع أبدًا)"
        )

    return {
        "flag": TRACING_FLAG,
        "enabled": True,
        "project": project_name,
        "api_key_present": True,
    }


def _redact(run: Any) -> dict[str, Any]:
    """يحوّل كائن الـrun إلى بيانٍ منقّح — نقطة التنقيح الوحيدة في الوحدة."""
    started_at = getattr(run, "start_time", None)
    return {
        "id": str(getattr(run, "id", "") or ""),
        "name": getattr(run, "name", None) or "",
        "status": getattr(run, "status", None) or "",
        "started_at": started_at.isoformat() if started_at else "",
    }


def list_recent_runs(
    project_name: str | None = None,
    limit: int = 3,
    since: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    """يعيد أحدث ``limit`` من الـruns منقّحةً (معرّف/اسم/حالة/وقت بدء).

    ``since`` يقصر النتيجة على ما بدأ بعدها (مع هامش انحراف الساعة).
    يفحص الإعداد أولًا، فرسالةُ «التتبع غير مضبوط» أنفع من خطأ مصادقة خام.
    """
    summary = assert_tracing_configured()
    target_project = (project_name or summary["project"]).strip()

    from langsmith import Client

    query: dict[str, Any] = {
        "project_name": target_project,
        "limit": limit,
        "select": list(_SELECTED_FIELDS),
    }
    if since is not None:
        query["start_time"] = _as_utc(since) - CLOCK_SKEW_ALLOWANCE

    with warnings.catch_warnings():
        # مكتومٌ هنا وحده: الإهلاك معروف ومشروح في وثيقة الوحدة، ولا داعي
        # لتلويث مخرَج كل تشغيلة اختبار بتحذيرٍ قرارُه متّخذ.
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        runs = list(Client().list_runs(**query))

    return [_redact(run) for run in runs]


def wait_for_recent_run(
    project_name: str | None = None,
    since: dt.datetime | None = None,
    timeout_s: float = 60,
    poll_s: float = 5,
) -> dict[str, Any]:
    """ينتظر ظهور run في المشروع ثم يعيد بيانه المنقّح (معرّف/اسم/حالة).

    ``since`` هو ما يجعل الانتظار دليلًا: مع ``since=now`` قبل نداء النموذج،
    الـrun الذي يعود لا يمكن أن يكون بقيّةَ تشغيلةٍ سابقة. وبلا ``since`` تكفي
    أي run تاريخية — وهذا يثبت الاتصال والاستعلام وحدهما.

    الانتظار **polling بمهلة** لا نومٌ ثابت: الـrun قد يظهر بعد ثانية وقد يتأخر
    عشرًا، فالنوم الثابت إما يُبطئ كل تشغيلة أو يسقط عشوائيًا. تُجرى محاولة
    واحدة على الأقل مهما صغرت المهلة (``timeout_s=0`` يعني محاولةً ثم انقضاء).

    يرفع :class:`TimeoutError` عند انقضاء المهلة — لا يعيد ``None`` أبدًا،
    فقيمةٌ فارغة تُنسى فحصُها تحوّل «التتبع لا يعمل» إلى نجاحٍ كاذب.
    """
    deadline = time.monotonic() + max(timeout_s, 0)
    attempts = 0

    while True:
        attempts += 1
        found = list_recent_runs(project_name=project_name, limit=1, since=since)
        if found:
            newest = found[0]
            # الحقول الثلاثة فقط — ``started_at`` يبقى للقائمة اليدوية.
            return {
                "id": newest["id"],
                "name": newest["name"],
                "status": newest["status"],
            }

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(poll_s, remaining))

    target_project = (
        project_name or os.environ.get(PROJECT_VAR, "") or "<غير مضبوط>"
    ).strip()
    window = f" بعد {_as_utc(since).isoformat()}" if since is not None else ""
    raise TimeoutError(
        f"لم يظهر أي run في مشروع LANGCHAIN_PROJECT=«{target_project}»{window} "
        f"خلال {timeout_s:g} ثانية ({attempts} محاولة). تحقق أن "
        f"{TRACING_FLAG}=true حرفيًا — {WRONG_TRACING_FLAG} اسم خاطئ يفشل بصمت"
    )
