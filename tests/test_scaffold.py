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

    # 2) get_llm() يبني عميل المزود المضبوط بالمواصفات الموحدة — بناء الكائن
    # لا يتصل بالشبكة. العقد صار متعدد المزودين (توجيه مالك، 19 أغسطس):
    # النموذج من خريطة DEFAULT_MODELS للمزود الفعّال (أو MUNASSIQ_MODEL)،
    # والحرارة شبه صفرية (بعض المكتبات تستبدل 0 الحرفي بقيمة ضئيلة).
    from munassiq.config import DEFAULT_MODELS, DEFAULT_PROVIDER, get_llm

    provider = os.environ.get("MUNASSIQ_PROVIDER", DEFAULT_PROVIDER)
    expected_model = os.environ.get("MUNASSIQ_MODEL") or DEFAULT_MODELS[provider]
    llm = get_llm()
    actual_model = getattr(llm, "model_name", None) or getattr(llm, "model", None)
    assert actual_model.endswith(expected_model.split("/")[-1]) or actual_model == expected_model
    assert (llm.temperature or 0) < 1e-6
    assert llm.max_retries == 2

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
