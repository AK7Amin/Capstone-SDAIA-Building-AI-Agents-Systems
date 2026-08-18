"""اختبار الشريحة 1 — السقالة: البيئة، ChatGroq، وسياج الوثائق التركيبية."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_env_and_corpus_guarded():
    # 1) البيئة محمّلة (المفتاحان غير فارغين) — دون طباعة أي قيمة.
    assert os.environ.get("GROQ_API_KEY"), "GROQ_API_KEY غائب من البيئة بعد تحميل config"
    assert os.environ.get(
        "LANGSMITH_API_KEY"
    ), "LANGSMITH_API_KEY غائب من البيئة بعد تحميل config"
    assert os.environ.get("LANGCHAIN_TRACING_V2"), "LANGCHAIN_TRACING_V2 غائب من البيئة"
    assert os.environ.get("LANGCHAIN_PROJECT"), "LANGCHAIN_PROJECT غائب من البيئة"

    # 2) get_llm() يبني ChatGroq بالمواصفات المطلوبة — بناء الكائن لا يتصل بالشبكة.
    from langchain_groq import ChatGroq

    from munassiq.config import get_llm

    llm = get_llm()
    assert isinstance(llm, ChatGroq)
    assert llm.model_name == "openai/gpt-oss-120b"
    # ChatGroq يستبدل 0 الحرفي داخليًا بقيمة شبه صفرية (Groq يرفض 0 تمامًا) —
    # القيمة المُمرَّرة للبانِي هي 0، والتحقق هنا من قرب الناتج من الصفر.
    assert llm.temperature < 1e-6
    assert llm.max_retries == 2
    assert llm.request_timeout == 60

    # 3) وثائق data/corpus الثلاث موجودة وتحرس الحقائق الحرفية المزروعة فيها.
    corpus_dir = PROJECT_ROOT / "data" / "corpus"
    planted_facts = {
        "سياسة-النشر.md": "ثلاثة أيام عمل",
        "دليل-المتطوعين.md": "أربع ساعات شهريًا",
        "إجراءات-الفعاليات.md": "أربع وعشرين ساعة",
    }
    for filename, needle in planted_facts.items():
        path = corpus_dir / filename
        assert path.is_file(), f"وثيقة الكوربس غائبة: {filename}"
        content = path.read_text(encoding="utf-8")
        assert needle in content, f"الحقيقة المزروعة حرفيًا غائبة في {filename}: {needle!r}"

    # 4) .gitignore يحرس مسارات الأسرار والمخازن المحلية المولَّدة.
    gitignore_content = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    for guarded_line in (".env", "data/chroma/", "data/outbox/"):
        assert guarded_line in gitignore_content, f".gitignore لا يحوي السطر: {guarded_line}"
