"""عمّال «المُنسِّق» — وكيلٌ لكل اختصاص، وأدواته وحدها في متناوله.

كل عامل هنا وكيل ReAct كامل: نموذج + مجموعة أدوات ضيّقة + تعليمات عربية
تحصره في اختصاصه. الفصل مقصود — عامل التقويم لا يرى أداة البريد، فلا يقدر
أن ينحرف إليها أصلًا، وهذا حصرٌ بالبنية لا بالرجاء في نص التعليمات.

الاسم (``name``) **إلزامي** لكل عامل: منه يشتقّ المشرف أداة التسليم
``transfer_to_<name>``. عاملٌ بلا اسم يعني مشرفًا بلا يدٍ يسلّم بها.

عامل المعرفة (RAG) يُضاف في الشريحة 4 كدالة ``build_*_agent`` أخرى، ويُدرج
في قائمة المشرف — لا تعديل على ما هنا حين يأتي.
"""

from langgraph.graph.state import CompiledStateGraph

from langchain.agents import create_agent

from munassiq.config import get_llm
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
