"""الـentrypoint الوظيفي الجامع — الغراء الذي يربط الذاكرة بالمشرف.

**انضباط الـentrypoint**: جسم :func:`munassiq_app` غراءٌ نقي — شرطٌ ونداءات
`@task` وجمع نتائجها، لا أكثر. كل نداء نموذج وكل أثر جانبي (كتابة في
الـStore، كتابة ملف) يسكن داخل ``@task``. السبب ميكانيكي لا تجميلي: عند
الاستئناف بعد ``interrupt`` يُعاد تنفيذ جسم الـentrypoint من أوله، بينما
نتائج الـ``@task`` المكتملة تُقرأ من الـcheckpointer ولا تُعاد. فسطرٌ يستدعي
نموذجًا خارج ``@task`` يعني فاتورةً مكررة وناتجًا مختلفًا عمّا بُني عليه
القرار.

**حتمية الذاكرة**: تحميل ذكريات العضو وحقنها في السياق يقع في كل رحلة بلا
شرط. لو تُرك الأمر لأداةٍ يقرر النموذج نداءها، لصار التذكّر احتمالًا لا
ضمانًا — والروبرك يسأل عن ذاكرةٍ تعمل، لا عن ذاكرةٍ متاحة.
"""

from uuid import uuid4

from langgraph.config import get_store
from langgraph.func import entrypoint, task
from pydantic import BaseModel, Field

from munassiq.config import get_llm
from munassiq.memory import MEMORY_NAMESPACE, build_memory

MEMORY_DETECTOR_PROMPT = (
    "أنت ذاكرة مساعد مكتب جمعية المحتوى الإسلامي. مهمتك وحدها أن تقرر: هل في "
    "رسالة المستخدم حقيقةٌ ثابتة عنه أو تفضيلٌ له يستحق أن يُتذكَّر في "
    "محادثات قادمة؟ "
    "التفضيلات والمواعيد الثابتة والأسماء والصفات الدائمة تستحق التذكّر. "
    "أما الأسئلة والأوامر العابرة والتحيات فلا. "
    "وإن استحقّت، فاكتب الحقيقة جملةً عربية واحدة تنقل ألفاظ المستخدم كما "
    "وردت — خصوصًا الأيام والأسماء والأرقام — بلا إعادة صياغة ولا تفسير. "
    "وإن لم تستحق فاجعل fact نصًّا فارغًا."
)

SUPERVISOR_MEMORY_HEADER = (
    "ذكريات محفوظة عن هذا العضو من محادثات سابقة — اعتمدها متى كانت ذات صلة "
    "بالطلب، ولا تسأل المستخدم عمّا هو مذكور فيها:"
)

# المشرف يُبنى مرة واحدة لكل عملية: بناؤه يشمل بناء فهرس RAG وتضميناته، وهو
# أثقل من أن يُعاد في كل رحلة.
_SUPERVISOR = None


class MemoryCandidate(BaseModel):
    """حكمٌ مهيكل على رسالة واحدة: أتستحق التذكّر، وبأي صيغة."""

    should_remember: bool = Field(
        description=(
            "هل تحمل الرسالة حقيقة ثابتة أو تفضيلًا يستحق تذكّره عبر "
            "المحادثات؟ false للأسئلة والأوامر العابرة."
        )
    )
    fact: str = Field(
        description=(
            "الحقيقة جملةً عربية واحدة بألفاظ المستخدم كما وردت، أو نص فارغ "
            "إن كانت should_remember تساوي false."
        )
    )


def _get_supervisor():
    """يبني المشرف عند أول حاجة ويعيده مخزَّنًا بعدها.

    بلا ``checkpointer``: الحالة الدائمة مسؤولية الـentrypoint وحده، ومشرفٌ
    يحفظ حالته أيضًا يعني مصدرَي حقيقة لنفس المحادثة.
    """
    global _SUPERVISOR
    if _SUPERVISOR is None:
        from munassiq.supervisor import build_supervisor

        _SUPERVISOR = build_supervisor(checkpointer=None)
    return _SUPERVISOR


def _last_text(result) -> str:
    """آخر نص فعلي في رحلة المشرف.

    الرسالة الأخيرة قد تكون نداء أداة محتواها فارغ، فنمشي إلى الوراء حتى
    نجد نصًّا — وإلا خرج ``reply`` فارغًا بلا أن يفشل شيء ظاهر.
    """
    for message in reversed(result.get("messages", [])):
        content = getattr(message, "content", "") or ""
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if content.strip():
            return content.strip()
    return ""


@task
def load_memories(user_id: str) -> list[str]:
    """يقرأ كل ذكريات العضو من الـStore — أثرٌ خارجي، فهو داخل ``@task``."""
    store = get_store()
    items = store.search((MEMORY_NAMESPACE, user_id))
    return [
        str(item.value.get("fact", "")).strip()
        for item in items
        if str(item.value.get("fact", "")).strip()
    ]


@task
def detect_and_store_memory(request: str, user_id: str) -> str | None:
    """يحكم على الطلب بمخرج مهيكل، ويكتب الحقيقة في الـStore إن استحقّت.

    نداء نموذج **وكتابة** معًا — أثران لا يجوز تكرارهما عند الاستئناف، ولذلك
    هما هنا داخل ``@task`` لا في جسم الـentrypoint.

    Returns:
        نص الحقيقة المكتوبة، أو ``None`` إن لم يستحق الطلب تذكّرًا.
    """
    judge = get_llm().with_structured_output(MemoryCandidate)
    verdict = judge.invoke(
        [
            {"role": "system", "content": MEMORY_DETECTOR_PROMPT},
            {"role": "user", "content": request},
        ]
    )
    fact = (verdict.fact or "").strip()
    if not verdict.should_remember or not fact:
        return None

    # مفتاح uuid: الذكريات تُضاف ولا يدهس بعضها بعضًا — العضو قد يذكر أكثر
    # من حقيقة عبر محادثاته.
    get_store().put((MEMORY_NAMESPACE, user_id), str(uuid4()), {"fact": fact})
    return fact


@task
def run_supervisor(request: str, memories: list[str], history: list[dict]) -> str:
    """يحقن الذكريات وسياق الأدوار السابقة ثم يشغّل المشرف ويعيد آخر نص.

    Args:
        request: طلب هذا الدور كما ورد.
        memories: ذكريات طويلة المدى تُحقن رسالةَ نظامٍ قبل كل شيء.
        history: أدوار هذا الـthread السابقة — الذاكرة قصيرة المدى.
    """
    messages: list[dict] = []
    if memories:
        block = "\n".join(f"- {fact}" for fact in memories)
        messages.append(
            {"role": "system", "content": f"{SUPERVISOR_MEMORY_HEADER}\n{block}"}
        )
    for turn in history:
        messages.append({"role": "user", "content": turn["request"]})
        messages.append({"role": "assistant", "content": turn["reply"]})
    messages.append({"role": "user", "content": request})

    return _last_text(_get_supervisor().invoke({"messages": messages}))


def build_app(checkpointer=None, store=None):
    """يبني الـentrypoint فوق زوج الذاكرة ويعيده.

    مصنعٌ لا تعريفٌ ساكن: الاختبارات تصفّر الذاكرة إلى ملف مؤقت ثم تعيد
    البناء، فلا تتسرب حالة تشغيلةٍ إلى التي بعدها.
    """
    if checkpointer is None or store is None:
        default_checkpointer, default_store = build_memory()
        checkpointer = checkpointer or default_checkpointer
        store = store or default_store

    @entrypoint(checkpointer=checkpointer, store=store)
    def munassiq_app(payload: dict, *, previous: dict | None = None) -> dict:
        """يستقبل ``{"request": str, "user_id": str}`` ويعيد الرد وما ذُكر.

        الجسم غراءٌ نقي: لا نداء نموذج ولا كتابة هنا — كلها في الـ``@task``
        أعلاه.
        """
        state = previous or {"turn": 0, "history": []}
        history = list(state.get("history", []))

        request = payload["request"]
        user_id = payload["user_id"]

        memories = load_memories(user_id).result()
        stored = detect_and_store_memory(request, user_id).result()
        if stored and stored not in memories:
            memories = memories + [stored]

        # نقطة الـinterrupt للشريحة 6 (اعتماد المراسلات) تدخل هنا — قبل
        # ``run_supervisor`` وبعد اكتمال حكم التصنيف.

        reply = run_supervisor(request, memories, history).result()

        turn = int(state.get("turn", 0)) + 1
        history = history + [{"request": request, "reply": reply}]
        result = {"reply": reply, "memories_used": memories, "turn": turn}
        return entrypoint.final(
            value=result, save={"turn": turn, "history": history}
        )

    return munassiq_app


# الـapp الجاهز للنوتبوك ولبقية الشرائح — فوق قاعدة الحالة الدائمة.
munassiq_app = build_app()
