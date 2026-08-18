"""اختبار الشريحة 5 — الذاكرة قصيرة وطويلة المدى حول الـentrypoint الوظيفي.

المحور الذي يفحصه الروبرك هنا ليس «هل بدا النموذج متذكِّرًا؟» بل **أين
سكنت الحقيقة**. رسائل متراكمة في thread واحد ليست ذاكرة طويلة المدى — هي
سياق محادثة. الدليل الوحيد المقبول أن تُكتب الحقيقة في مخزنٍ خارج الـthread،
ثم تُقرأ من thread آخر لا يشترك مع الأول في أي رسالة.

لذلك الفحص الصلب هنا على **الـStore مباشرة** لا على نص النموذج: نؤكد أن
`store.search(("memories", user_id))` يحوي الحقيقة فعلًا. أما نص الرد فلا
نؤكد عليه حرفيًا (قرار «ما لا يُختبر»: صياغة النموذج غير حتمية) — نؤكد أن
الذكريات المحقونة وصلت إلى الرحلة عبر `memories_used`.

وتقسيم الاختبارات مقصود: اختبار الـsingleton بلا شبكة أصلًا، ليبقى دليلًا
قائمًا حتى لو سقطت الشبكة أو نفدت حصة الـAPI.
"""

import pytest


def _reset_and_build(tmp_path):
    """يعيد بناء الذاكرة على ملف مؤقت ثم يبني الـapp فوقها.

    الترتيب إلزامي: التصفير **قبل** استيراد ``munassiq.app``، فالـapp يلتقط
    الـcheckpointer والـstore من الـsingleton لحظة بنائه. عكسُ الترتيب يبني
    الـapp على قاعدة المشروع الدائمة فيتضخم الملف عبر التشغيلات.
    """
    from munassiq.memory import reset_memory_for_tests

    checkpointer, store = reset_memory_for_tests(tmp_path)

    from munassiq.app import build_app

    return build_app(), checkpointer, store


def test_build_memory_is_singleton(tmp_path):
    """بلا شبكة: نداءان لـ``build_memory`` يعيدان الكائنين نفسيهما."""
    from munassiq import memory

    memory.reset_memory_for_tests(tmp_path)

    checkpointer_a, store_a = memory.build_memory()
    checkpointer_b, store_b = memory.build_memory()

    assert checkpointer_a is checkpointer_b, (
        "build_memory بنت checkpointer جديدًا في النداء الثاني — "
        "اتصالان على الملف نفسه يعنيان حالةً منقسمة"
    )
    assert store_a is store_b, "build_memory بنت Store جديدًا في النداء الثاني"

    assert list(tmp_path.glob("*.sqlite")), (
        f"لم يُنشأ أي ملف sqlite في المسار المؤقت {tmp_path} — "
        "التصفير لم يُحوِّل الذاكرة عن قاعدة المشروع الدائمة"
    )


@pytest.mark.api
@pytest.mark.flaky(reruns=2, reruns_delay=30)
def test_cross_thread_store(tmp_path):
    """حقيقة تُكتب في thread وتُقرأ في آخر — الفحص على الـStore نفسه."""
    app, _checkpointer, store = _reset_and_build(tmp_path)

    app.invoke(
        {
            "request": "تذكّر أن اليوم المفضل لاجتماعاتنا هو الخميس",
            "user_id": "member-001",
        },
        {"configurable": {"thread_id": "thread-1"}},
    )

    items = store.search(("memories", "member-001"))
    assert items, (
        "الـStore فارغ بعد طلبٍ صريح بالتذكّر — الحقيقة لم تُكتب خارج الـthread"
    )
    assert any("الخميس" in str(item.value) for item in items), (
        "لا عنصر في الـStore يحمل الحقيقة المطلوبة — "
        f"ما وُجد: {[item.value for item in items]}"
    )

    result = app.invoke(
        {"request": "ما اليوم المفضل لاجتماعاتنا؟", "user_id": "member-001"},
        {"configurable": {"thread_id": "thread-2"}},
    )

    assert isinstance(result, dict), f"الـentrypoint أعاد {type(result).__name__} لا dict"
    assert result.get("reply", "").strip(), "الرد فارغ في الـthread الثاني"
    assert "الخميس" in " ".join(result.get("memories_used", [])), (
        "الذكريات لم تُحقن في الـthread الثاني — الحقن ليس حتميًا؛ "
        f"ما حُقن: {result.get('memories_used')}"
    )


@pytest.mark.api
@pytest.mark.flaky(reruns=2, reruns_delay=30)
def test_same_thread_keeps_short_term_context(tmp_path):
    """قِصر المدى: نداءان بنفس thread_id، والثاني يجد أثر الأول في الـcheckpointer."""
    app, _checkpointer, _store = _reset_and_build(tmp_path)

    config = {"configurable": {"thread_id": "thread-short"}}

    first = app.invoke(
        {"request": "ما المواعيد المسجّلة في التقويم؟", "user_id": "member-002"},
        config,
    )
    assert first["turn"] == 1, f"الدور الأول لم يُحسب دورًا أولًا: {first.get('turn')}"

    second = app.invoke(
        {"request": "وهل هناك جديد بعد ذلك؟", "user_id": "member-002"},
        config,
    )
    assert second["turn"] == 2, (
        "الدور الثاني لم يجد سياق الأول — الـcheckpointer لا يحمل الحالة عبر "
        f"النداءين: {second.get('turn')}"
    )

    snapshot = app.get_state(config)
    assert snapshot.values.get("turn") == 2, (
        f"لقطة الحالة لا تعكس دورين على الـthread نفسه: {snapshot.values}"
    )
