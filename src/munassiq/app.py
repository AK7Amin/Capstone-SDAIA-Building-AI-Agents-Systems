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

**الوقوف البشري**: الفعل غير القابل للعكس (إرسال بريد باسم الجمعية) لا يقع
إلا بعد ``interrupt`` يعرض على البشري مسودةً **مصوغةً سلفًا**. وموضع الوقوف
جسمُ الـentrypoint نفسه لا داخل ``@task``: الـ``@task`` وحدة تُعاد أو
تُستعاد كاملة، فوقوفٌ في وسطها يعني إعادة تنفيذ ما سبقه عند الاستئناف. وما
يعود من الاستئناف يمضي **حرفيًا** إلى صندوق الصادر بلا أي تمرير على نموذج —
وإلا لم يعد ما خرج تعديلَ البشري.

**نمط Evaluator-Optimizer**: مسار المراسلات لا يعرض أول ما يخطر للنموذج.
:func:`draft_correspondence` تدير حلقةً مسمّاة — صياغة، ثم تقييمٌ بحكمٍ
مهيكل، ثم تحسينٌ بالملاحظات إن رُفضت المسودة، ثم إعادة تقييم — بسقف
:data:`MAX_EVALUATION_ROUNDS`. والحلقة كلها تسبق الـinterrupt: البشري
مراجعٌ أخير لنصٍّ نُقّح، لا مصحّحُ مسوّدةٍ خام. وهي مطويّة داخل ``@task``
واحدة لا مبسوطةٌ في جسم الـentrypoint، فتُستعاد وحدةً واحدة من
الـcheckpointer عند الاستئناف بدل أن تُعاد جولاتها.
"""

from uuid import uuid4

from langgraph.config import get_store
from langgraph.func import entrypoint, task
from langgraph.types import Command, interrupt  # noqa: F401  (Command يُعاد تصديره)
from pydantic import BaseModel, Field

from munassiq.config import get_llm, invoke_structured
from munassiq.memory import MEMORY_NAMESPACE, build_memory
from munassiq.tools import TriageDecision, send_approved_email, triage

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

DRAFT_SYSTEM_PROMPT = (
    "أنت كاتب مراسلات جمعية المحتوى الإسلامي. اكتب نص الرسالة التي يطلبها "
    "المستخدم جاهزةً للإرسال: تحيةٌ، ثم المضمون كما ورد في الطلب بلا زيادة "
    "من عندك، ثم خاتمة. بعربية فصيحة موجزة تليق بمراسلات الجمعية. "
    "أخرج نص الرسالة وحده — بلا مقدمة ولا تعليق ولا شرح لما فعلت."
)

EVALUATOR_SYSTEM_PROMPT = (
    "أنت مراجع مراسلات جمعية المحتوى الإسلامي. أمامك طلب المستخدم والمسودة "
    "المكتوبة استجابةً له. قيّمها على أربعة معايير: هل تنقل ما طُلب كاملًا، "
    "وهل خلت من زيادةٍ لم تَرِد في الطلب، وهل لغتها عربية فصيحة موجزة تليق "
    "بمراسلات الجمعية، وهل فيها تحية وخاتمة. "
    "أعطِ درجة من 1 إلى 10، واجعل approved تساوي true إن كانت المسودة صالحة "
    "للعرض على المسؤول البشري كما هي. "
    "وإن لم تعتمدها فاكتب في feedback ملاحظاتٍ محددة تقول ما يُصلَح بالضبط "
    "وكيف، لا حكمًا عامًا مثل «تحتاج تحسينًا»."
)

OPTIMIZER_SYSTEM_PROMPT = (
    "أنت كاتب مراسلات جمعية المحتوى الإسلامي. أمامك مسودةٌ وملاحظات مراجعٍ "
    "عليها. أعد كتابة المسودة معالجًا كل ملاحظة، محافظًا على مضمون الطلب كما "
    "ورد بلا زيادة من عندك. "
    "أخرج نص الرسالة المحسّنة وحدها — بلا مقدمة ولا تعليق ولا ذكر للملاحظات."
)

# سقف جولات التقييم في حلقة Evaluator-Optimizer. اثنتان لا أكثر: الجولة
# الثانية هي التي تُثبت أن الملاحظات عولجت، وما بعدها كلفةٌ ونداءات نموذج
# إضافية على مسارٍ ينتهي أصلًا إلى مراجعٍ بشري.
MAX_EVALUATION_ROUNDS = 2

# ما يُعرض على البشري عند الوقوف: أمرٌ صريح بما هو مطلوب منه، لا مجرد
# «موافق؟» — الحمولة هي كل ما يراه من يستأنف الرحلة.
INTERRUPT_ACTION = "راجع المسودة واعتمدها أو عدّلها"

# المشرف يُبنى مرة واحدة لكل عملية: بناؤه يشمل بناء فهرس RAG وتضميناته، وهو
# أثقل من أن يُعاد في كل رحلة.
_SUPERVISOR = None


class DraftVerdict(BaseModel):
    """حكم المراجع على مسودةٍ واحدة — مخرجٌ مهيكل لا نصٌّ يُفتَّش فيه.

    قرارُ الاعتماد يُقرأ من :attr:`approved` وحده. البديل — البحث عن كلمة
    «معتمدة» في نص الملاحظات — يجعل قرارًا تنفيذيًا رهينةَ صياغةٍ قد تذكر
    الكلمة نفيًا أو اقتباسًا، وهو بالضبط ما يفحصه اختبار الشريحة.
    """

    score: int = Field(
        ge=1,
        le=10,
        description="درجة المسودة من 1 (غير صالحة) إلى 10 (جاهزة كما هي).",
    )
    approved: bool = Field(
        description=(
            "هل المسودة صالحة للعرض على المسؤول البشري كما هي؟ false إن كانت "
            "تحتاج تحسينًا قبل العرض."
        )
    )
    feedback: str = Field(
        description=(
            "ملاحظات عملية محددة تقول ما يُصلَح وكيف، أو نص فارغ إن كانت "
            "approved تساوي true."
        )
    )


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


def _message_text(message) -> str:
    """نص رسالةٍ واحدة — يسوّي المحتوى المُقطَّع قائمةَ أجزاء إلى نص واحد."""
    content = getattr(message, "content", "") or ""
    if isinstance(content, list):
        content = " ".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return content.strip()


def _last_text(result) -> str:
    """آخر نص فعلي في رحلة المشرف.

    الرسالة الأخيرة قد تكون نداء أداة محتواها فارغ، فنمشي إلى الوراء حتى
    نجد نصًّا — وإلا خرج ``reply`` فارغًا بلا أن يفشل شيء ظاهر.
    """
    for message in reversed(result.get("messages", [])):
        text = _message_text(message)
        if text:
            return text
    return ""


def needs_approval(decision: TriageDecision) -> bool:
    """هل يقف التنفيذ لموافقة بشرية قبل تنفيذ هذا الطلب؟

    دالة نقية عمدًا: شرطُ توجيهٍ مدفونٌ داخل جسم الـentrypoint لا يُفحص إلا
    بنداء نموذج، وهذا يُفحص بلا شبكة أصلًا.

    شرطان بينهما «أو» لا شرطٌ واحد: كون العامل ``correspondence`` كافٍ وحده،
    فالمراسلة فعلٌ باسم الجمعية لا يُترك لعلمٍ قد يغفل النموذج عن رفعه؛
    و``needs_human_approval`` كافٍ وحده أيضًا، فيغطي ما يوسمه النموذج غير
    قابل للعكس في عاملٍ آخر.
    """
    return decision.worker == "correspondence" or decision.needs_human_approval


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
    verdict = invoke_structured(judge, 
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
def classify_request(request: str) -> TriageDecision:
    """يصنّف الطلب مخرجًا مهيكلًا — نداء نموذج، فهو داخل ``@task``.

    غلافٌ رفيع حول :func:`munassiq.tools.triage`: وجوده هنا ليس تكرارًا، بل
    ليقع النداء داخل وحدةٍ تُستعاد من الـcheckpointer عند الاستئناف فلا
    يُصنَّف الطلب مرتين ولا يتبدّل القرار الذي بُني عليه الوقوف.
    """
    return triage(request)


def _memory_messages(memories: list[str]) -> list[dict]:
    """رسالة نظامٍ واحدة بالذكريات، أو لا شيء إن لم تكن هناك ذكريات."""
    if not memories:
        return []
    block = "\n".join(f"- {fact}" for fact in memories)
    return [{"role": "system", "content": f"{SUPERVISOR_MEMORY_HEADER}\n{block}"}]


@task
def compose_draft(request: str, memories: list[str]) -> str:
    """يصوغ المسودة الأولى — الخطوة المولِّدة في حلقة Evaluator-Optimizer.

    الذكريات تُحقن هنا أيضًا فتظل تفضيلات العضو حاضرة في المسودة كما هي في
    بقية المسارات.
    """
    messages = (
        [{"role": "system", "content": DRAFT_SYSTEM_PROMPT}]
        + _memory_messages(memories)
        + [{"role": "user", "content": request}]
    )
    return _message_text(get_llm().invoke(messages))


@task
def evaluate_draft(request: str, draft: str) -> DraftVerdict:
    """يحكم على المسودة حكمًا مهيكلًا — الخطوة المقيِّمة Evaluator.

    الحكم :class:`DraftVerdict` عبر ``with_structured_output``: يعود حقلٌ
    منطقي يُقرأ مباشرة، فلا يُبنى قرار الحلقة على تفتيشٍ في نصٍّ حر.
    """
    judge = get_llm().with_structured_output(DraftVerdict)
    return invoke_structured(judge, 
        [
            {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"طلب المستخدم:\n{request}\n\nالمسودة:\n{draft}",
            },
        ]
    )


@task
def improve_draft(
    request: str, draft: str, feedback: str, memories: list[str]
) -> str:
    """يعيد كتابة المسودة معالجًا ملاحظات المقيّم — الخطوة المحسِّنة Optimizer.

    الملاحظات تدخل السياق نصًّا صريحًا: التحسين بلا ملاحظاتٍ إعادةُ صياغةٍ
    عمياء قد تُفسد ما كان سليمًا.
    """
    messages = (
        [{"role": "system", "content": OPTIMIZER_SYSTEM_PROMPT}]
        + _memory_messages(memories)
        + [
            {
                "role": "user",
                "content": (
                    f"طلب المستخدم:\n{request}\n\n"
                    f"المسودة الحالية:\n{draft}\n\n"
                    f"ملاحظات المراجع:\n{feedback}"
                ),
            }
        ]
    )
    return _message_text(get_llm().invoke(messages))


@task
def draft_correspondence(request: str, memories: list[str]) -> dict:
    """يصوغ المسودة ويُنقّحها بحلقة مراجعة، ويعيد النص وحصيلة الحلقة.

    # نمط Evaluator-Optimizer
    صياغة ← تقييم ← (إن لم يُعتمد) تحسينٌ بالملاحظات ← إعادة تقييم، بسقف
    :data:`MAX_EVALUATION_ROUNDS` جولتين. كل مسودةٍ تخرج من هنا قد مرّت على
    المقيّم — لا يُسلَّم للبشري نصٌّ حُسِّن بلا أن يُراجَع بعد تحسينه.

    الحلقة مطويّة داخل هذه المهمة لا مبسوطةً في جسم الـentrypoint، لسببين:
    نتائجها تُستعاد وحدةً واحدة من الـcheckpointer عند الاستئناف؛ ومسار
    المراسلات يبقى في جسم الـentrypoint نداءً واحدًا يسبق الـinterrupt
    فيظل الجسم غراءً نقيًا مقروءًا. ونداء ``@task`` من داخل ``@task`` مدعوم
    (مُثبَت بسبايك الشريحة).

    وحدّ الجولتين صلب: مقيّمٌ لا يقتنع أبدًا لا يُدير حلقةً بلا نهاية —
    تُعرض آخر مسودةٍ على البشري، وهو الحَكَم الأخير أصلًا.

    Returns:
        ``{"draft": str, "rounds": int, "score": int, "approved": bool}`` —
        الحصيلة تعود مع النص لا تُطرح جانبًا: النمط المسمّى يُطالَب بدليلٍ
        مطبوع (كم جولةً دارت وبأي درجة انتهت)، وحسابُها هنا فيُقرأ من ناتج
        المهمة أوثق من إعادة استنتاجه من الخارج.
    """
    draft = compose_draft(request, memories).result()

    verdict = evaluate_draft(request, draft).result()
    rounds = 1
    while not verdict.approved and rounds < MAX_EVALUATION_ROUNDS:
        draft = improve_draft(request, draft, verdict.feedback, memories).result()
        verdict = evaluate_draft(request, draft).result()
        rounds += 1

    return {
        "draft": draft,
        "rounds": rounds,
        "score": verdict.score,
        "approved": verdict.approved,
    }


def _draft_parts(drafted) -> tuple[str, int | None, int | None]:
    """يفكّ ناتج حلقة المراجعة إلى (نص، عدد الجولات، الدرجة).

    دالة نقية في جسم الغراء لا نداءَ فيها: تقبل الشكل الغني ``dict``، وتقبل
    نصًّا مجردًا فتعيد حصيلةً فارغة. قبول النص المجرد ليس تساهلًا — مهمةٌ
    مستبدَلة في اختبارٍ قد تعيد سلسلة، وناتجٌ مستعاد من checkpointer كُتب قبل
    هذه الإضافة كذلك، ولا يصح أن ينكسر مسار الوقوف البشري على شكلٍ أضيق.
    """
    if isinstance(drafted, dict):
        return (
            str(drafted.get("draft", "")),
            drafted.get("rounds"),
            drafted.get("score"),
        )
    return str(drafted), None, None


@task
def send_final(approved_text: str) -> dict:
    """يكتب النص المعتمَد من البشر في صندوق الصادر ويعيد الرد ومساره.

    الفعل غير القابل للعكس، ولذلك هو داخل ``@task``: عند أي استئناف لاحق
    على هذا الـthread يُستعاد ناتجه من الـcheckpointer فلا يُكتب الملف
    مرتين. والنص يمضي إلى :func:`send_approved_email` **كما وصل** — لا
    نموذج بينه وبين القرص.
    """
    return {
        "reply": approved_text,
        "outbox_path": send_approved_email(approved_text),
    }


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
        أعلاه. الاستثناء الوحيد ``interrupt``، وهو ليس أثرًا خارجيًا بل
        آلية الوقوف نفسها، وموضعها الصحيح جسمُ الـentrypoint.

        الناتج dict فيه ``reply`` و``memories_used`` و``turn``
        و``outbox_path`` (``None`` لكل مسار لم يُرسل شيئًا) و``evaluation``
        (حصيلة حلقة Evaluator-Optimizer: ``rounds`` و``score``، و``None``
        على المسار الذي لا حلقة فيه). وفي رحلة الوقوف يعود بدلًا منه dict
        مفتاحه ``__interrupt__`` من LangGraph نفسه، وحمولته تحمل الحصيلة
        نفسها في ``evaluation_rounds`` و``evaluation_score``.
        """
        state = previous or {"turn": 0, "history": []}
        history = list(state.get("history", []))

        request = payload["request"]
        user_id = payload["user_id"]

        memories = load_memories(user_id).result()
        stored = detect_and_store_memory(request, user_id).result()
        if stored and stored not in memories:
            memories = memories + [stored]

        decision = classify_request(request).result()

        if needs_approval(decision):
            # نمط Evaluator-Optimizer داخل هذه المهمة: صياغة ← تقييم ←
            # تحسين ← تقييم. تكتمل كاملةً **قبل** السطر التالي، فما يراه
            # البشري نصٌّ نُقّح لا مسوّدة خام.
            drafted = draft_correspondence(request, memories).result()
            draft, rounds, score = _draft_parts(drafted)
            # الوقوف هنا: المسودة جاهزة والفعل لم يقع بعد. قيمة الاستئناف
            # (نص ``Command(resume=...)``) هي نص البشري، ويمضي كما هو.
            approved = interrupt(
                {
                    "action": INTERRUPT_ACTION,
                    "draft": draft,
                    "summary": decision.summary,
                    "evaluation_rounds": rounds,
                    "evaluation_score": score,
                }
            )
            sent = send_final(approved).result()
            reply = sent["reply"]
            outbox_path = sent["outbox_path"]
            evaluation = {"rounds": rounds, "score": score}
        else:
            reply = run_supervisor(request, memories, history).result()
            outbox_path = None
            evaluation = None

        turn = int(state.get("turn", 0)) + 1
        history = history + [{"request": request, "reply": reply}]
        result = {
            "reply": reply,
            "memories_used": memories,
            "turn": turn,
            "outbox_path": outbox_path,
            "evaluation": evaluation,
        }
        return entrypoint.final(
            value=result, save={"turn": turn, "history": history}
        )

    return munassiq_app


# الـapp الجاهز للنوتبوك ولبقية الشرائح — فوق قاعدة الحالة الدائمة.
munassiq_app = build_app()
