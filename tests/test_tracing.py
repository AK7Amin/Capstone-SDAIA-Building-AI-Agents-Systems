"""اختبار الشريحة 8 — تتبع LangSmith: الاسم الصحيح، والاستعلام، ووصول الـrun.

ثلاثة أسئلة منفصلة، وأثمانها مختلفة فلا تُدمج في اختبار واحد:

1. **الاسم**: ``LANGCHAIN_TRACING_V2`` هو الاسم الذي تقرؤه LangChain. الفخ أن
   ``LANGSMITH_TRACING_V2`` يبدو صحيحًا ويُقبل بلا خطأ — ثم **لا يصل أي
   trace**، فالفشل صامت لا يُكتشف إلا بغياب الـruns من اللوحة. لذلك يفحص
   الاختبار الرسالة لا مجرد وقوع الاستثناء: رسالةٌ لا تسمّي الاسم الصحيح
   تترك القارئ في الفخ نفسه.
2. **الاستعلام**: أن ``wait_for_recent_run`` يتصل بـLangSmith فعلًا ويعيد
   الحقول الثلاثة. هذا الاختبار **لا يستهلك حصة Groq** — يقرأ runs موجودة
   أصلًا في المشروع بلا توليد أي شيء، فيبقى في مجموعة ``not api``.
3. **الرحلة كاملة**: نداء نموذج حقيقي ثم ظهور run جديد بعده. هذا وحده موسوم
   ``api`` لأنه هو وحده ما يستهلك حصة النموذج.

التأكيد على **مجموعة المفاتيح بالضبط** (لا على وجودها فقط) مقصود: قرار الأمن
في هذه الشريحة أن يعود بيانُ الـrun منقّحًا — معرّف واسم وحالة — لا
``dict(run)`` كاملًا بمدخلاته ومخرجاته ولا رابطًا موقّعًا. تأكيدُ «يحتوي على»
يمرّ على تسريبٍ كهذا؛ تأكيدُ «يساوي» يسقط عنده.
"""

import datetime as dt

import pytest

from munassiq.tracing import (
    TRACING_FLAG,
    WRONG_TRACING_FLAG,
    assert_tracing_configured,
    wait_for_recent_run,
)

# الحقول الثلاثة المسموح بعودتها — لا رابعَ لها.
EXPECTED_RUN_FIELDS = {"id", "name", "status"}


def _assert_redacted(run: dict) -> None:
    """يتحقق أن بيان الـrun منقّح: ثلاثة حقول، وبلا أي رابط."""
    assert set(run) == EXPECTED_RUN_FIELDS, (
        "بيان الـrun ليس الحقول الثلاثة بالضبط — تسريبُ مدخلات أو مخرجات أو "
        f"روابط موقّعة إلى المتصل؛ ما عاد: {sorted(run)}"
    )
    leaked = [key for key, value in run.items() if "http" in str(value).lower()]
    assert not leaked, f"رابط تسرّب في الحقول {leaked} — قرار الأمن: بلا روابط"


@pytest.mark.langsmith
def test_tracing_env_is_correctly_named(monkeypatch):
    """الاسم الصحيح يمرّ، والاسم الخاطئ يُوقَف برسالة تسمّي الصحيح.

    الشطر الأول يثبت أن بيئة هذا الجهاز مضبوطة فعلًا (وإلا فكل ما بعده وهم)،
    والشطر الثاني يثبت أن الفخ مكشوف لا مسكوت عنه.
    """
    summary = assert_tracing_configured()

    assert summary["project"], (
        f"اسم المشروع غائب عن ملخّص الإعداد: {summary!r}"
    )
    assert summary["api_key_present"] is True, (
        "الملخّص لا يقرّ بوجود مفتاح LangSmith رغم مرور الفحص"
    )
    assert not any("http" in str(value).lower() for value in summary.values()), (
        f"الملخّص يحمل رابطًا — لا يُطبع من الإعداد إلا ما لا يُسرّب: {summary!r}"
    )
    # لا يُعاد مفتاح ولا قيمته — الإقرار بالوجود فقط.
    assert "api_key" not in summary, "قيمة المفتاح لا تخرج من الدالة أبدًا"

    # ---- الفخ: الاسم الخاطئ مكان الصحيح ----
    monkeypatch.delenv(TRACING_FLAG, raising=False)
    monkeypatch.setenv(WRONG_TRACING_FLAG, "true")

    with pytest.raises(RuntimeError) as excinfo:
        assert_tracing_configured()

    message = str(excinfo.value)
    assert TRACING_FLAG in message, (
        "الرسالة لا تسمّي الاسم الصحيح — القارئ يبقى في الفخ نفسه؛ "
        f"ما قيل له: {message!r}"
    )
    assert WRONG_TRACING_FLAG in message, (
        f"الرسالة لا تسمّي الاسم الخاطئ الذي زُرع فعلًا: {message!r}"
    )
    assert "صامت" in message or "بصمت" in message, (
        "الرسالة لا تنبّه أن فشل الاسم الخاطئ صامت — وهذا لبّ الفخ؛ "
        f"ما قيل: {message!r}"
    )


@pytest.mark.langsmith
def test_langsmith_query_works():
    """الاستعلام والاتصال يعملان — بلا توليد أي run جديد ولا حصة نموذج.

    بلا ``since``: أي run تاريخي في المشروع يكفي. ما يُثبَت هنا أن المفتاح
    صالح، وأن المشروع موجود، وأن ``wait_for_recent_run`` يعود بالحقول
    المنقّحة الثلاثة — فلا يبقى في الاختبار الموسوم ``api`` مجهولٌ إلا نداء
    النموذج نفسه.
    """
    run = wait_for_recent_run(timeout_s=45, poll_s=5)

    _assert_redacted(run)
    assert run["id"], f"معرّف الـrun فارغ: {run!r}"
    assert run["name"], f"اسم الـrun فارغ: {run!r}"


@pytest.mark.langsmith
def test_wait_for_recent_run_times_out_without_matches():
    """المهلة تنقضي فيُرمى خطأ صريح — لا انتظارٌ بلا نهاية ولا ``None`` صامت.

    ``since`` في المستقبل البعيد لا يطابقه أي run، و``timeout_s=0`` يعني
    محاولةً واحدة ثم انقضاء — فيُفحص الوجه الآخر من الـpolling بلا انتظار
    فعلي في الجلسة.
    """
    far_future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=3650)

    with pytest.raises(TimeoutError) as excinfo:
        wait_for_recent_run(since=far_future, timeout_s=0, poll_s=1)

    message = str(excinfo.value)
    assert "LANGCHAIN_PROJECT" in message or "المشروع" in message, (
        f"رسالة المهلة لا تدلّ على المشروع الذي بُحث فيه: {message!r}"
    )


@pytest.mark.api
@pytest.mark.timeout(180)
def test_trace_lands_in_langsmith():
    """الرحلة كاملة: نداء نموذج حقيقي يُنتج run جديدًا يصل LangSmith.

    ``since`` يُلتقط **قبل** النداء، فالـrun الذي يعود لا يمكن أن يكون بقيّة
    تشغيلة سابقة — وهذا ما يجعل الاختبار دليلًا على أن التتبع يعمل الآن لا
    على أنه عمل يومًا ما.
    """
    from munassiq.config import get_llm

    since = dt.datetime.now(dt.timezone.utc)

    get_llm().invoke("ping")

    run = wait_for_recent_run(since=since, timeout_s=60, poll_s=5)

    _assert_redacted(run)
    assert run["id"], f"معرّف الـrun الجديد فارغ: {run!r}"
