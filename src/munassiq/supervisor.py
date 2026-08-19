"""مشرف «المُنسِّق» — يوجّه بقرار النموذج لا بسلسلة شروط.

المشرف هنا نموذجٌ يملك أداة ``transfer_to_<name>`` لكل عامل، فالتوجيه قرارٌ
يتخذه النموذج ويظهر أثره في الرسائل نداءَ تسليمٍ صريحًا. هذا هو الفرق بين
«توجيه بالنموذج» و`if "احجز" in request`.

وprompt المشرف يمنعه صراحةً من الإجابة المباشرة: **لا تجب بنفسك أبدًا**.
بغير هذا المنع يميل النموذج إلى تلبية الطلب من عنده — فيخرج جوابٌ معقول
بلا أي نداء أداة، وهو بالضبط ما يبطل الدليل ويترك التقويم فارغًا.
"""

from langgraph_supervisor import create_supervisor

from munassiq.config import get_llm
from munassiq.workers import (
    build_calendar_agent,
    build_correspondence_agent,
    build_knowledge_agent,
)

SUPERVISOR_PROMPT = (
    "أنت مُنسِّق مكتب جمعية المحتوى الإسلامي. دورك التوجيه فقط: "
    "فوّض كل طلب إلى العامل المختص به ولا تجب بنفسك أبدًا، "
    "ولا تنفّذ أي طلب مباشرةً ولو بدا لك سهلًا. "
    "طلبات حجز المواعيد وعرض التقويم إلى calendar_agent، "
    "وصياغة الرسائل والبريد إلى correspondence_agent، "
    "والأسئلة عن سياسات الجمعية وإجراءاتها وأدلتها إلى knowledge_agent. "
    "فوّض إلى عامل واحد في كل مرة، ومرّر له الطلب بتفاصيله كاملة كما وردت. "
    "وبعد أن يردّ العامل، انقل جوابه كاملًا إلى المستخدم بلا اختصار ولا "
    "إعادة صياغة، ولا تضف من عندك شيئًا. "
    # قاعدة التوقف الصريحة: بعض المستضيفين يجعل النموذج يعيد التفويض بعد
    # عودة العامل فتتكرر التحويلات (رُصد عبر OpenRouter) — النص التالي يقطعها.
    "قاعدة صارمة: حوّل الطلب الواحد مرةً واحدة فقط — إذا رجع إليك العامل "
    "بجواب فقد انتهى دورك في التوجيه: أجب المستخدم فورًا بجواب العامل ولا "
    "تستدعِ أي أداة تحويل مرة ثانية لنفس الطلب أبدًا."
)


def build_supervisor(checkpointer=None):
    """يبني غراف المشرف مع عمّاله ويعيده مُصرَّفًا جاهزًا للاستدعاء.

    Args:
        checkpointer: مخزن نقاط الحفظ للمحادثات متعددة الأدوار. يُمرَّر إلى
            ``compile`` فقط حين لا يكون ``None``، فالغراف بلا ذاكرة يظل
            قابلًا للبناء والاختبار بلا أي بنية تحتية.
    """
    agents = [
        build_calendar_agent(),
        build_correspondence_agent(),
        build_knowledge_agent(),
    ]
    graph = create_supervisor(
        agents=agents,
        model=get_llm(),
        prompt=SUPERVISOR_PROMPT,
        # full_history: يرى المشرف رسائل العامل كاملة (جوابه الفعلي لا مجرد
        # إيصال التحويل) — بدونها كان الرد النهائي أحيانًا نص السباكة
        # «Successfully transferred…» بدل جواب العامل.
        output_mode="full_history",
    )
    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()
