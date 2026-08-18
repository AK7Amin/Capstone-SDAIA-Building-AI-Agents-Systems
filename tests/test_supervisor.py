"""اختبار الشريحة 3 — العمّال والمشرف.

المحور الذي يفحصه الروبرك: **النموذج** هو من يوجّه، لا سلسلة `if` مخبّأة.
الدليل نداء `transfer_to_<worker>` في الرسائل الناتجة — وهو ما لا يظهر إلا
حين يقرّر المشرف بنفسه أن يسلّم الطلب لعامل.

ودليلٌ ثانٍ لا يقلّ أهمية: أن العامل **فعل شغلًا حقيقيًا** لا صاغ جملة
جميلة. لذلك نؤكد على حالة `tools.CALENDAR` نفسها بعد الرحلة، فالحدث لا
يدخلها إلا عبر نداء أداة فعلي.
"""

import pytest

from munassiq import tools


@pytest.fixture(autouse=True)
def _clean_calendar():
    """التقويم حالة على مستوى الموديول — يُفرَّغ قبل كل اختبار وبعده."""
    tools.CALENDAR.clear()
    yield
    tools.CALENDAR.clear()


def _tool_call_names(result) -> list[str]:
    """يجمع أسماء كل نداءات الأدوات من كل رسائل الرحلة."""
    return [
        tool_call["name"]
        for message in result["messages"]
        for tool_call in (getattr(message, "tool_calls", None) or [])
    ]


@pytest.mark.api
@pytest.mark.flaky(reruns=2, reruns_delay=30)
def test_llm_routes_via_transfer():
    from munassiq.supervisor import build_supervisor

    result = build_supervisor().invoke(
        {"messages": [{"role": "user", "content": "احجز اجتماع لجنة المحتوى يوم الثلاثاء"}]}
    )

    names = _tool_call_names(result)
    assert any(name.startswith("transfer_to_calendar_agent") for name in names), (
        "لا دليل أن النموذج هو من وجّه إلى عامل التقويم — "
        f"نداءات الأدوات التي ظهرت: {names}"
    )

    assert tools.CALENDAR, (
        "التقويم فارغ بعد الرحلة — العامل صاغ جوابًا ولم ينادِ أداةً فعلًا"
    )
    assert any(
        "المحتوى" in event["title"] and "الثلاثاء" in event["day"]
        for event in tools.CALENDAR
    ), (
        "الحدث المسجّل لا يطابق عنوان/يوم الطلب — الأداة لم تستعمل معاملات "
        f"الطلب: {tools.CALENDAR}"
    )


def test_supervisor_builds_and_forbids_direct_answers():
    """بناءٌ بلا شبكة + التأكد أن prompt المشرف يمنع الإجابة المباشرة."""
    from munassiq import supervisor as supervisor_module

    graph = supervisor_module.build_supervisor(checkpointer=None)
    assert graph is not None, "build_supervisor أعادت None بدل غراف مُصرَّف"
    assert hasattr(graph, "invoke"), "الناتج ليس غرافًا مُصرَّفًا — ينقصه .invoke"

    prompt = getattr(supervisor_module, "SUPERVISOR_PROMPT", None)
    text = prompt if isinstance(prompt, str) else (supervisor_module.__doc__ or "")
    assert "لا تجب بنفسك" in text, (
        "prompt المشرف لا يمنع الإجابة المباشرة نصًّا — المشرف قد يجيب بدل "
        "أن يفوّض"
    )


def test_workers_carry_names_the_supervisor_needs():
    """اسم كل عامل إلزامي — منه يشتقّ المشرف أداة transfer_to_<name>."""
    from munassiq.workers import build_calendar_agent, build_correspondence_agent

    assert build_calendar_agent().name == "calendar_agent"
    assert build_correspondence_agent().name == "correspondence_agent"
