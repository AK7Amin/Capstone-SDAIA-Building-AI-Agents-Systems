"""أدوات «المُنسِّق» ونموذج التصنيف المهيكل.

ثلاثة أنواع من الفعل هنا:

* **أدوات يناديها النموذج** (`@tool`): التقويم وحفظ مسودة البريد. كل واحدة
  تستعمل معاملاتها فعلًا — معاملات مختلفة تعطي ناتجًا مختلفًا، وهذا هو الفرق
  بين نداء أداة حقيقي ودالة تتجاهل ما يُمرَّر إليها.
* **دالة عادية خارج متناول النموذج**: :func:`send_approved_email`. لا تُعرَّف
  أداةً لأن الفعل غير القابل للعكس لا يُترك لقرار النموذج — تُستدعى من
  الـentrypoint بعد موافقة بشرية، وتكتب النص **حرفيًا كما وصلها** بلا أي
  تمرير على نموذج.
* **مخرج مهيكل**: :class:`TriageDecision` مع :func:`triage`.

لا إرسال حقيقي لأي بريد في هذا المشروع — «الإرسال» كتابةٌ في صندوق صادر محلي
تحت ``data/outbox/`` (مُتجاهَل في git).
"""

from datetime import datetime
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from munassiq.config import get_llm, invoke_structured

# جذر المشروع مشتق من موقع الملف: src/munassiq/tools.py -> src/munassiq -> src
# -> الجذر. لا مسار مطلق حرفي مزروع في الكود.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# صندوق الصادر المحلي. يُقرأ من الغلاف الموديولي عند كل نداء، فيمكن للاختبارات
# تحويله إلى مجلد مؤقت عبر monkeypatch بلا أي مخلَّف في مجلد المشروع.
OUTBOX_DIR = PROJECT_ROOT / "data" / "outbox"

# حالة التقويم في الذاكرة — كافية لغرض المشروع، وتُفرَّغ بين الاختبارات.
CALENDAR: list[dict] = []


def _timestamped_path(prefix: str) -> Path:
    """يبني مسارًا فريدًا داخل صندوق الصادر باسم مشتق من الطابع الزمني."""
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = OUTBOX_DIR / f"{prefix}-{stamp}.txt"
    # احتياط تصادم لو نُودي مرتين داخل الميكروثانية نفسها.
    counter = 2
    while path.exists():
        path = OUTBOX_DIR / f"{prefix}-{stamp}-{counter}.txt"
        counter += 1
    return path


def _relative_to_project(path: Path) -> str:
    """المسار نسبةً لجذر المشروع متى أمكن — وإلا فالمسار كما هو."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


@tool
def create_event(title: str, day: str) -> str:
    """يضيف موعدًا إلى تقويم الجمعية.

    Args:
        title: عنوان الموعد كما يذكره الطلب.
        day: اليوم المطلوب للموعد.
    """
    CALENDAR.append({"title": title, "day": day})
    return f"أُضيف الموعد «{title}» يوم {day} إلى التقويم."


@tool
def list_events() -> str:
    """يعرض كل المواعيد المسجّلة في تقويم الجمعية."""
    if not CALENDAR:
        return "التقويم فارغ — لا مواعيد مسجّلة."
    lines = [f"- «{event['title']}» يوم {event['day']}" for event in CALENDAR]
    return "مواعيد التقويم:\n" + "\n".join(lines)


@tool
def save_email_draft(to: str, subject: str, body: str) -> str:
    """يحفظ مسودة بريد في صندوق الصادر المحلي — بلا إرسال حقيقي.

    Args:
        to: عنوان المستقبِل.
        subject: موضوع الرسالة.
        body: نص الرسالة.
    """
    path = _timestamped_path("draft")
    content = f"إلى: {to}\nالموضوع: {subject}\n\n{body}\n"
    path.write_text(content, encoding="utf-8", newline="")
    return _relative_to_project(path)


def send_approved_email(text: str) -> str:
    """يكتب النص المعتمَد من البشر حرفيًا في صندوق الصادر ويعيد مساره.

    ليست ``@tool`` عمدًا: الفعل غير القابل للعكس لا يُترك لقرار النموذج، بل
    يُستدعى من الـentrypoint بعد موافقة بشرية. والنص يُكتب **كما وصل** بلا
    إعادة صياغة ولا تمرير على أي نموذج، حتى يظل تعديل البشري هو ما يخرج.
    """
    path = _timestamped_path("sent")
    path.write_text(text, encoding="utf-8", newline="")
    return _relative_to_project(path)


class TriageDecision(BaseModel):
    """قرار توجيه طلبٍ وارد إلى العامل المناسب."""

    worker: Literal["calendar", "knowledge", "correspondence"] = Field(
        description=(
            "العامل الذي يتولى الطلب: calendar لحجز المواعيد وعرض التقويم، "
            "knowledge للأسئلة التي جوابها في وثائق الجمعية، "
            "correspondence لصياغة الرسائل والبريد."
        )
    )
    needs_human_approval: bool = Field(
        description=(
            "هل يحتاج تنفيذ الطلب موافقة بشرية قبل الفعل؟ true لكل فعل غير "
            "قابل للعكس مثل إرسال بريد باسم الجمعية، وfalse لما هو قراءة أو "
            "تسجيل داخلي."
        )
    )
    summary: str = Field(
        description="ملخّص عربي مقتضب في جملة واحدة لما يطلبه المستخدم."
    )


TRIAGE_SYSTEM_PROMPT = (
    "أنت مُنسِّق مكتب جمعية. صنّف الطلب الوارد وحدّد العامل المناسب له، "
    "وهل يحتاج موافقة بشرية قبل التنفيذ، مع ملخّص عربي مقتضب. "
    "طلبات حجز المواعيد وعرض التقويم إلى calendar، والأسئلة عن سياسات "
    "الجمعية وإجراءاتها إلى knowledge، وصياغة الرسائل والبريد إلى "
    "correspondence."
)


def triage(request: str) -> TriageDecision:
    """يصنّف طلبًا واردًا ويعيد قرار التوجيه مخرجًا مهيكلًا."""
    classifier = get_llm().with_structured_output(TriageDecision)
    return invoke_structured(classifier, 
        [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": request},
        ]
    )
