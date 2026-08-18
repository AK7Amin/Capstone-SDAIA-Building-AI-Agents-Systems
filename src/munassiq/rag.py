"""خط RAG لـ«المُنسِّق» — فهرسة وثائق الجمعية التركيبية وأداة البحث فيها.

ثلاثة قرارات مثبتة بسبايك، مكتوبة هنا كما ثبتت لا كما هو شائع:

* **التضمين متعدد اللغات إلزامًا**: موديل fastembed الافتراضي إنجليزي
  (`bge-small-en`) وفشل مع العربية في السبايك — استرجع مقاطع لا صلة لها
  بالسؤال. البديل المعتمد ``paraphrase-multilingual-MiniLM-L12-v2``. تحذير
  الإهمال من ``langchain_community`` مقبول ولا يُداوى بتغيير الموديل.
* **الـcollection تُحذف قبل كل بناء** (قرار نقد الجولة 1): اسمٌ ثابت بلا
  حذف يعني أن كل نداء ``build_retriever`` يضيف نسخة أخرى من المقاطع نفسها
  إلى الفهرس نفسه، فيمتلئ أعلى الترتيب بمكرَّرات المقطع الواحد ويُزاح ما
  عداه. العميل هنا ``EphemeralClient`` في الذاكرة — لا يخلّف شيئًا على
  القرص أصلًا — ومع ذلك يُحذف الـcollection صراحةً لأن العميل مشترك على
  مستوى الموديول ويعمّر عبر النداءات.
* **الإحماء منفصل عن القياس**: أول نداء تضمين قد ينزّل الموديل، وهو زمن
  تحميل لا زمن استرجاع. :func:`warm_up_embeddings` تعزله عمّا يُقاس.

كل الوثائق تحت ``data/corpus/`` **تركيبية مؤلَّفة لغرض التدريب** — لا وثيقة
جمعية حقيقية تدخل أي نموذج أو خدمة تضمين (R021).
"""

from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter

# جذر المشروع مشتق من موقع الملف: src/munassiq/rag.py -> src/munassiq -> src
# -> الجذر. لا مسار مطلق حرفي مزروع في الكود.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"

# الموديل متعدد اللغات — الافتراضي الإنجليزي فشل مع العربية (سبايك).
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# مقاسات التقسيم المثبتة بالسبايك: مقاطع تحتفظ بالفقرة كاملة مع تراكب
# يمنع قطع الحقيقة على حدّ المقطع.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

COLLECTION_NAME = "munassiq_policies"

# التضمينات والعميل حالة على مستوى الموديول: تحميل الموديل مرة واحدة لكل
# عملية، والعميل في الذاكرة يعمّر عبر النداءات (ولذلك يلزم حذف الـcollection).
_EMBEDDINGS: FastEmbedEmbeddings | None = None
_CLIENT: chromadb.ClientAPI | None = None
_RETRIEVER = None


def get_embeddings() -> FastEmbedEmbeddings:
    """يعيد كائن التضمين المشترك، ويبنيه عند أول نداء."""
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        _EMBEDDINGS = FastEmbedEmbeddings(model_name=EMBEDDING_MODEL)
    return _EMBEDDINGS


def warm_up_embeddings() -> None:
    """يملأ كاش الموديل بنداء تضمين واحد صغير.

    يُستدعى قبل أي قياس أو تأكيد: أول نداء قد ينزّل الموديل ويحمّله، وهذا
    زمن تحميل لا زمن استرجاع.
    """
    get_embeddings().embed_query("إحماء")


def _get_client() -> chromadb.ClientAPI:
    """عميل chroma في الذاكرة — لا يكتب شيئًا على القرص."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = chromadb.EphemeralClient(
            Settings(anonymized_telemetry=False, allow_reset=True)
        )
    return _CLIENT


def load_corpus() -> list[Document]:
    """يحمّل وثائق ``data/corpus/*.md`` بترميز utf-8 مع اسم الملف مصدرًا."""
    documents = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        documents.append(
            Document(
                page_content=path.read_text(encoding="utf-8"),
                metadata={"source": path.name},
            )
        )
    if not documents:
        raise FileNotFoundError(f"لا وثائق md في مجلد الكوربس: {CORPUS_DIR}")
    return documents


def split_corpus(documents: list[Document]) -> list[Document]:
    """يقسّم الوثائق مقاطع 500/50 مع الاحتفاظ بـmetadata المصدر."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def build_retriever(k: int = 3):
    """يبني الفهرس من صفر ويعيد مسترجعًا بأعلى ``k`` مقاطع.

    الـcollection ثابتة الاسم تُحذف أولًا إن وُجدت ثم يعاد إنشاؤها، فبناءان
    متتاليان يعطيان فهرسًا واحدًا لا فهرسًا مضاعفًا.
    """
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        # لا collection بهذا الاسم بعد — أول بناء في هذه العملية.
        pass

    chunks = split_corpus(load_corpus())
    store = Chroma.from_documents(
        chunks,
        get_embeddings(),
        collection_name=COLLECTION_NAME,
        client=client,
    )
    return store.as_retriever(search_kwargs={"k": k})


def _shared_retriever():
    """مسترجع واحد تشترك فيه نداءات الأداة — لا يعاد بناء الفهرس كل سؤال."""
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = build_retriever()
    return _RETRIEVER


def format_passages(documents: list[Document]) -> str:
    """يصوغ المقاطع بنصها ومصدرها — نصًّا يقرؤه النموذج ويقدر أن يعزو إليه."""
    if not documents:
        return "لا أجد في وثائق الجمعية مقطعًا يتعلق بهذا السؤال."
    blocks = [
        f"[مصدر: {doc.metadata.get('source', 'غير معروف')}]\n{doc.page_content}"
        for doc in documents
    ]
    return "\n\n---\n\n".join(blocks)


@tool
def search_policies(query: str) -> str:
    """يبحث في سياسات الجمعية وإجراءاتها ويعيد المقاطع ذات الصلة بمصادرها.

    Args:
        query: السؤال أو العبارة المراد البحث عنها في وثائق الجمعية.
    """
    return format_passages(_shared_retriever().invoke(query))


def build_knowledge_tool():
    """يعيد أداة البحث في وثائق الجمعية — الأداة الوحيدة لعامل المعرفة."""
    return search_policies
