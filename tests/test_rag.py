"""اختبار الشريحة 4 — خط RAG وعامل المعرفة.

المحور الذي يفحصه الروبرك هنا: **الاسترجاع يعيد الحقيقة الحرفية المزروعة**
في الوثائق التركيبية، لا جوابًا معقولًا من عند النموذج. لذلك التأكيد على
`page_content` نفسه — «ثلاثة أيام عمل» — لا على نص جواب.

التضمين محلي (fastembed) فلا يحتاج هذا الملف مفتاح شبكة إلا في اختبار
العامل الموسوم `api`. والإحماء يسبق كل تأكيد: أول نداء تضمين قد ينزّل
الموديل، وهو زمن تحميل لا زمن استرجاع — لا يُحسب على الاسترجاع ولا يُقاس به.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WRITEUP_PATH = PROJECT_ROOT / "docs" / "WRITEUP-DRAFT.md"

pytestmark = pytest.mark.timeout(300)


@pytest.fixture(scope="module", autouse=True)
def _warm_embeddings():
    """إحماء الكاش قبل أي تأكيد — تحميل الموديل ليس جزءًا مما نقيسه."""
    from munassiq.rag import warm_up_embeddings

    warm_up_embeddings()


def test_verbatim_fact_retrieved():
    """الحقيقة الحرفية «ثلاثة أيام عمل» في أول نتيجتين لسؤال المدة."""
    from munassiq.rag import build_retriever

    question = "كم مدة مراجعة المحتوى قبل النشر؟"
    docs = build_retriever().invoke(question)

    assert docs, "المسترجِع أعاد لا شيء — خط RAG مكسور"
    top_two = docs[:2]
    assert any("ثلاثة أيام عمل" in doc.page_content for doc in top_two), (
        "الحقيقة الحرفية المزروعة ليست في أول نتيجتين — "
        f"الترتيب المسترجَع: {[doc.page_content[:60] for doc in docs]}"
    )
    assert all(doc.metadata.get("source") for doc in docs), (
        "مقطع بلا مصدر في الـmetadata — الجواب لن يقدر أن يشير إلى وثيقته"
    )


def test_rebuild_does_not_duplicate_index():
    """بناءان متتاليان لا يضاعفان الفهرس — الـcollection تُحذف وتُعاد.

    قرار نقد الجولة 1: collection ثابتة الاسم بلا حذف تتراكم عبر
    الاستدعاءات، فيصير أعلى الترتيب نُسخًا مكررة من المقطع نفسه.
    """
    from munassiq.rag import build_retriever

    question = "كم مدة مراجعة المحتوى قبل النشر؟"

    first = build_retriever()
    first_docs = first.invoke(question)
    first_count = first.vectorstore._collection.count()

    second = build_retriever()
    second_docs = second.invoke(question)
    second_count = second.vectorstore._collection.count()

    assert second_count == first_count, (
        "عدد المقاطع في الفهرس تضاعف بعد إعادة البناء — "
        f"{first_count} ثم {second_count}"
    )
    assert len(second_docs) == len(first_docs), (
        "عدد النتائج لنفس السؤال تغيّر بين بناءين — الفهرس غير مستقر"
    )
    contents = [doc.page_content for doc in second_docs]
    assert len(set(contents)) == len(contents), (
        "مقاطع مكررة في نتيجة واحدة — الفهرس فيه نسخ مضاعفة"
    )


def test_knowledge_tool_returns_passages_with_source():
    """أداة search_policies تعيد نص المقاطع ومصدرها — بلا أي نداء شبكة."""
    from munassiq.rag import build_knowledge_tool

    tool = build_knowledge_tool()
    assert tool.name == "search_policies", (
        f"اسم الأداة ليس search_policies بل {tool.name!r} — "
        "العامل يستدعيها بالاسم"
    )

    answer = tool.invoke({"query": "كم مدة مراجعة المحتوى قبل النشر؟"})
    assert "ثلاثة أيام عمل" in answer, (
        f"نص الأداة لا يحوي الحقيقة الحرفية — ما عاد: {answer[:200]!r}"
    )
    assert "سياسة-النشر" in answer, "الأداة لا تذكر مصدر المقطع"


def test_knowledge_agent_carries_its_name_and_tool():
    """اسم العامل إلزامي — منه يشتقّ المشرف transfer_to_knowledge_agent."""
    from munassiq.workers import build_knowledge_agent

    agent = build_knowledge_agent()
    assert agent.name == "knowledge_agent"


def test_supervisor_knows_the_knowledge_worker():
    """المشرف يعرف عامل المعرفة نصًّا في توجيهه — وإلا لن يفوّض إليه."""
    from munassiq import supervisor as supervisor_module

    assert "knowledge_agent" in supervisor_module.SUPERVISOR_PROMPT, (
        "prompt المشرف لا يذكر knowledge_agent — أسئلة السياسات بلا وجهة"
    )


def test_writeup_draft_justifies_the_rag_architecture():
    """مسودة الـwrite-up تقارن البدائل الثلاثة نصًّا وتبرّر الاختيار."""
    assert WRITEUP_PATH.is_file(), f"مسودة الـwrite-up غائبة: {WRITEUP_PATH}"

    text = WRITEUP_PATH.read_text(encoding="utf-8")
    for needle in ("2-Step", "Agentic", "Hybrid"):
        assert needle in text, f"المسودة لا تذكر البديل {needle!r} في المقارنة"


@pytest.mark.api
@pytest.mark.flaky(reruns=2, reruns_delay=30)
def test_knowledge_agent_answers_from_the_corpus():
    """عامل المعرفة يجيب سؤال المدة من المقاطع — تسامح في الصياغة."""
    from munassiq.workers import build_knowledge_agent

    result = build_knowledge_agent().invoke(
        {"messages": [{"role": "user", "content": "كم مدة مراجعة المحتوى قبل النشر؟"}]}
    )

    tool_names = [
        tool_call["name"]
        for message in result["messages"]
        for tool_call in (getattr(message, "tool_calls", None) or [])
    ]
    assert "search_policies" in tool_names, (
        f"العامل لم ينادِ أداة البحث أصلًا — النداءات: {tool_names}"
    )

    final = result["messages"][-1].content
    assert "ثلاثة" in final or "3" in final, (
        f"جواب العامل لا يذكر المدة الصحيحة: {final!r}"
    )
