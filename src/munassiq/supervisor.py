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
from munassiq.workers import build_calendar_agent, build_correspondence_agent

SUPERVISOR_PROMPT = (
    "أنت مُنسِّق مكتب جمعية المحتوى الإسلامي. دورك التوجيه فقط: "
    "فوّض كل طلب إلى العامل المختص به ولا تجب بنفسك أبدًا، "
    "ولا تنفّذ أي طلب مباشرةً ولو بدا لك سهلًا. "
    "طلبات حجز المواعيد وعرض التقويم إلى calendar_agent، "
    "وصياغة الرسائل والبريد إلى correspondence_agent. "
    "فوّض إلى عامل واحد في كل مرة، ومرّر له الطلب بتفاصيله كاملة كما وردت. "
    "وبعد أن يردّ العامل، انقل جوابه كاملًا إلى المستخدم بلا اختصار ولا "
    "إعادة صياغة، ولا تضف من عندك شيئًا."
)


def build_supervisor(checkpointer=None):
    """يبني غراف المشرف مع عمّاله ويعيده مُصرَّفًا جاهزًا للاستدعاء.

    Args:
        checkpointer: مخزن نقاط الحفظ للمحادثات متعددة الأدوار. يُمرَّر إلى
            ``compile`` فقط حين لا يكون ``None``، فالغراف بلا ذاكرة يظل
            قابلًا للبناء والاختبار بلا أي بنية تحتية.
    """
    agents = [build_calendar_agent(), build_correspondence_agent()]
    graph = create_supervisor(
        agents=agents,
        model=get_llm(),
        prompt=SUPERVISOR_PROMPT,
    )
    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()
