"""اختبار الشريحة 6 — الوقوف البشري (interrupt) والاستئناف في المراسلات.

المحور الذي يفحصه الروبرك هنا ليس «هل ظهرت كلمة interrupt في الكود؟» بل
**هل وقف التنفيذ فعلًا قبل الفعل غير القابل للعكس، وهل خرج نصُّ البشري كما
كتبه**. ولذلك تأكيدان صلبان لا واحد:

1. الرحلة الأولى تعيد dict فيه ``__interrupt__`` وحمولته فيها مسودة غير
   فارغة — أي أن المسودة صيغت **قبل** الوقوف، فالبشري يراجع نصًّا لا فراغًا.
2. الرحلة الثانية بـ``Command(resume=...)`` على الـthread نفسه تُخرج نص
   البشري **حرفيًا** في ``reply`` وفي ملف صندوق الصادر — تساوٍ تام لا
   احتواء، لأن أي تمرير على نموذج بعد الموافقة كان سيغيّر حرفًا.

وتقسيم الاختبارات مقصود كما في :mod:`test_memory`: مسار الـinterrupt نفسه
مُغطّى **مرتين** — مرة بنداءات النموذج الحقيقية (موسومة ``api``)، ومرة
بمحاكاة تستبدل الـ``@task`` النموذجية بأخرى ثابتة فتفحص الميكانيكا وحدها
(الوقوف، الاستئناف، الحرفية، إعادة تنفيذ الجسم) بلا شبكة أصلًا. فيبقى دليل
الميكانيكا قائمًا حتى لو سقطت الشبكة أو نفدت حصة الـAPI.

كتابة صندوق الصادر تُحوَّل إلى ``tmp_path`` عبر monkeypatch على
``tools.OUTBOX_DIR`` — لا يتراكم أي مخلَّف في ``data/outbox`` الحقيقي.
"""

from pathlib import Path

import pytest
from langgraph.func import task
from langgraph.types import Command

from munassiq import tools

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# طلب مراسلة صريح: فعلٌ غير قابل للعكس باسم الجمعية ⇒ لا بد من موافقة بشرية.
MAIL_REQUEST = "أرسل بريدًا للمتطوعين عن تأجيل فعالية السبت"

# نص البشري بعد التعديل — هو وحده ما يجب أن يخرج، بلا حرفٍ زائد ولا ناقص.
HUMAN_EDIT = "النص المعتمد من المشرف البشري: الفعالية مؤجلة لأسبوع."


def _resolve(returned: str) -> Path:
    """يحوّل المسار الذي أعادته الأداة إلى مسار قابل للقراءة."""
    path = Path(returned)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _reset_and_build(tmp_path):
    """يصفّر الذاكرة إلى ملف مؤقت ثم يبني الـapp فوقها.

    الترتيب إلزامي كما في :mod:`test_memory`: التصفير **قبل** بناء الـapp،
    فالـapp يلتقط الـcheckpointer والـstore لحظة بنائه. وinterrupt/resume
    بالذات لا يعمل إلا على checkpointer واحدٍ عبر النداءين.
    """
    from munassiq.memory import reset_memory_for_tests

    reset_memory_for_tests(tmp_path)

    from munassiq.app import build_app

    return build_app()


@pytest.fixture
def outbox(tmp_path, monkeypatch):
    """يحوّل صندوق الصادر إلى مجلد مؤقت يمحوه pytest تلقائيًا."""
    target = tmp_path / "outbox"
    monkeypatch.setattr(tools, "OUTBOX_DIR", target)
    return target


def _stub_llm_tasks(monkeypatch, *, decision, draft="مسودة اختبارية للمتطوعين."):
    """يستبدل كل ``@task`` تنادي نموذجًا بأخرى ثابتة — لتشغيل بلا شبكة.

    الاستبدال على موديول ``munassiq.app`` نفسه: جسم الـentrypoint يبحث عن
    هذه الأسماء في فضاء الموديول عند كل نداء، فالتحويل هنا يطاله فعلًا.
    الأثر الوحيد الباقي حقيقيًا هو الكتابة في صندوق الصادر — وهو بالضبط ما
    نريد فحصه.

    Args:
        decision: قرار التصنيف الثابت الذي تعيده ``classify_request``.
        draft: المسودة الثابتة التي تعيدها ``draft_correspondence``.
    """
    from munassiq import app as app_module

    @task
    def load_memories(user_id: str) -> list[str]:
        return []

    @task
    def detect_and_store_memory(request: str, user_id: str):
        return None

    @task
    def classify_request(request: str):
        return decision

    @task
    def draft_correspondence(request: str, memories: list[str]) -> str:
        return draft

    @task
    def run_supervisor(request: str, memories: list[str], history: list[dict]) -> str:
        return f"رد المشرف على: {request}"

    for stub in (
        load_memories,
        detect_and_store_memory,
        classify_request,
        draft_correspondence,
        run_supervisor,
    ):
        monkeypatch.setattr(app_module, stub.__name__, stub)


def test_needs_approval_is_pure():
    """قرار «هل يحتاج موافقة» دالة نقية تُختبر بلا نموذج ولا شبكة.

    استخراجه من جسم الـentrypoint مقصود: شرطُ توجيهٍ مدفونٌ داخل غرافٍ لا
    يُفحص إلا بنداء نموذج، ودالةٌ نقية تُفحص بأربعة أسطر.
    """
    from munassiq.app import needs_approval

    mail = tools.TriageDecision(
        worker="correspondence", needs_human_approval=True, summary="إرسال بريد"
    )
    assert needs_approval(mail) is True, "طلب مراسلة معلَّم بالموافقة لم يُعتبر محتاجًا لها"

    # المراسلة تحتاج موافقة بحكم كونها مراسلة، ولو غفل النموذج عن رفع العلم.
    mail_flag_off = tools.TriageDecision(
        worker="correspondence", needs_human_approval=False, summary="صياغة رسالة"
    )
    assert needs_approval(mail_flag_off) is True, (
        "طلب مراسلة مرّ بلا موافقة لأن النموذج لم يرفع needs_human_approval — "
        "الحصر يجب أن يكون بالبنية لا برجاء النموذج"
    )

    calendar = tools.TriageDecision(
        worker="calendar", needs_human_approval=False, summary="حجز اجتماع"
    )
    assert needs_approval(calendar) is False, (
        "طلب تقويمي عادي طُلبت له موافقة بشرية — انحدار على المسار غير المراسلاتي"
    )

    # العلم وحده كافٍ: عاملٌ غير المراسلات إن وُسم بأنه غير قابل للعكس يقف.
    calendar_flagged = tools.TriageDecision(
        worker="calendar", needs_human_approval=True, summary="حذف كل المواعيد"
    )
    assert needs_approval(calendar_flagged) is True, (
        "طلب موسوم needs_human_approval مرّ بلا وقوف"
    )


def test_send_approved_email_is_verbatim(outbox):
    """المسار الحرفي: ما يُمرَّر إلى ``send_approved_email`` هو ما يُكتب.

    بلا شبكة: هذه هي النقطة التي يموت عندها الدليل لو مرّ نص البشري على أي
    نموذج — فالتساوي هنا تامّ لا احتواء.
    """
    returned = tools.send_approved_email(HUMAN_EDIT)
    path = _resolve(returned)

    assert path.is_file(), f"send_approved_email لم تنشئ ملفًا: {returned}"
    assert path.parent == outbox, (
        f"الكتابة خرجت عن صندوق الصادر المؤقت: {path.parent} بدل {outbox}"
    )
    assert path.read_bytes().decode("utf-8") == HUMAN_EDIT, (
        "محتوى الملف لا يساوي نص البشري حرفيًا — مرّ على شيء غيّره"
    )


def test_app_builds_after_hitl_wiring(tmp_path):
    """بلا شبكة: الـapp الجاهز يُستورد ويُبنى بعد إضافة مسار الـinterrupt."""
    from munassiq.app import munassiq_app

    assert munassiq_app is not None, "munassiq_app الجاهز غاب بعد تعديلات الشريحة 6"
    assert _reset_and_build(tmp_path) is not None, "build_app فشل بعد تعديلات الشريحة 6"


def test_interrupt_and_resume_mechanics_without_llm(tmp_path, monkeypatch, outbox):
    """ميكانيكا الوقوف والاستئناف كاملةً بلا أي نداء نموذج.

    كل ``@task`` تنادي نموذجًا مستبدَلة بثابتة؛ الباقي هو الكود الحقيقي:
    التفريع، ``interrupt`` في جسم الـentrypoint، الـcheckpointer، وكتابة
    صندوق الصادر. فلو انكسرت الميكانيكا ظهر هنا بلا انتظار حصة API.
    """
    app = _reset_and_build(tmp_path)
    _stub_llm_tasks(
        monkeypatch,
        decision=tools.TriageDecision(
            worker="correspondence",
            needs_human_approval=True,
            summary="إرسال بريد للمتطوعين عن تأجيل فعالية السبت",
        ),
        draft="مسودة اختبارية: الفعالية مؤجلة.",
    )

    config = {"configurable": {"thread_id": "hitl-offline"}}

    paused = app.invoke({"request": MAIL_REQUEST, "user_id": "member-006"}, config)

    assert isinstance(paused, dict), f"الرحلة الأولى أعادت {type(paused).__name__} لا dict"
    assert "__interrupt__" in paused, (
        "لم يقف التنفيذ على interrupt قبل الفعل غير القابل للعكس — "
        f"ما عاد: {sorted(paused)}"
    )
    assert not list(outbox.glob("sent-*.txt")), (
        "كُتب ملف إرسال قبل موافقة البشري — الوقوف جاء بعد الفعل لا قبله"
    )

    payload = paused["__interrupt__"][0].value
    assert isinstance(payload, dict), f"حمولة الـinterrupt ليست dict: {type(payload).__name__}"
    assert payload.get("draft", "").strip(), (
        f"المسودة في حمولة الـinterrupt فارغة — البشري يراجع فراغًا: {payload}"
    )
    assert payload.get("action", "").strip(), "حمولة الـinterrupt بلا وصف للفعل المطلوب"

    done = app.invoke(Command(resume=HUMAN_EDIT), config)

    assert isinstance(done, dict), f"الاستئناف أعاد {type(done).__name__} لا dict"
    assert "__interrupt__" not in done, "الرحلة وقفت مرة ثانية بدل أن تكتمل"
    assert done.get("reply") == HUMAN_EDIT, (
        "نص البشري لم يخرج حرفيًا في reply — مرّ على نموذج أو أُعيدت صياغته؛ "
        f"ما خرج: {done.get('reply')!r}"
    )

    sent_path = _resolve(done["outbox_path"])
    assert sent_path.is_file(), f"لم يُكتب ملف الإرسال: {done.get('outbox_path')}"
    assert sent_path.read_bytes().decode("utf-8") == HUMAN_EDIT, (
        "محتوى ملف صندوق الصادر لا يساوي نص البشري حرفيًا"
    )


def test_non_correspondence_request_skips_interrupt(tmp_path, monkeypatch, outbox):
    """لا انحدار: الطلب غير المراسلاتي يمضي إلى المشرف بلا وقوف — بلا شبكة."""
    app = _reset_and_build(tmp_path)
    _stub_llm_tasks(
        monkeypatch,
        decision=tools.TriageDecision(
            worker="calendar", needs_human_approval=False, summary="حجز اجتماع"
        ),
    )

    result = app.invoke(
        {"request": "احجز اجتماعًا يوم الأحد", "user_id": "member-006"},
        {"configurable": {"thread_id": "hitl-offline-calendar"}},
    )

    assert "__interrupt__" not in result, (
        "طلب تقويمي أوقف الرحلة — الـinterrupt تسرّب إلى المسار غير المراسلاتي"
    )
    assert result.get("reply", "").strip(), "الرد فارغ على المسار غير المراسلاتي"
    assert result.get("turn") == 1, f"عدّاد الأدوار انكسر: {result.get('turn')}"
    assert not list(outbox.glob("sent-*.txt")), "كُتب ملف إرسال لطلب لا علاقة له بالمراسلات"


@pytest.mark.api
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=2, reruns_delay=30)
def test_interrupt_then_resume_completes(tmp_path, outbox):
    """المسار كاملًا بنداءات حقيقية: وقوفٌ بمسودة، ثم استئنافٌ حرفي."""
    app = _reset_and_build(tmp_path)

    config = {"configurable": {"thread_id": "hitl-live"}}

    paused = app.invoke({"request": MAIL_REQUEST, "user_id": "member-006"}, config)

    assert isinstance(paused, dict), f"الرحلة الأولى أعادت {type(paused).__name__} لا dict"
    assert "__interrupt__" in paused, (
        "لم يقف التنفيذ على interrupt قبل إرسال بريد باسم الجمعية — "
        f"ما عاد: {sorted(paused)}"
    )

    payload = paused["__interrupt__"][0].value
    assert isinstance(payload, dict), f"حمولة الـinterrupt ليست dict: {type(payload).__name__}"
    assert payload.get("draft", "").strip(), (
        f"المسودة في حمولة الـinterrupt فارغة — البشري يراجع فراغًا: {payload}"
    )
    assert not list(outbox.glob("sent-*.txt")), (
        "كُتب ملف إرسال قبل موافقة البشري — الفعل سبق الوقوف"
    )

    done = app.invoke(Command(resume=HUMAN_EDIT), config)

    assert isinstance(done, dict), f"الاستئناف أعاد {type(done).__name__} لا dict"
    assert "__interrupt__" not in done, "الرحلة وقفت مرة ثانية بدل أن تكتمل"
    assert done.get("reply") == HUMAN_EDIT, (
        "نص البشري لم يخرج حرفيًا في reply — مرّ على نموذج بعد الموافقة؛ "
        f"ما خرج: {done.get('reply')!r}"
    )
    assert HUMAN_EDIT in str(done), "تعديل البشري لا أثر له في الناتج النهائي"

    sent_path = _resolve(done["outbox_path"])
    assert sent_path.is_file(), f"لم يُكتب ملف الإرسال: {done.get('outbox_path')}"
    assert sent_path.read_bytes().decode("utf-8") == HUMAN_EDIT, (
        "محتوى ملف صندوق الصادر لا يساوي نص البشري حرفيًا"
    )
