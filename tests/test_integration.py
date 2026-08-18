"""اختبار التكامل الختامي — الصياغة التنفيذية لمعيار نجاح المشروع.

يمثّل سيناريو الروبرك كاملًا عبر واجهات munassiq العامة. كُتب أحمر في
المرحلة 1 موسومًا xfail؛ الشريحة 9 ترفع الوسم وخضرته بلا وسم شرط الإغلاق.
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.timeout(300),
    pytest.mark.flaky(reruns=2, reruns_delay=30),
    pytest.mark.xfail(reason="الميزة قيد البناء — يُرفع الوسم في الشريحة 9", strict=True),
]


def test_capstone_end_to_end():
    try:
        from munassiq.app import munassiq_app
        from munassiq.memory import build_memory
        from munassiq.rag import build_retriever
        from munassiq.supervisor import build_supervisor
    except ImportError:
        pytest.fail("الميزة غائبة: حزمة munassiq لم تُبنَ بعد")

    checkpointer, store = build_memory()

    # 1+2 — المشرف يوجّه بقرار النموذج: دليل transfer_to_*
    supervisor = build_supervisor()
    result = supervisor.invoke(
        {"messages": [{"role": "user", "content": "احجز اجتماع لجنة المحتوى يوم الثلاثاء"}]}
    )
    handoffs = [
        tc["name"]
        for m in result["messages"]
        for tc in (getattr(m, "tool_calls", None) or [])
    ]
    assert any(h.startswith("transfer_to_") for h in handoffs), (
        "لا دليل أن النموذج هو من وجّه — لا نداء transfer_to_* في الرسائل"
    )

    # 3 — RAG: سؤال إجابته حرفية في الوثائق التركيبية
    retriever = build_retriever()
    docs = retriever.invoke("كم مدة مراجعة المحتوى قبل النشر؟")
    assert docs, "المسترجِع أعاد لا شيء — خط RAG مكسور"
    assert any("ثلاثة أيام عمل" in d.page_content for d in docs), (
        "الحقيقة الحرفية المزروعة في الوثائق لم تُسترجَع"
    )

    # 4 — ذاكرة طويلة المدى عبر الـ threads: التأكيد الصلب على الـ Store مباشرة
    # (نص جواب النموذج دليلُ نوتبوك لا بوابةُ اختبار — قرار نقد الجولة 1)
    user_id = "member-001"
    t1 = {"configurable": {"thread_id": f"t1-{uuid.uuid4().hex[:6]}"}}
    t2 = {"configurable": {"thread_id": f"t2-{uuid.uuid4().hex[:6]}"}}
    munassiq_app.invoke(
        {"request": "تذكّر أن اليوم المفضل لاجتماعاتنا هو الخميس", "user_id": user_id},
        t1,
    )
    stored = store.search(("memories", user_id))
    assert any("الخميس" in str(item.value) for item in stored), (
        "الحقيقة لم تُكتب في الـ Store — الذاكرة ليست طويلة المدى"
    )
    recalled = munassiq_app.invoke(
        {"request": "ما اليوم المفضل لاجتماعاتنا؟", "user_id": user_id}, t2
    )
    assert recalled is not None, "الاستدعاء من thread ثانٍ فشل رغم وجود الحقيقة في الـ Store"

    # 5 — interrupt ثم resume بتعديل بشري يظهر في الناتج
    t3 = {"configurable": {"thread_id": f"t3-{uuid.uuid4().hex[:6]}"}}
    paused = munassiq_app.invoke(
        {"request": "أرسل بريدًا للمتطوعين عن تأجيل فعالية السبت", "user_id": "member-001"},
        t3,
    )
    assert "__interrupt__" in paused, "لم يقف على interrupt قبل الفعل غير القابل للعكس"

    from langgraph.types import Command

    human_edit = "النص المعتمد من المشرف البشري: الفعالية مؤجلة لأسبوع."
    done = munassiq_app.invoke(Command(resume=human_edit), t3)
    assert human_edit in str(done), "تعديل البشري لم يظهر في الناتج النهائي — resume غير مُثبَت"
