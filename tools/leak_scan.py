"""بوابة فحص التسرب — تمنع خروج مفتاح أو مسار جهاز أو اسم إلى ريبو عام.

يُشغَّل من جذر المشروع::

    .venv\\Scripts\\python.exe tools\\leak_scan.py

بلا وسائط يفحص هدفين: النوتبوك ``munassiq_capstone.ipynb`` وكل ملف
**متتبَّع في git** (``git ls-files``). ويقبل مسارات صريحة بدلًا من ذلك.

**لماذا بايتات خامًا لا نصًّا**: النوتبوك ملف JSON، فما يُطبع في خلية يُخزَّن
مهرَّبًا (``C:\\Users`` يصير ``C:\\\\Users``) وقد يُخزَّن العربي هروبًا
سداسيًا. القراءة بايتاتٍ خامًا مع أنماطٍ تحتمل الشرطة المضاعفة تلتقط الصورتين،
والقراءة نصًّا بترميزٍ مفترض قد تسقط عند أول بايت لا يوافقه.

**ما لا يُطبع**: لا يخرج من هنا سطرٌ ولا مقتطف ولا النص المطابق — اسم الملف
واسم النمط فقط. تقريرٌ يقتبس السطر المتسرِّب يصير هو نفسه تسريبًا حين يُلصق
في سجل أو كوميت.

**استثناءان موثقان**:

1. ``docs/plan/`` — سجلات التخطيط والنقد الداخلية: تناقش الأنماط بأسمائها
   (وفيها قائمة الأنماط نفسها حرفيًا)، وليست جزءًا من التسليم المنشور.
   تُستثنى افتراضيًا، والعلَم ``--include-docs`` يعكس ذلك فتُفحص معها.
2. **هذا الملف نفسه** — يحوي الأنماط بحكم وظيفته، فلولا استثناؤه لأسقط نفسه.

**ولماذا لا يُزرع اسم المستخدم حرفيًا هنا**: كتابة الاسم في ملفٍ متتبَّع هي
عين التسريب الذي تمنعه هذه البوابة — يُشتق من بيئة الجهاز عند التشغيل
(``USERNAME``/``USER``/اسم مجلد المنزل)، ويُتجاوز عند الحاجة بـ``--username``.
والتقرير يذكر وسم النمط «اسم مستخدم الجهاز» لا قيمته.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# جذر المشروع مشتق من موقع هذا الملف: tools/leak_scan.py -> tools -> الجذر.
# لا مسار مطلق حرفي مزروع في الكود.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# هذا الملف — يُستثنى دائمًا لأنه يحوي الأنماط بحكم وظيفته.
SELF_PATH = Path(__file__).resolve()

# النوتبوك هدفٌ صريح: قد يكون غير متتبَّع بعد في git وهو أخطر ملف في المشروع
# (يحمل مخرجات تشغيل حقيقية).
NOTEBOOK_NAME = "munassiq_capstone.ipynb"

# مجلد السجلات الداخلية المستثنى افتراضيًا.
DOCS_PLAN_PREFIX = "docs/plan/"

# الأنماط الثابتة — كلها ASCII، فتلتقط النص الخام والنص المهرَّب في JSON معًا.
#
# * مفاتيح Groq وLangSmith: البادئة وحدها ليست سرًّا، وطول 10 فأكثر يمنع
#   مطابقة ذِكرٍ عابر للبادئة في وثيقة.
# * مسار المستخدم على ويندوز: ``[\\/]{1,2}`` تحتمل ``C:\\Users`` الخام
#   و``C:\\\\Users`` المهرَّب في JSON و``C:/Users`` بالشرطة الأمامية.
STATIC_PATTERNS: tuple[tuple[str, bytes], ...] = (
    ("مفتاح Groq (gsk_)", rb"gsk_[A-Za-z0-9]{10,}"),
    ("مفتاح LangSmith (lsv2_)", rb"lsv2_[A-Za-z0-9_]{10,}"),
    ("مفتاح OpenRouter (sk-or-)", rb"sk-or-[A-Za-z0-9-]{10,}"),
    ("مفتاح Google (AIza)", rb"AIza[A-Za-z0-9_-]{10,}"),
    ("مفتاح Mistral في سياق تعيين", rb"MISTRAL_API_KEY\s{0,2}=\s{0,2}[A-Za-z0-9]{8,}"),
    ("مسار مستخدم على القرص (C:\\Users)", rb"[Cc]:[\\/]{1,2}[Uu]sers"),
    ("اسم الجمعية بالإنجليزية", rb"Islamic\s{1,4}Content\s{1,4}Association"),
)

# وسم نمط اسم المستخدم — يُطبع الوسم لا القيمة.
USERNAME_LABEL = "اسم مستخدم الجهاز"

# اسمٌ أقصر من ثلاثة أحرف يطابق كل شيء تقريبًا — يُهمَل بدل أن يغرق التقرير.
MIN_USERNAME_LENGTH = 3


def detect_username() -> str:
    """يشتق اسم مستخدم الجهاز من البيئة — بلا أي اسم مزروع في هذا الملف."""
    for variable in ("USERNAME", "USER", "LOGNAME"):
        value = (os.environ.get(variable) or "").strip()
        if value:
            return value
    return Path.home().name


def build_patterns(username: str | None = None) -> list[tuple[str, re.Pattern[bytes]]]:
    """يبني قائمة (وسم، نمط مُصرَّف) — الثوابت ثم اسم المستخدم إن صلح.

    Args:
        username: اسم المستخدم المراد البحث عنه. ``None`` يعني الاشتقاق من
            البيئة، والنص الفارغ يعني إسقاط نمط الاسم أصلًا.
    """
    patterns = [
        (label, re.compile(expression)) for label, expression in STATIC_PATTERNS
    ]

    name = detect_username() if username is None else username.strip()
    if len(name) >= MIN_USERNAME_LENGTH:
        # حدود كلمات \b حول الاسم: المطلوب مسك «abdul» في مسار مثل
        # C:\Users\abdul\ لا داخل اسم علم أطول مثل «Abdulaziz» — اسم صاحب
        # المشروع مقصودٌ نشره، واسم مستخدم الجهاز وحده هو التسرب.
        patterns.append(
            (
                USERNAME_LABEL,
                re.compile(
                    rb"\b" + re.escape(name.encode("utf-8")) + rb"\b",
                    re.IGNORECASE,
                ),
            )
        )
    return patterns


def _relative(path: Path) -> str:
    """المسار نسبةً لجذر المشروع متى أمكن — وإلا فاسم الملف وحده.

    الخروج إلى اسم الملف وحده مقصود: طباعة مسارٍ مطلق في تقرير التسرب تكشف
    بنية الجهاز، وهو بالضبط أحد الأنماط التي تلاحقها هذه البوابة.
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.name


def is_excluded(path: Path, *, include_docs: bool = False) -> bool:
    """هل يُستثنى هذا المسار من الفحص؟ (الاستثناءان الموثقان وحدهما)."""
    if path.resolve() == SELF_PATH:
        return True
    if not include_docs and _relative(path).startswith(DOCS_PLAN_PREFIX):
        return True
    return False


def scan_file(path: Path, patterns) -> list[str]:
    """يعيد أوسمة الأنماط المطابِقة في ملف واحد — بلا أي مقتطف من محتواه."""
    try:
        blob = path.read_bytes()
    except OSError:
        # ملف اختفى بين ``git ls-files`` والقراءة، أو لا صلاحية عليه.
        return []
    return [label for label, pattern in patterns if pattern.search(blob)]


def git_tracked_files(root: Path = PROJECT_ROOT) -> list[Path]:
    """يعيد الملفات المتتبَّعة في git، أو قائمة فارغة إن تعذّر النداء."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        # لا git أو ليس ريبو — الأهداف الصريحة تبقى مفحوصة.
        return []
    names = completed.stdout.decode("utf-8", errors="replace").split("\0")
    return [root / name for name in names if name]


def default_targets(root: Path = PROJECT_ROOT) -> list[Path]:
    """الأهداف الافتراضية: النوتبوك (ولو غير متتبَّع) وكل متتبَّع في git."""
    targets = [root / NOTEBOOK_NAME]
    targets.extend(git_tracked_files(root))
    return targets


def scan_paths(
    paths,
    *,
    username: str | None = None,
    include_docs: bool = False,
) -> list[tuple[str, str]]:
    """يفحص مسارات ويعيد قائمة (الملف، وسم النمط) لكل تطابق.

    قائمة فارغة تعني نظافة الأهداف. لا يعود من هنا سطرٌ ولا نصٌّ مطابق.
    """
    patterns = build_patterns(username)
    findings: list[tuple[str, str]] = []
    seen: set[Path] = set()

    for raw in paths:
        path = Path(raw)
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)

        if not path.is_file() or is_excluded(path, include_docs=include_docs):
            continue

        for label in scan_file(path, patterns):
            findings.append((_relative(path), label))

    return findings


def main(argv: list[str] | None = None) -> int:
    """يفحص الأهداف ويطبع تقريرًا مقتضبًا؛ 1 عند أي تطابق و0 عند النظافة."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            # سطر أوامر ويندوز يفتح بترميز لا يسع العربية.
            reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="فحص تسرب المفاتيح والمسارات والأسماء قبل الدفع."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="ملفات تُفحص بدل الأهداف الافتراضية (النوتبوك + متتبَّع git).",
    )
    parser.add_argument(
        "--include-docs",
        action="store_true",
        help=f"يفحص {DOCS_PLAN_PREFIX} أيضًا (مستثنى افتراضيًا: سجلات داخلية).",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="اسم المستخدم المبحوث عنه؛ افتراضه مشتق من البيئة.",
    )
    args = parser.parse_args(argv)

    targets = [Path(p) for p in args.paths] if args.paths else default_targets()
    findings = scan_paths(
        targets, username=args.username, include_docs=args.include_docs
    )

    scanned = sum(
        1
        for path in targets
        if path.is_file() and not is_excluded(path, include_docs=args.include_docs)
    )

    if not findings:
        print(f"[✓] فحص التسرب نظيف — {scanned} ملفًا مفحوصًا، لا تطابق.")
        return 0

    print(f"[x] فحص التسرب أسقط {len(findings)} تطابقًا (السطور لا تُطبع):")
    for name, label in findings:
        print(f"    {name}  ←  {label}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
