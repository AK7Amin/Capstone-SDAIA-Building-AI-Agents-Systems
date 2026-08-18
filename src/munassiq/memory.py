"""ذاكرة «المُنسِّق» — نوعان مختلفان لا نوعٌ واحد بمقياسين.

* **قصيرة المدى**: :class:`~langgraph.checkpoint.sqlite.SqliteSaver`. حالة
  محادثةٍ واحدة، مفتاحها ``thread_id``. تُستأنف بعد إعادة التشغيل لأنها على
  القرص لا في الذاكرة.
* **طويلة المدى**: Store بفضاء أسماء ``("memories", user_id)``. لا يعرف
  الـthread أصلًا، فما يُكتب فيه في محادثة يُقرأ في محادثة أخرى. هذا هو
  الفرق الذي يسقط فيه أكثر المتقدمين: رسائل متراكمة في thread واحد ليست
  ذاكرة طويلة المدى.

**لماذا لا ``from_conn_string``**: كلا الصنفين يوفّرها مديرَ سياق
(``@contextmanager``) يغلق الاتصال عند الخروج من ``with``. استعمالها خارج
``with`` يعطي كائنًا فوق اتصالٍ مغلق — يعمل في السطر الأول ويفشل في الثاني.
لذلك نبني الاتصال بأنفسنا ونمرّره للباني مباشرة، والاتصال يعيش ما عاشت
العملية.

**لماذا singleton**: الـcheckpointer والـStore حالةٌ على القرص. اتصالان
مختلفان على الملف نفسه في العملية نفسها يعنيان قفلًا متنازعًا وحالةً
منقسمة. فالبناء مرة واحدة، وكل من طلب الذاكرة أخذ الكائنين نفسيهما.

**أي Store**: ``SqliteStore`` موجود فعلًا في ``langgraph.store.sqlite``
(الحزمة ``langgraph-checkpoint-sqlite``) في هذه البيئة، فهو المستعمل — لا
حاجة إلى بديل ``InMemoryStore``. والمطلوب في الروبرك Store **منفصل عبر
الـthreads**؛ ودوامه على القرص فوق ذلك ربحٌ إضافي يقوّي دليل «الحالة
الدائمة».
"""

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore

# جذر المشروع مشتق من موقع الملف: src/munassiq/memory.py -> src/munassiq ->
# src -> الجذر. لا مسار مطلق حرفي مزروع في الكود.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# قاعدة الحالة الدائمة — مُتجاهَلة في git عبر نمط ``*.sqlite``.
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "munassiq-state.sqlite"

# اسم فضاء الأسماء الأول في الـStore. الثاني هو ``user_id``، فالذكريات
# مفصولة بالعضو لا بالمحادثة.
MEMORY_NAMESPACE = "memories"

# الكائنان المبنيان مرة واحدة لكل عملية.
_MEMORY: tuple[SqliteSaver, SqliteStore] | None = None


def _connect(db_path: Path, *, autocommit: bool) -> sqlite3.Connection:
    """يفتح اتصال sqlite صالحًا للاستعمال عبر خيوط LangGraph.

    ``check_same_thread=False`` إلزامي: LangGraph ينفّذ الـtasks على خيوط
    عاملة، وsqlite يرفض افتراضيًا استعمال اتصالٍ من غير خيط إنشائه.

    ``isolation_level=None`` (وضع الالتزام التلقائي) إلزامي للـStore وحده:
    ``SqliteStore`` يفتح معاملاته بنفسه بـ``BEGIN``، ووضع python الافتراضي
    يكون قد فتح معاملة ضمنية قبله فيرمي
    ``cannot start a transaction within a transaction``.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(
        str(db_path),
        check_same_thread=False,
        isolation_level=None if autocommit else "",
    )


def _build(db_path: Path) -> tuple[SqliteSaver, SqliteStore]:
    """يبني الزوج على ملفين متجاورين ويهيّئ جدولَيهما."""
    checkpointer = SqliteSaver(_connect(db_path, autocommit=False))
    checkpointer.setup()

    store_path = db_path.with_name(f"{db_path.stem}-store{db_path.suffix}")
    store = SqliteStore(_connect(store_path, autocommit=True))
    store.setup()

    return checkpointer, store


def build_memory(db_path=None) -> tuple[SqliteSaver, SqliteStore]:
    """يعيد زوج (checkpointer, store) المشترك للعملية — singleton.

    Args:
        db_path: مسار قاعدة الحالة. يُقرأ في أول نداء فقط؛ النداءات التالية
            تعيد الكائنين المبنيين مهما كان ما مُرِّر، لأن انقسام الحالة
            على ملفين أسوأ من تجاهل معاملٍ مُتأخر.

    Returns:
        الـcheckpointer للذاكرة قصيرة المدى، والـStore للطويلة.
    """
    global _MEMORY
    if _MEMORY is None:
        _MEMORY = _build(Path(db_path) if db_path is not None else DEFAULT_DB_PATH)
    return _MEMORY


def reset_memory_for_tests(tmp_path) -> tuple[SqliteSaver, SqliteStore]:
    """يعيد بناء الـsingleton على ملفٍ داخل ``tmp_path`` ويعيد الزوج الجديد.

    بلا هذا الباب تكتب كل تشغيلة اختبارات في قاعدة المشروع الدائمة، فيتضخم
    الملف وتتسرب ذكريات تشغيلةٍ إلى تأكيدات التي بعدها.

    يجب أن يُنادى **قبل** استيراد :mod:`munassiq.app`، فالـapp يلتقط الزوج
    لحظة بنائه.
    """
    global _MEMORY
    _MEMORY = _build(Path(tmp_path) / "munassiq-test-state.sqlite")
    return _MEMORY
