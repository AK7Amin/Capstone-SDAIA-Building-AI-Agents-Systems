"""محاكاة تقييم المصحح: يرسل الروبرك + أدلة المشروع إلى DeepSeek عبر OpenRouter.

أداة تحقق داخلية — ليست جزءًا من تسليم المشروع. تُشغَّل يدويًا:
    .venv/Scripts/python tools/grade_with_deepseek.py [model]
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

MODEL = sys.argv[1] if len(sys.argv) > 1 else "deepseek/deepseek-chat"

RUBRIC_PATH = (
    PROJECT_ROOT.parent / "materials" / "L01" / "capstone_prep.qmd"
)


def notebook_as_text(path: Path, max_output_chars: int = 700) -> str:
    """يفرد النوتبوك نصًا: markdown كما هو، والكود مع مخرجاته المحفوظة."""
    nb = json.loads(path.read_text(encoding="utf-8"))
    parts = []
    for i, cell in enumerate(nb["cells"]):
        src = "".join(cell["source"])
        if cell["cell_type"] == "markdown":
            parts.append(f"--- [markdown cell {i}] ---\n{src}")
        else:
            outs = []
            for o in cell.get("outputs", []):
                if o.get("output_type") == "stream":
                    outs.append("".join(o.get("text", [])))
                elif "text/plain" in o.get("data", {}):
                    outs.append("".join(o["data"]["text/plain"]))
            out_text = "\n".join(outs)[:max_output_chars]
            parts.append(
                f"--- [code cell {i}, execution_count="
                f"{cell.get('execution_count')}] ---\n{src}\n"
                f"[SAVED OUTPUT]:\n{out_text}"
            )
    return "\n\n".join(parts)


def main() -> None:
    rubric = RUBRIC_PATH.read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    writeup = (PROJECT_ROOT / "docs" / "WRITEUP-DRAFT.md").read_text(encoding="utf-8")
    nb_text = notebook_as_text(PROJECT_ROOT / "munassiq_capstone.ipynb")

    prompt = f"""You are the capstone grader for the SDAIA Academy course
"Building AI Agent Systems". Grade STRICTLY against the official rubric below:
8 sections, 100 points total, pass at 60, and no single section may score
below 40% of its points. Be a tough, evidence-driven grader: a claim only
counts if the submitted evidence (saved notebook outputs, tests referenced,
files listed) actually shows it. Where evidence is weak, say exactly what is
missing.

=== OFFICIAL RUBRIC (capstone_prep) ===
{rubric}

=== SUBMISSION: README.md ===
{readme}

=== SUBMISSION: WRITE-UP ===
{writeup}

=== SUBMISSION: THE NOTEBOOK (cells with their SAVED outputs) ===
{nb_text}

Return your evaluation as:
1. A table: section | points awarded / max | one-line justification citing
   specific evidence you saw (cell number, output text, or file).
2. Any section at risk of the 40% floor.
3. Total score and pass/fail.
4. The three toughest questions you would ask this student in the defense.
5. Anything that looked like a claim NOT backed by visible evidence.
"""

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    verdict = response.choices[0].message.content
    out_path = PROJECT_ROOT / "docs" / "plan" / "2026-08-18-munassiq-capstone" / "deepseek-grading.md"
    out_path.write_text(
        f"# محاكاة تقييم المصحح — {MODEL}\n\n{verdict}\n", encoding="utf-8"
    )
    print(f"WRITTEN: {out_path.name}")
    print(verdict[:600])


if __name__ == "__main__":
    main()
