"""اختبار بوابة فحص التسرب — الشريحة 9، بلا شبكة ولا نموذج.

البوابة نفسها يجب أن تُختبر، وإلا صارت طقسًا: سكربتٌ يخرج بصفر دائمًا يبدو
ناجحًا وهو لا يفحص شيئًا. فثلاثة أسئلة:

1. **لا إنذار كاذب**: ملف نظيف يمرّ — وإلا عُطِّلت البوابة بعد أول إزعاج.
2. **يُمسك فعلًا**: ملف فيه نمط مفتاح يسقط — والقيمة **لا تظهر** في التقرير.
3. **الواقع الحالي**: النوتبوك المؤلَّف في هذه الشريحة يمرّ كما هو.

**قاعدة صياغة هذا الملف نفسه**: لا يُكتب فيه أي نمطٍ حرفيًا — هو ملف متتبَّع
في git، فبادئةُ مفتاحٍ كاملة مكتوبة هنا تجعل البوابة تسقط على اختبارها. لذلك
المفتاح المزيف يُركَّب في زمن التشغيل من بادئةٍ وذيلٍ منفصلين.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ‏tools/ ليست حزمة مثبَّتة — تُضاف إلى مسار الاستيراد كما في verify_trace.py.
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import leak_scan  # noqa: E402  بعد ضبط sys.path

NOTEBOOK = PROJECT_ROOT / "munassiq_capstone.ipynb"

# مفتاح مزيف يُركَّب في زمن التشغيل: البادئة وحدها لا تطابق النمط (يشترط 10
# محارف بعدها)، فلا يتسرب إلى بايتات هذا الملف نمطٌ كامل يسقط البوابة عليه.
FAKE_KEY = "gsk" + "_" + "A1b2C3d4E5f6G7h8"

CLEAN_TEXT = "سطر عربي نظيف بلا مفاتيح ولا مسارات ولا أسماء.\n"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_clean_file_passes(tmp_path):
    """ملف نظيف لا يُنتج أي تطابق — البوابة لا تُطلق إنذارًا كاذبًا."""
    clean = _write(tmp_path, "clean.txt", CLEAN_TEXT)

    findings = leak_scan.scan_paths([clean], username="")

    assert findings == [], f"ملف نظيف أنتج تطابقات: {findings!r}"


def test_fake_key_is_caught_without_quoting_it(tmp_path):
    """مفتاح مزيف يسقط الملف — والتقرير يذكر الوسم لا القيمة.

    التأكيد الثاني هو لبّ قرار الأمن: تقريرٌ يقتبس السطر المتسرِّب يصير هو
    نفسه تسريبًا حين يُلصق في سجل أو كوميت.
    """
    leaky = _write(tmp_path, "leaky.txt", f"KEY={FAKE_KEY}\n")

    findings = leak_scan.scan_paths([leaky], username="")

    assert findings, "نمط المفتاح لم يُلتقط — البوابة لا تفحص شيئًا"
    assert all(name == "leaky.txt" for name, _ in findings), (
        f"اسم الملف في التقرير ليس النسبي/المجرد: {findings!r}"
    )
    report = " ".join(f"{name} {label}" for name, label in findings)
    assert FAKE_KEY not in report, (
        f"قيمة المفتاح ظهرت في التقرير — التقرير نفسه صار تسريبًا: {report!r}"
    )


def test_username_and_windows_path_are_caught(tmp_path):
    """اسم المستخدم ومسار ويندوز — بصورتيه الخام والمهرَّبة في JSON."""
    named = _write(tmp_path, "named.txt", "المسار: /home/hidden-user/file\n")
    findings = leak_scan.scan_paths([named], username="hidden-user")
    assert [label for _, label in findings] == [leak_scan.USERNAME_LABEL], (
        f"اسم المستخدم لم يُلتقط وحده: {findings!r}"
    )

    # الصورتان: خام في نص، ومهرَّبة بشرطتين كما تُخزَّن داخل JSON النوتبوك.
    raw_path = _write(tmp_path, "raw.txt", "C:" + "\\" + "Users\\x\n")
    escaped_path = _write(tmp_path, "escaped.json", '{"p": "C:' + "\\\\" + 'Users"}')

    for target in (raw_path, escaped_path):
        labels = [label for _, label in leak_scan.scan_paths([target], username="")]
        assert any("C:" in label for label in labels), (
            f"مسار المستخدم لم يُلتقط في {target.name}: {labels!r}"
        )


def test_self_and_docs_plan_are_excluded():
    """الاستثناءان الموثقان: هذا السكربت نفسه، وسجلات docs/plan افتراضيًا."""
    scanner = PROJECT_ROOT / "tools" / "leak_scan.py"
    assert leak_scan.is_excluded(scanner), (
        "سكربت الفحص لا يستثني نفسه — سيسقط على الأنماط التي يحملها بحكم عمله"
    )

    plan_dir = PROJECT_ROOT / "docs" / "plan"
    plan_files = sorted(plan_dir.rglob("*.md"))
    assert plan_files, f"لا ملفات خطة تحت {plan_dir.name} — الاستثناء غير مفحوص"

    assert leak_scan.is_excluded(plan_files[0]), "docs/plan لم يُستثنَ افتراضيًا"
    assert not leak_scan.is_excluded(plan_files[0], include_docs=True), (
        "‏--include-docs لا يعكس الاستثناء — العلَم بلا أثر"
    )


def test_notebook_and_tracked_files_are_clean():
    """الحالة الراهنة نظيفة: النوتبوك المؤلَّف وكل متتبَّع في git."""
    assert NOTEBOOK.is_file(), f"النوتبوك غائب عن جذر المشروع: {NOTEBOOK.name}"

    findings = leak_scan.scan_paths(leak_scan.default_targets())

    assert findings == [], (
        "فحص التسرب أسقط ملفات (الأوسمة فقط، بلا سطور): "
        f"{sorted({(name, label) for name, label in findings})}"
    )
