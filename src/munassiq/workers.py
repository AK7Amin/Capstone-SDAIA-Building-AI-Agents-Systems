"""عمّال «المُنسِّق» — وكيلٌ لكل اختصاص، وأدواته وحدها في متناوله.

كل عامل هنا وكيل ReAct كامل: نموذج + مجموعة أدوات ضيّقة + تعليمات عربية
تحصره في اختصاصه. الفصل مقصود — عامل التقويم لا يرى أداة البريد، فلا يقدر
أن ينحرف إليها أصلًا، وهذا حصرٌ بالبنية لا بالرجاء في نص التعليمات.

الاسم (``name``) **إلزامي** لكل عامل: منه يشتقّ المشرف أداة التسليم
``transfer_to_<name>``. عاملٌ بلا اسم يعني مشرفًا بلا يدٍ يسلّم بها.

عامل المعرفة (RAG) أُضيف في الشريحة 4 على النمط نفسه: أداة بحث واحدة في
وثائق الجمعية، وتعليمات تحصر جوابه في المقاطع المسترجَعة.

**قسم الصمود** في آخر الملف يضيف استراتيجيتَي التعامل مع الخطأ. تسكنان هنا
لا في :mod:`munassiq.app` لأنهما قدرتان عامتان يستعملهما أي عامل، بينما
``app`` مخصص لخيط الرحلة الواحدة. وكلتاهما ``@task``، فلا تُناديان خارج
سياق runnable — ولذلك :func:`run_reliability_task` أدناه.
"""

from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.func import entrypoint, task
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from langchain.agents import create_agent

from munassiq.config import get_llm
from munassiq.rag import build_knowledge_tool
from munassiq.tools import create_event, list_events, save_email_draft

CALENDAR_AGENT_PROMPT = (
    "أنت عامل التقويم في مكتب جمعية المحتوى الإسلامي. مهمتك حجز المواعيد "
    "وعرض ما هو مسجّل في التقويم، لا غير. "
    "استعمل أداة create_event لتسجيل أي موعد جديد، وحدّد لها عنوان الموعد "
    "واليوم كما وردا في طلب المستخدم حرفيًا بلا إعادة صياغة، "
    "واستعمل list_events حين يُسأل عمّا هو محجوز. "
    "لا تدّعِ أنك سجّلت موعدًا قبل أن تناديَ الأداة فعلًا. "
    "ثم أجب بجملة عربية واحدة موجزة تؤكد ما تمّ."
)

CORRESPONDENCE_AGENT_PROMPT = (
    "أنت عامل المراسلات في مكتب جمعية المحتوى الإسلامي. مهمتك صياغة الرسائل "
    "وحفظها مسوّدات، لا غير. "
    "استعمل أداة save_email_draft لحفظ كل رسالة تصوغها، ومرّر لها المستقبِل "
    "والموضوع ونص الرسالة. "
    "الحفظ مسوّدةٌ فقط ولا إرسال هنا — لا تقل للمستخدم إنك أرسلت شيئًا. "
    "اكتب بعربية فصيحة موجزة تليق بمراسلات الجمعية، "
    "ثم أجب بجملة واحدة تذكر أن المسودة حُفظت."
)

KNOWLEDGE_AGENT_PROMPT = (
    "أنت عامل المعرفة في مكتب جمعية المحتوى الإسلامي. مهمتك الإجابة عن "
    "الأسئلة المتعلقة بسياسات الجمعية وإجراءاتها وأدلتها، لا غير. "
    "استعمل أداة search_policies للبحث في الوثائق قبل أي جواب، ولك أن "
    "تكررها بصياغات مختلفة إن لم تكفِ النتيجة الأولى. "
    "أجب من المقاطع المسترجَعة وحدها ولا تضف من معرفتك العامة شيئًا، "
    "وانقل الأرقام والمدد كما وردت في المقطع حرفيًا. "
    "وإن لم تجد الجواب في المقاطع فقل «لا أجد هذا في وثائق الجمعية» "
    "ولا تخمّن. "
    "ثم أجب بعربية موجزة مع ذكر الوثيقة التي جاء منها الجواب."
)


def build_calendar_agent() -> CompiledStateGraph:
    """يبني عامل التقويم: أدوات الحجز والعرض وحدها في متناوله."""
    return create_agent(
        get_llm(),
        [create_event, list_events],
        system_prompt=CALENDAR_AGENT_PROMPT,
        name="calendar_agent",
    )


def build_correspondence_agent() -> CompiledStateGraph:
    """يبني عامل المراسلات: حفظ المسودات وحده في متناوله."""
    return create_agent(
        get_llm(),
        [save_email_draft],
        system_prompt=CORRESPONDENCE_AGENT_PROMPT,
        name="correspondence_agent",
    )


def build_knowledge_agent() -> CompiledStateGraph:
    """يبني عامل المعرفة: البحث في وثائق الجمعية وحده في متناوله.

    الوكيل هو من يقرر متى يستعلم وكم مرة — هذا هو Agentic RAG بخلاف خطٍّ
    ثابت يسترجع مرة واحدة قبل كل جواب.
    """
    return create_agent(
        get_llm(),
        [build_knowledge_tool()],
        system_prompt=KNOWLEDGE_AGENT_PROMPT,
        name="knowledge_agent",
    )


# ---------------------------------------------------------------------------
# الصمود: استراتيجيتان مختلفتان لصنفين مختلفين من الخطأ
#
# الفرق بينهما ليس في شدة الخطأ بل في **من يملك إصلاحه**:
#   * العابر Transient — لا أحد يملك إصلاحه، والوقت وحده يصلحه. فالعلاج
#     تكرارٌ آليّ محدود بلا تدخل نموذج: :func:`fetch_external_resource`.
#   * خطأ المدخل — النموذج نفسه هو من أخطأ، فالتكرار الأعمى يعيد الخطأ حرفيًا
#     إلى الأبد. العلاج أن يُعاد إليه نص الخطأ ليصحح:
#     :func:`run_tool_with_llm_recovery`.
# ---------------------------------------------------------------------------

# دليل خارجي مفتعل يقف موقف الخدمة البعيدة. القيم ثابتة عمدًا: الهشاشة تأتي
# من دالة الجلب المحقونة لا من عشوائيةٍ تجعل الاختبار يتذبذب.
_EXTERNAL_DIRECTORY = {
    "قائمة المتطوعين": "volunteers@islamiccontent.example",
    "قائمة الأعضاء": "members@islamiccontent.example",
}

TOOL_INPUT_SYSTEM_PROMPT = (
    "أنت تولّد مدخل أداةٍ واحدة. أخرج قيمة المدخل وحدها — بلا شرح ولا "
    "علامات اقتباس ولا أي نص إضافي."
)

CORRECTION_MESSAGE_TEMPLATE = (
    "فشل نداء الأداة بالمدخل «{tool_input}».\n"
    "الخطأ كما ورد: {error}\n"
    "صحّح المدخل بناءً على نص الخطأ وحده، وأخرج المدخل المصحَّح وحده."
)


def _format_error(error: BaseException) -> str:
    """نوع الخطأ ورسالته فقط — لا traceback خام.

    قرار أمن لا تجميل: الـtraceback يحمل مسارات مطلقة تكشف اسم المستخدم وبنية
    الجهاز، وهذا النص يمضي إلى سياق النموذج وإلى مخرجات النوتبوك المحفوظة.
    """
    return f"{type(error).__name__}: {error}"


def _default_external_fetch(resource: str) -> str:
    """الجلب الافتراضي من الدليل المفتعل — يقوم مقام نداء الشبكة الحقيقي."""
    if resource not in _EXTERNAL_DIRECTORY:
        raise LookupError(f"المورد «{resource}» غير موجود في الدليل الخارجي")
    return _EXTERNAL_DIRECTORY[resource]


@task(retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.1))
def fetch_external_resource(
    resource: str, fetcher: Callable[[str], str] | None = None
) -> str:
    """يجلب موردًا من خدمة خارجية هشّة، ويعيد المحاولة ثلاثًا عند العطل العابر.

    **الاستراتيجية 1 — العابر Transient**: التكرار في ``retry_policy`` على
    المهمة نفسها لا في حلقة ``try/except`` داخل الجسم. الفرق أن LangGraph هو
    من يدير المحاولات والمهل، فتظهر في الـcheckpointer وفي أثر LangSmith
    محاولاتٍ مرقّمة — بينما الحلقة اليدوية تُخفي الفشل داخل نداءٍ واحد ناجح
    ظاهريًا.

    و``ConnectionError`` مُلتقَط بالسياسة الافتراضية؛ وبعد استنفاد المحاولات
    الثلاث **ينتشر** الاستثناء ولا يُبتلَع — عطلٌ دائم يجب أن يُرى.

    Args:
        resource: اسم المورد المطلوب من الدليل الخارجي.
        fetcher: دالة الجلب — تُحقن في الاختبار والنوتبوك لمحاكاة الهشاشة،
            وافتراضها :func:`_default_external_fetch`.
    """
    return (fetcher or _default_external_fetch)(resource)


@task
def run_tool_with_llm_recovery(
    request: str,
    tool: Callable[[str], Any],
    model: Callable[[list[dict]], str] | None = None,
    max_attempts: int = 2,
) -> dict:
    """ينادي أداةً بمدخلٍ من النموذج، وعند فشلها يعيد نص الخطأ إليه ليصحح.

    **الاستراتيجية 2 — LLM-recoverable**: خطأٌ سببه مدخلٌ خاطئ لا يصلحه
    التكرار الأعمى — النموذج سيعيد المدخل نفسه فيقع الخطأ نفسه. فالعلاج أن
    يدخل نص الخطأ **سياق النموذج** رسالةً تصحيحية، فيصير الخطأ معلومةً
    يتعلّم منها لا حائطًا يرتطم به. ولذلك لا ``retry_policy`` هنا: السياسة
    تعيد تنفيذ المهمة من أولها بالسياق نفسه، وهذا بالضبط ما لا ينفع.

    Args:
        request: ما يريده المستخدم، يُعرض على النموذج ليشتق منه مدخل الأداة.
        tool: الأداة المنادَاة بمدخلٍ نصي واحد.
        model: بديل قابل للحقن يأخذ الرسائل ويعيد نص المدخل — يُحقن في
            الاختبار ليُفحص التصحيح بلا شبكة؛ وافتراضه نموذج المشروع.
        max_attempts: سقف نداءات الأداة (محاولةٌ أولى + تصحيحاتها).

    Returns:
        ``{"result": ..., "attempts": int, "errors": list[str]}`` —
        ``errors`` سجلّ الأخطاء المصحَّحة (بلا traceback) للعرض والتوثيق.

    Raises:
        RuntimeError: إن استُنفدت المحاولات ولم ينجح أي مدخل.
    """
    invoke_model = model or _default_tool_input_model
    messages: list[dict] = [
        {"role": "system", "content": TOOL_INPUT_SYSTEM_PROMPT},
        {"role": "user", "content": request},
    ]
    errors: list[str] = []

    for attempt in range(1, max_attempts + 1):
        tool_input = invoke_model(messages)
        try:
            return {"result": tool(tool_input), "attempts": attempt, "errors": errors}
        except Exception as error:  # خطأ الأداة معلومةٌ تُعاد للنموذج لا انهيار
            detail = _format_error(error)
            errors.append(detail)
            messages = messages + [
                {"role": "assistant", "content": str(tool_input)},
                {
                    "role": "user",
                    "content": CORRECTION_MESSAGE_TEMPLATE.format(
                        tool_input=tool_input, error=detail
                    ),
                },
            ]

    raise RuntimeError(
        f"فشل نداء الأداة بعد {max_attempts} محاولة؛ آخر خطأ — {errors[-1]}"
    )


def _default_tool_input_model(messages: list[dict]) -> str:
    """نموذج المشروع في صورة callable بسيط يعيد نص المدخل مجرَّدًا."""
    content = get_llm().invoke(messages).content
    if isinstance(content, list):
        content = " ".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return str(content).strip()


def run_reliability_task(task_fn, *args, **kwargs):
    """ينفّذ مهمة صمودٍ واحدة داخل سياق runnable مؤقت ويعيد ناتجها.

    مهام ``@task`` لا تُنادى خارج entrypoint (السبايك: ``RuntimeError:
    Called get_config outside of a runnable context``). فبدل أن يرتجل كلُّ
    اختبارٍ وكلُّ خلية نوتبوك سقالتَه، يسكن عقد الاستدعاء هنا مُختبَرًا.

    الوسائط تُمرَّر بالإغلاق لا في حمولة الـentrypoint: الحمولة تُسلسَل
    للـcheckpointer، ودالة الجلب المحقونة ليست قابلة للتسلسل.
    """

    @entrypoint(checkpointer=InMemorySaver())
    def _runner(_payload: dict):
        return task_fn(*args, **kwargs).result()

    return _runner.invoke({}, {"configurable": {"thread_id": "reliability-run"}})
