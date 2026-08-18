"""اختبار الشريحة 2 — الأدوات والمخرج المهيكل.

المحور الذي يفحصه الروبرك: الأداة التي تتجاهل معاملاتها ليست نداء أداة. لذلك
كل أداة هنا تُستدعى مرتين بمعاملات مختلفة، والتأكيد أن الناتجين يختلفان فعلًا
لا أن الأداة «لم ترمِ استثناءً».

كتابة صندوق الصادر تُحوَّل إلى ``tmp_path`` عبر monkeypatch على
``tools.OUTBOX_DIR`` — لا يتراكم أي مخلَّف في ``data/outbox`` الحقيقي.
"""

from pathlib import Path

import pytest

from munassiq import tools

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve(returned: str) -> Path:
    """يحوّل المسار الذي أعادته الأداة إلى مسار قابل للقراءة."""
    path = Path(returned)
    return path if path.is_absolute() else PROJECT_ROOT / path


@pytest.fixture(autouse=True)
def _clean_calendar():
    """التقويم حالة على مستوى الموديول — يُفرَّغ قبل كل اختبار وبعده."""
    tools.CALENDAR.clear()
    yield
    tools.CALENDAR.clear()


@pytest.fixture
def outbox(tmp_path, monkeypatch):
    """يحوّل صندوق الصادر إلى مجلد مؤقت يمحوه pytest تلقائيًا."""
    target = tmp_path / "outbox"
    monkeypatch.setattr(tools, "OUTBOX_DIR", target)
    return target


def test_tools_use_their_args(outbox):
    # 1) التقويم: الأداة تستعمل العنوان واليوم الممرَّرين لها
    first = tools.create_event.invoke({"title": "اجتماع تجريبي", "day": "الثلاثاء"})
    assert "اجتماع تجريبي" in first, "رسالة create_event لا تذكر العنوان الممرَّر"
    assert "الثلاثاء" in first, "رسالة create_event لا تذكر اليوم الممرَّر"
    assert len(tools.CALENDAR) == 1, "الحدث لم يُضَف إلى حالة التقويم"
    assert tools.CALENDAR[0]["title"] == "اجتماع تجريبي"
    assert tools.CALENDAR[0]["day"] == "الثلاثاء"

    listed = tools.list_events.invoke({})
    assert "اجتماع تجريبي" in listed and "الثلاثاء" in listed, (
        "list_events لا يذكر الحدث المضاف"
    )

    # استدعاء ثانٍ بمعاملات مختلفة ⇒ ناتج مختلف، وإلا فالأداة تتجاهل معاملاتها
    second = tools.create_event.invoke({"title": "ورشة المتطوعين", "day": "الأحد"})
    assert second != first, "create_event أعادت الناتج نفسه لمعاملات مختلفة"
    assert "ورشة المتطوعين" in second and "الأحد" in second
    assert len(tools.CALENDAR) == 2
    listed_again = tools.list_events.invoke({})
    assert listed_again != listed, "list_events لا يعكس تغيّر حالة التقويم"

    # 2) صندوق الصادر: المسودة ملف فعلي محتواه يتضمن المعاملات الثلاثة
    draft_one = tools.save_email_draft.invoke(
        {
            "to": "volunteers@example.org",
            "subject": "تأجيل فعالية السبت",
            "body": "الفعالية مؤجلة أسبوعًا واحدًا.",
        }
    )
    path_one = _resolve(draft_one)
    assert path_one.is_file(), f"save_email_draft لم تنشئ ملفًا فعليًا: {draft_one}"
    content_one = path_one.read_bytes().decode("utf-8")
    for needle in (
        "volunteers@example.org",
        "تأجيل فعالية السبت",
        "الفعالية مؤجلة أسبوعًا واحدًا.",
    ):
        assert needle in content_one, f"محتوى المسودة لا يتضمن المعامل: {needle!r}"

    draft_two = tools.save_email_draft.invoke(
        {
            "to": "board@example.org",
            "subject": "دعوة اجتماع اللجنة",
            "body": "نلقاكم يوم الخميس بإذن الله.",
        }
    )
    assert draft_two != draft_one, "مسودتان بمعاملات مختلفة كتبتا المسار نفسه"
    content_two = _resolve(draft_two).read_bytes().decode("utf-8")
    assert content_two != content_one, (
        "save_email_draft أنتجت المحتوى نفسه لمعاملات مختلفة"
    )
    assert "board@example.org" in content_two

    # 3) الإرسال المعتمَد: النص يُكتب حرفيًا كما وصل، بلا تمريره على أي نموذج
    verbatim = "نص حرفي ١٢٣"
    sent_one = tools.send_approved_email(verbatim)
    sent_path_one = _resolve(sent_one)
    assert sent_path_one.is_file(), "send_approved_email لم تنشئ ملفًا"
    assert sent_path_one.name.startswith("sent-"), (
        f"اسم ملف الإرسال لا يبدأ بـ sent-: {sent_path_one.name}"
    )
    assert sent_path_one.read_bytes().decode("utf-8") == verbatim, (
        "محتوى الملف لا يساوي النص الممرَّر حرفيًا"
    )

    other = "نص آخر ٤٥٦"
    sent_two = tools.send_approved_email(other)
    assert sent_two != sent_one, "إرسالان بنصين مختلفين كتبا المسار نفسه"
    assert _resolve(sent_two).read_bytes().decode("utf-8") == other


def test_outbox_default_is_inside_project_data():
    """المسار الافتراضي داخل data/outbox المُتجاهَل في git — بلا كتابة أي ملف.

    لا يستعمل تثبيتة ``outbox``، فالقيمة المفحوصة هي الافتراضية لا المحوَّلة.
    """
    assert tools.OUTBOX_DIR == PROJECT_ROOT / "data" / "outbox", (
        f"صندوق الصادر الافتراضي في مكان غير متوقع: {tools.OUTBOX_DIR}"
    )


def test_triage_decision_model_shape():
    """شكل نموذج التصنيف — بلا نداء شبكة."""
    decision = tools.TriageDecision(
        worker="calendar", needs_human_approval=False, summary="حجز اجتماع"
    )
    assert decision.worker == "calendar"
    assert decision.needs_human_approval is False
    assert decision.summary == "حجز اجتماع"

    with pytest.raises(Exception):
        tools.TriageDecision(
            worker="not-a-worker", needs_human_approval=False, summary="x"
        )


@pytest.mark.api
@pytest.mark.flaky(reruns=2, reruns_delay=30)
def test_triage_routes_booking_request_to_calendar():
    decision = tools.triage("احجز اجتماعًا يوم الأحد")
    assert isinstance(decision, tools.TriageDecision), (
        f"triage أعادت نوعًا غير TriageDecision: {type(decision).__name__}"
    )
    assert decision.worker == "calendar", (
        f"طلب حجز وُجّه إلى عامل غير التقويم: {decision.worker}"
    )
    assert isinstance(decision.needs_human_approval, bool)
    assert decision.summary, "الملخّص فارغ"
