"""اختبار الشريحة 7 — استراتيجيتا الخطأ والنمط المسمّى Evaluator-Optimizer.

ثلاثة محاور يفحصها الروبرك هنا، وكلها مفحوصة **بلا أي نداء نموذج**:

1. **العابر Transient**: ``RetryPolicy`` على ``@task`` يلتقط فشلًا شبكيًا
   مفتعلًا فينجح في المحاولة الثالثة — ودليلُه عدّادٌ يحصي المحاولات فعلًا،
   لا مجرد نجاح النداء (نجاحٌ من أول محاولة يمرّ بلا أن يثبت شيئًا). ويقابله
   اختبار الوجه الآخر: الفشل **الدائم** ينتشر بعد استنفاد الثلاث، فالسياسة
   تكرارٌ محدود لا ابتلاعٌ للأخطاء.
2. **LLM-recoverable**: خطأ الأداة يعود إلى النموذج نصًّا في رسالة تصحيحية
   فيصحح مدخله. الآلية تُفحص ببديل نموذج مُحقن (callable) يعيد مدخلًا فاسدًا
   أولًا ثم مصححًا — فيبقى الدليل قائمًا بلا شبكة ولا حصة API.
3. **Evaluator-Optimizer**: الحلقة تدور **قبل** الـinterrupt، والتحسين
   يُستدعى بملاحظات المقيّم نفسها. وأدقّ تأكيد هنا أن القرار يُقرأ من
   ``DraftVerdict.approved`` المهيكل لا من نص الملاحظات: حكم الرفض في
   الاختبار نصّه يقول «معتمدة» بينما ``approved=False`` — فأي كود يفحص النص
   بـ``in`` يمرّ عندها بلا تحسين ويسقط الاختبار.

المهام (``@task``) لا تُنادى خارج سياق runnable — لذلك تمرّ استراتيجيتا
الخطأ عبر :func:`munassiq.workers.run_reliability_task`، وهو نفسه ما
يستعمله النوتبوك، فيبقى عقد الاستدعاء مُختبَرًا لا مرتجَلًا في خلية.
"""

import pytest
from langgraph.func import task
from pydantic import ValidationError

from munassiq import tools
from munassiq.app import DraftVerdict
from munassiq.workers import (
    fetch_external_resource,
    run_reliability_task,
    run_tool_with_llm_recovery,
)

# طلب مراسلة: هو وحده ما يسلك مسار الصياغة والمراجعة قبل الوقوف البشري.
MAIL_REQUEST = "أرسل بريدًا للمتطوعين عن تأجيل فعالية السبت"

# ملاحظات الرفض — نصّها يقول «معتمدة» عمدًا بينما approved=False، فيسقط أي
# كود يقرأ القرار من النص بدل الحقل المهيكل.
REJECTION_FEEDBACK = "المسودة معتمدة لغويًا لكنها بلا خاتمة — أضف خاتمة وتوقيعًا."

FIRST_DRAFT = "مسودة أولى بلا خاتمة."
IMPROVED_DRAFT = "مسودة محسّنة: الفعالية مؤجلة، وتقبلوا تحياتنا."


def _reset_and_build(tmp_path):
    """يصفّر الذاكرة إلى ملف مؤقت ثم يبني الـapp فوقها.

    التصفير **قبل** البناء: الـapp يلتقط الـcheckpointer والـstore لحظة
    بنائه (النمط نفسه المستقر في :mod:`test_memory` و:mod:`test_hitl`).
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


def _stub_gate_tasks(monkeypatch):
    """يستبدل مهام ما قبل التفريع بثوابت — بلا شبكة، ومسارها ليس محلَّ الفحص.

    الذاكرة والتصنيف مفحوصان في شرائحهما؛ ما نفحصه هنا ما يقع **بعد** قرار
    الوقوف: حلقة المراجعة ثم الـinterrupt.
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
        return tools.TriageDecision(
            worker="correspondence",
            needs_human_approval=True,
            summary="إرسال بريد للمتطوعين عن تأجيل فعالية السبت",
        )

    for stub in (load_memories, detect_and_store_memory, classify_request):
        monkeypatch.setattr(app_module, stub.__name__, stub)


def test_retry_and_llm_recoverable():
    """استراتيجيتا الخطأ معًا: العابر يُلتقط بالتكرار، وخطأ الأداة يُصحَّح بالنموذج.

    اختبارٌ واحد لأنهما وجهان لسؤال الروبرك نفسه («استراتيجيتان في كود
    يعمل»)، وكلٌّ منهما بعدّاده الخاص فلا يستر نجاحُ أحدهما فشلَ الآخر.
    """
    # ---- الاستراتيجية 1: العابر Transient ----
    attempts = {"count": 0}

    def flaky_fetch(resource: str) -> str:
        """يفشل مرتين بانقطاع شبكة ثم ينجح — مورد خارجي هشّ مفتعل."""
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ConnectionError("انقطاع مفتعل في المورد الخارجي")
        return f"محتوى {resource}"

    value = run_reliability_task(
        fetch_external_resource, "قائمة المتطوعين", fetcher=flaky_fetch
    )

    assert attempts["count"] == 3, (
        "عدد المحاولات ليس ثلاثًا — RetryPolicy لم يُطبَّق فعلًا على المهمة؛ "
        f"ما جرى: {attempts['count']} محاولة"
    )
    assert "قائمة المتطوعين" in value, (
        f"الناتج لا يشتق من المورد المطلوب بعد نجاح المحاولة الثالثة: {value!r}"
    )

    # ---- الاستراتيجية 2: LLM-recoverable ----
    seen_messages: list[list[dict]] = []
    model_calls = {"count": 0}

    def strict_tool(day: str) -> str:
        """أداة لا تقبل إلا يومًا من قائمة مغلقة — ورسالة خطئها تُعلّم المصحِّح."""
        allowed = ("السبت", "الأحد")
        if day not in allowed:
            raise ValueError(f"اليوم «{day}» غير مقبول؛ المقبول: {', '.join(allowed)}")
        return f"سُجّل يوم {day}."

    def two_step_model(messages: list[dict]) -> str:
        """بديل النموذج: مدخل فاسد أولًا، ثم مصحَّح بعد أن يرى نص الخطأ."""
        seen_messages.append(list(messages))
        model_calls["count"] += 1
        return "يوم_غير_موجود" if model_calls["count"] == 1 else "السبت"

    outcome = run_reliability_task(
        run_tool_with_llm_recovery,
        "سجّل الفعالية يوم السبت",
        tool=strict_tool,
        model=two_step_model,
    )

    assert outcome["result"] == "سُجّل يوم السبت.", (
        f"النداء الثاني لم ينجح بمدخل مصحَّح — ما عاد: {outcome!r}"
    )
    assert outcome["attempts"] == 2, (
        f"عدد محاولات الأداة ليس اثنتين: {outcome['attempts']}"
    )
    assert model_calls["count"] == 2, (
        f"النموذج لم يُستدعَ مرتين (فشل ثم تصحيح): {model_calls['count']}"
    )

    # الرسالة التصحيحية: نص الخطأ نفسه لا إشارة عامة إلى وقوع خطأ.
    correction_text = " ".join(
        str(message.get("content", "")) for message in seen_messages[1]
    )
    assert "يوم_غير_موجود" in correction_text, (
        "المدخل الفاسد لم يعد إلى النموذج في رسالة التصحيح — لن يعرف ما يصحّح؛ "
        f"ما وصله: {correction_text!r}"
    )
    assert "غير مقبول" in correction_text, (
        "نص خطأ الأداة لم يصل رسالة التصحيح — التصحيح تخمينٌ لا تعلّم؛ "
        f"ما وصله: {correction_text!r}"
    )
    assert "ValueError" in correction_text, (
        f"نوع الخطأ غائب عن رسالة التصحيح: {correction_text!r}"
    )
    assert "Traceback" not in correction_text, (
        "traceback خام تسرّب إلى رسالة التصحيح — قرار أمن: النوع والرسالة فقط"
    )


def test_permanent_failure_propagates_after_retries():
    """الوجه الآخر: الفشل الدائم ينتشر بعد استنفاد المحاولات الثلاث.

    بلا هذا التأكيد قد تكون السياسة ابتلاعًا صامتًا للأخطاء لا تكرارًا محدودًا.
    """
    attempts = {"count": 0}

    def always_down(resource: str) -> str:
        attempts["count"] += 1
        raise ConnectionError("المورد الخارجي ساقط دائمًا")

    with pytest.raises(ConnectionError):
        run_reliability_task(
            fetch_external_resource, "قائمة المتطوعين", fetcher=always_down
        )

    assert attempts["count"] == 3, (
        "المحاولات لم تُستنفد ثلاثًا قبل انتشار الاستثناء: " f"{attempts['count']}"
    )


def test_draft_verdict_is_structured_and_bounded():
    """حكم المراجع نموذج Pydantic بحدود فعلية — لا نص يُفتَّش فيه بـ``in``."""
    verdict = DraftVerdict(score=9, approved=True, feedback="")
    assert verdict.approved is True, "الحقل المهيكل approved لا يحمل قرار الاعتماد"
    assert verdict.score == 9, "الدرجة لم تُحفظ كما مُرّرت"

    for bad_score in (0, 11):
        with pytest.raises(ValidationError):
            DraftVerdict(score=bad_score, approved=False, feedback="خارج المدى")


def test_evaluator_optimizer_loop_runs_before_interrupt(tmp_path, monkeypatch, outbox):
    """نمط Evaluator-Optimizer: رفضٌ ثم تحسينٌ ثم اعتماد — كله قبل الوقوف.

    المهام النموذجية الثلاث (صياغة، تقييم، تحسين) مستبدَلة بثوابت، والباقي
    كودٌ حقيقي: الحلقة، وترتيبها قبل ``interrupt``، وما يصل حمولة الوقوف.
    """
    from munassiq import app as app_module

    app = _reset_and_build(tmp_path)
    _stub_gate_tasks(monkeypatch)

    evaluations: list[str] = []
    improvements: list[dict] = []

    @task
    def compose_draft(request: str, memories: list[str]) -> str:
        return FIRST_DRAFT

    @task
    def evaluate_draft(request: str, draft: str) -> DraftVerdict:
        evaluations.append(draft)
        # الجولة الأولى رفض، والثانية اعتماد — أقصر حلقة تُظهر النمط كاملًا.
        if len(evaluations) == 1:
            return DraftVerdict(score=4, approved=False, feedback=REJECTION_FEEDBACK)
        return DraftVerdict(score=9, approved=True, feedback="")

    @task
    def improve_draft(
        request: str, draft: str, feedback: str, memories: list[str]
    ) -> str:
        improvements.append({"draft": draft, "feedback": feedback})
        return IMPROVED_DRAFT

    for stub in (compose_draft, evaluate_draft, improve_draft):
        monkeypatch.setattr(app_module, stub.__name__, stub)

    paused = app.invoke(
        {"request": MAIL_REQUEST, "user_id": "member-007"},
        {"configurable": {"thread_id": "eval-opt-offline"}},
    )

    assert "__interrupt__" in paused, (
        f"لم يقف التنفيذ على interrupt بعد حلقة المراجعة — ما عاد: {sorted(paused)}"
    )

    assert len(improvements) == 1, (
        "التحسين لم يُستدعَ مرة واحدة بالضبط — الحلقة إما لم تدر أو تجاوزت "
        f"حدّها؛ عدد الاستدعاءات: {len(improvements)}"
    )
    assert improvements[0]["feedback"] == REJECTION_FEEDBACK, (
        "ملاحظات المقيّم لم تصل نص التحسين — التحسين حينها إعادةُ صياغةٍ عمياء؛ "
        f"ما وصل: {improvements[0]['feedback']!r}"
    )
    assert improvements[0]["draft"] == FIRST_DRAFT, (
        f"المسودة المرفوضة لم تُمرَّر إلى التحسين: {improvements[0]['draft']!r}"
    )

    assert len(evaluations) == 2, (
        f"عدد جولات التقييم ليس اثنتين: {len(evaluations)} — {evaluations}"
    )
    assert evaluations[1] == IMPROVED_DRAFT, (
        "الجولة الثانية لم تقيّم المسودة المحسّنة — الحلقة لا تُغذّي نفسها"
    )

    payload = paused["__interrupt__"][0].value
    assert payload.get("draft") == IMPROVED_DRAFT, (
        "ما عُرض على البشري ليس المسودة المعتمَدة من المقيّم — الحلقة وقعت بعد "
        f"الوقوف أو أُهمل ناتجها؛ ما عُرض: {payload.get('draft')!r}"
    )
    assert not list(outbox.glob("sent-*.txt")), (
        "كُتب ملف إرسال قبل موافقة البشري — حلقة المراجعة لا تُغني عن الوقوف"
    )


def test_evaluator_optimizer_stops_at_round_cap(tmp_path, monkeypatch, outbox):
    """مقيّم يرفض دائمًا لا يُدير الحلقة إلى الأبد — سقفٌ صلب بجولتين."""
    from munassiq import app as app_module

    app = _reset_and_build(tmp_path)
    _stub_gate_tasks(monkeypatch)

    counters = {"evaluate": 0, "improve": 0}

    @task
    def compose_draft(request: str, memories: list[str]) -> str:
        return FIRST_DRAFT

    @task
    def evaluate_draft(request: str, draft: str) -> DraftVerdict:
        counters["evaluate"] += 1
        return DraftVerdict(score=3, approved=False, feedback=REJECTION_FEEDBACK)

    @task
    def improve_draft(
        request: str, draft: str, feedback: str, memories: list[str]
    ) -> str:
        counters["improve"] += 1
        return f"{IMPROVED_DRAFT} ({counters['improve']})"

    for stub in (compose_draft, evaluate_draft, improve_draft):
        monkeypatch.setattr(app_module, stub.__name__, stub)

    paused = app.invoke(
        {"request": MAIL_REQUEST, "user_id": "member-007"},
        {"configurable": {"thread_id": "eval-opt-cap"}},
    )

    assert counters["evaluate"] == 2, (
        f"سقف جولات التقييم انكسر: {counters['evaluate']} جولة"
    )
    assert counters["improve"] == 1, (
        f"سقف جولات التحسين انكسر: {counters['improve']} جولة"
    )
    assert "__interrupt__" in paused, (
        "الرحلة لم تصل الوقوف بعد استنفاد الجولات — المسودة غير المعتمَدة يجب "
        "أن تُعرض على البشري لا أن تُسقط الرحلة"
    )
    assert paused["__interrupt__"][0].value.get("draft", "").strip(), (
        "حمولة الوقوف بلا مسودة بعد استنفاد الجولات — البشري يراجع فراغًا"
    )


@pytest.mark.api
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=2, reruns_delay=30)
def test_llm_recovery_with_real_model():
    """التصحيح بنموذج حقيقي: الأداة ترفض المدخل، والنموذج يقرأ الخطأ فيصحح.

    قائمة المقبول **غائبة** عن التعليمات عمدًا: السبيل الوحيد إلى المدخل
    الصحيح هو نص الخطأ العائد من الأداة، فلو مرّ الاختبار فقد ثبت أن الرسالة
    التصحيحية هي ما أنقذ النداء لا معرفة النموذج المسبقة.
    """
    allowed = ("SAT-2026-08-22", "SUN-2026-08-23")

    def strict_tool(slot: str) -> str:
        if slot not in allowed:
            raise ValueError(
                f"الرمز «{slot}» غير موجود؛ الرموز المتاحة: {', '.join(allowed)}"
            )
        return f"حُجز الموعد {slot}."

    outcome = run_reliability_task(
        run_tool_with_llm_recovery,
        "احجز موعد فعالية السبت. أخرج رمز الموعد وحده بلا أي شرح.",
        tool=strict_tool,
    )

    assert outcome["result"].startswith("حُجز الموعد"), (
        f"النموذج لم يصحّح مدخله بعد رسالة الخطأ: {outcome!r}"
    )
    assert outcome["attempts"] <= 2, f"تجاوز سقف المحاولتين: {outcome['attempts']}"
