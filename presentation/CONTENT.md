# Munassiq — محتوى العرض التقديمي للمشروع الختامي

> بنية STAR على تصميم عرض onboarding-agent المرجعي: فواصل كحلية بحرف ذهبي،
> محتوى أبيض، جداول برؤوس كحلية، صناديق تنبيه ملونة، أرقام مُتحقَّقة بمصادرها،
> قسم «Not built»، وملحق أسئلة متوقعة. سكربت الإلقاء العربي الموقوت في ملاحظات
> كل شريحة (الزمن الكلي للجزء الأساسي ≈ 5 دقائق).

---

## Slide 1 — Title (dark navy)
**Munassiq (المُنسِّق) — Association Office Assistant**
A supervisor and three specialist agents on a LangGraph Functional API core.
Every irreversible act waits for a human. Every claim has a captured run behind it.
- Footer: SDAIA Academy — Building AI Agent Systems · Cohort 16–20 August 2026 · Riyadh · Capstone Track A
- **Abdulaziz Mulia (عبدالعزيز مُليا)** — github.com/AK7Amin

**Notes [00:00 · 25ث]:** السلام عليكم. مشروعي «المُنسِّق»: مساعد مكتب جمعية —
مشرف يوزع على ثلاثة عمال متخصصين، بذاكرة تعيش عبر المحادثات، وبوابة موافقة
بشرية قبل أي فعل لا يرتد. كل رقم في هذا العرض وراءه تشغيلة حقيقية ملتقطة
في المستودع.

## Slide 2 — S divider (dark, gold "S", "Situation")
**Notes [00:25 · 8ث]:** أعرض على بنية STAR: الوضع، فالمهمة، فالبناء، فالنتيجة.

## Slide 3 — The office inbox is scattered, manual, and unforgiving
Table (what arrives daily → what happens today → the cost):
- سؤال سياسة: «كم مدة مراجعة المحتوى؟» → يبحث موظف في الوثائق يدويًا → دقائق تضيع، وإجابات متفاوتة
- طلب حجز اجتماع → تقويم يُحدَّث يدويًا → نسيان وتعارضات
- بريد للمتطوعين → يُصاغ ويُرسل مباشرة → **رسالة خاطئة لا ترتد**
Right column (What breaks in practice):
- The knowledge lives in documents nobody re-reads.
- Preferences repeat in every conversation — nothing remembers.
- The riskiest step (sending) is the least guarded.
Callout (red): الإرسال الخاطئ باسم الجمعية هو الخطأ الذي لا تصلحه معذرة.

**Notes [00:33 · 40ث]:** مكتب الجمعية يستقبل ثلاثة أنواع طلبات يوميًا: أسئلة
سياسات، وحجوزات، ومراسلات. كلها يدوية، لا شيء يتذكر تفضيلات أحد، وأخطر
خطوة — الإرسال باسم الجمعية — هي الأقل حراسة.

## Slide 4 — Why a plain chatbot makes it worse
Three numbered failure modes:
1. **It answers policy from its imagination.** No retrieval → confident, wrong, unattributable.
2. **It forgets across threads.** State dies with the tab; "our preferred day" is re-asked forever.
3. **It acts without a gate.** A model that can draft can send — and sending is irreversible.
Design consequences (3 tinted boxes): retrieval before answering · memory must outlive the thread · interrupt() before anything irreversible.

**Notes [01:13 · 30ث]:** روبوت محادثة ساذج يزيد الطين بلة: يجيب عن السياسات
من خياله، وينسى كل شيء بين محادثة وأخرى، ويرسل بلا إذن. من هنا جاءت
القرارات المعمارية الثلاثة المقابلة.

## Slide 5 — T divider (dark, gold "T", "Task")
**Notes [01:43 · 6ث]:** المهمة والقيود التي التزمناها.

## Slide 6 — The brief, and the constraints we refused to relax
Left: rubric = acceptance criteria table (8 sections & points, pass 60, **no section below 40%**).
Right — five constraints written before any code:
- Real tool calls only — a function that ignores its arguments is not a tool.
- Routing decided by the **LLM** (structured output) — keyword matching is not routing.
- Long-term memory = a **separate Store**, proven across threads — a growing chat list doesn't count.
- interrupt() **and** resume both demonstrated, with the human's text passing verbatim.
- All corpus documents synthetic (R021) — no real association data near any model.

**Notes [01:49 · 35ث]:** الروبرك نفسه صار معيار القبول: ثمانية أقسام ولا قسم
تحت 40%. وكتبنا خمسة قيود قبل أول سطر كود — أهمها: التوجيه قرار النموذج
لا مطابقة كلمات، والذاكرة الطويلة مخزن منفصل يُثبَت عبر المحادثات، ووثائق
تركيبية بالكامل التزامًا بخصوصية الجمعية.

## Slide 7 — A divider (dark, gold "A", "Action")
**Notes [02:24 · 6ث]:** البناء: الغراف، العمال، الذاكرة، البوابة.

## Slide 8 — Architecture: one entrypoint, everything else is a task
Diagram (shapes): user → @entrypoint munassiq_app (SqliteSaver + SqliteStore) →
load_memories → detect_and_store_memory → classify_request (TriageDecision) →
[correspondence? → draft (Evaluator-Optimizer) → **interrupt()** → send_final verbatim]
[else → Supervisor → calendar_agent / knowledge_agent / correspondence_agent]
Right bullets:
- The entrypoint body is pure glue — every LLM call and side effect lives inside a @task, so nothing re-executes on resume.
- Supervisor holds no checkpointer; durable state belongs to the entrypoint alone.
- Two named patterns: **Orchestrator-Worker** (supervisor) · **Evaluator-Optimizer** (drafting loop).

**Notes [02:30 · 45ث]:** المعمارية: نقطة دخول وظيفية واحدة تملك الحالة —
checkpointer للسياق القصير وStore دائم للحقائق. جسمها غراء نقي: كل نداء
نموذج داخل @task، وإلا أعيد تنفيذه عند الاستئناف. التصنيف مخرج مهيكل،
والمراسلات تمر بحلقة تقييم قبل بوابة الموافقة، وبقية الطلبات لمشرف
Orchestrator-Worker بثلاثة عمال.

## Slide 9 — Routing is a model decision, printed as proof
Left: TriageDecision (Pydantic): worker ∈ {calendar, knowledge, correspondence} · needs_human_approval · summary — parsed by code, never by `in`.
Right: the captured evidence (mono block):
`كل نداءات الأدوات: ['transfer_to_calendar_agent', 'transfer_back_to_supervisor']`
Callout (green): The round trip is the proof the grader asks for — the LLM chose the worker; the handoff back is expected, not a bug.

**Notes [03:15 · 25ث]:** التوجيه قرار نموذج بمخرج Pydantic يقرؤه الكود.
والدليل المطبوع: نداء التحويل ورجوعه — الرحلتان متوقعتان، وهذا حرفيًا ما
يطلبه المقيم.

## Slide 10 — RAG that actually reads Arabic
- Pipeline: 3 synthetic policy docs → split 500/50 → **multilingual MiniLM (fastembed, local, free)** → Chroma → retrieve.
- The trap we caught by testing: the **default English embedding model silently fails on Arabic** — retrieved unrelated passages; the planted fact test exposed it.
- Verbatim proof: «كم مدة مراجعة المحتوى؟» → top passage contains **«ثلاثة أيام عمل»** from سياسة-النشر.md.
- Architecture choice written up: 2-Step vs **Agentic** vs Hybrid — Agentic fits: the worker decides when to search.

**Notes [03:40 · 35ث]:** خط RAG يقرأ العربية فعلًا — الموديل الافتراضي فشل
بصمت واصطدناه باختبار حقيقة مزروعة: سؤال المدة يسترجع «ثلاثة أيام عمل»
حرفيًا من وثيقة السياسة. والتبرير المكتوب اختار Agentic RAG لأن العامل
هو من يقرر متى يبحث.

## Slide 11 — Memory that survives the thread (screenshot slide)
Image: trace-memory-cross-thread.png (LangSmith run tree + memories_used).
Caption row: write in thread-1 → `store.search()` proves the write → recall in thread-2 with `memories_used` carrying the fact.
Callout: The test asserts on the **Store**, not on the model's phrasing — the hard evidence.

**Notes [04:15 · 25ث]:** الذاكرة الطويلة مخزن SQLite منفصل: نكتب الحقيقة في
محادثة، ونقرؤها من محادثة أخرى مختلفة تمامًا — والـtrace يعرض الحقن في
memories_used. الاختبار يفحص المخزن نفسه لا صياغة النموذج.

## Slide 12 — The human gate: nothing irreversible without approval
Two mono panels: PAUSED (interrupt payload: draft + action) → RESUMED (`Command(resume=...)`).
- The human's edit **is** the sent text — it reaches the outbox byte-for-byte, no model in between.
- Proven three ways: unit (no-LLM mechanics) · integration (live) · notebook (both halves with outputs).
Callout (amber): Pausing but never resuming is the most common half-finished capstone — both halves are captured here.

**Notes [04:40 · 30ث]:** بوابة الإنسان: قبل أي إرسال يقف الغراف بـinterrupt
عارضًا المسودة، ونص المعتمد البشري يصل الصادر حرفيًا بلا مرور على أي نموذج.
الشقان — التوقف والاستئناف — ملتقطان بمخرجيهما.

## Slide 13 — Reliability: four error classes, each with its own answer
Table: Transient → RetryPolicy(max_attempts=3), real object, no sleep loops · LLM-recoverable → error text fed back, bounded · User-fixable → interrupt() · Unexpected → propagate (type+message only, no raw tracebacks).
Bottom strip — provider quirks we caught live (3 mini-boxes):
`-2.0` instead of an object · a message with no `parsed` field · server-side `output_parse_failed` — one retry helper (`invoke_structured`) absorbs all three.

**Notes [05:10 · 30ث]:** الموثوقية: أربع فئات خطأ لكلٍّ علاجها — وأهم درس
حي: المزودون أنفسهم يرمون نزوات مخرج مهيكل؛ رصدنا ثلاثة أشكال فعلية
ولففناها بمعيد محاولة واحد موثق.

## Slide 14 — Evaluator-Optimizer, named and measured
Loop diagram: compose → evaluate (DraftVerdict: score/approved/feedback) → improve → evaluate (≤2 rounds) → interrupt.
Trace numbers (from LangSmith): composing 3.3s · judging up to **21.7s** — the structured judge is ~7× slower than the writer.
Callout: the loop always finishes **before** the human gate — every draft a human sees has been judged.

**Notes [05:40 · 25ث]:** النمط المسمى: Evaluator-Optimizer — صياغة فتقييم
بحكم مهيكل فتحسين، بجولتين كحد أقصى وقبل بوابة الموافقة دائمًا. والـtrace
كشف مفاجأة: الحَكم أبطأ من الكاتب سبع مرات.

## Slide 15 — Observability: the trap, the verifier, the finding
- The env var is **LANGCHAIN_TRACING_V2** — the lookalike misspelling fails silently; our config raises on it, a test enforces the raise.
- wait_for_recent_run(): polling with deadline, prints id/name/status only.
- What the trace actually showed: the judging bottleneck (21.7s vs 3.3s) and the recovery loop's two model calls (35.3s) — findings, not vibes.

**Notes [06:05 · 25ث]:** التتبع: الاسم الصحيح للمتغير محروس باختبار لأن
الخطأ فيه صامت. والقيمة الحقيقية: الـtrace أعطانا قياسات — عنق الزجاجة في
التقييم لا الصياغة.

## Slide 16 — R divider (dark, gold "R", "Result")
**Notes [06:30 · 5ث]:** النتيجة بالأرقام الموثقة.

## Slide 17 — Verified numbers — every one traced to its source
Big stats row: **40** tests (31 offline / 9 live) · **15/15** notebook cells executed, zero errors · **14 passed** closure suite · **~$0** total model cost.
Claims table: claim → verified by (file/log/test) — integration green without xfail → closure-run.log · cross-thread memory → test_memory + trace · verbatim resume → test_hitl + outbox file · leak gate → leak_scan.py exit 0 on 33 files.

**Notes [06:35 · 30ث]:** الأرقام: أربعون اختبارًا، النوتبوك كامل التنفيذ بلا
أخطاء، حزمة الإغلاق 14 ناجحًا، والتكلفة صفر تقريبًا. كل ادعاء في العمود
الأيسر يقابله ملف أو سجل أو اختبار في الأيمن.

## Slide 18 — What production actually taught us (the battle scars)
Timeline of real incidents → engineering responses:
1. Course model returns **404** on our account → spike caught it pre-build → swapped to gpt-oss-120b.
2. Groq free tier exhausted mid-build (200K TPD) → offline/live test split (`-m "not api"`), mechanics proven without models (stub tasks over real infra).
3. Smaller models failed structured output **qualitatively** (mangled tool name; boolean as string) → eliminated by evidence, not preference.
4. Second host's routing varied answers (transfer ping-pong; reasoning leak) → stop rule in prompt + full_history + final evidence captured on the primary provider.
Callout (green): None of this was in the plan. All of it is in the run log.

**Notes [07:05 · 40ث]:** أصدق شريحة في العرض: ما علمتنا إياه البيئة الحقيقية.
نموذج الدورة 404 فاصطاده سبايك مبكر؛ الحصة المجانية نفدت منتصف البناء
ففصلنا الاختبارات الحية وأثبتنا الآليات بلا نماذج؛ النماذج الأصغر سقطت
نوعيًا بالدليل؛ ومستضيف بديل ذبذب السلوك فعالجناه بقاعدة توقف وبالتقاط
الدليل النهائي على المزود الأصلي. كل حادثة موثقة في سجل التشغيل.

## Slide 19 — How it was built — the part that transfers to your projects
- Spikes before plans: risky assumptions burned down with throwaway code against real APIs.
- A four-angle critique (architecture, rubric, security, reliability) before the first line — 8 blockers died on paper.
- Ten vertical slices, each: red test committed → minimal green → central re-verification.
- A leak-scan gate before every push (keys, absolute paths, machine identity) — it once caught the author's own name.
- Final review: mechanical pass + two-axis deep review → 5 more blockers fixed.

**Notes [07:45 · 30ث]:** طريقة البناء نفسها قابلة للنقل: سبايكات قبل الخطة،
نقد رباعي قبل الكود أسقط ثمانية عوائق على الورق، عشر شرائح رأسية لكل منها
اختبار أحمر فأخضر، وبوابة فحص تسرب قبل كل دفع — أمسكت مرة اسمي أنا.

## Slide 20 — Where the grader finds the proof
Repo map table: rubric section → src file → test → notebook cell §.
Repo: github.com/AK7Amin/Capstone-SDAIA-Building-AI-Agents-Systems (final repo per owner's decision).
Run it: `pytest -m "not api"` (31 tests, no keys burned) → full `pytest` → open the notebook.

**Notes [08:15 · 20ث]:** كل قسم روبرك له صف: ملفه واختباره وخليته في
النوتبوك. والمستودع يعمل عندكم: الاختبارات المحلية بلا مفاتيح، ثم الحية،
ثم النوتبوك.

## Slide 21 — Not built — declared honestly
- No FastAPI serving layer, no UI, no real e-mail transport, no deployment — the rubric doesn't ask for them and nothing pretends they exist.
- Documented next steps: PostgresSaver/Store for multi-instance state; `/ask` + `/approve` endpoints (course Day-5 path).
Callout: An honest gap costs a few points. A claim your own output contradicts costs credibility.

**Notes [08:35 · 20ث]:** وما لم نبنه نعلنه: لا خدمة ولا واجهة ولا بريد حقيقي —
الروبرك لا يطلبها، وخطتها التالية موثقة. الفجوة الصادقة أرخص من ادعاء
يكذّبه مخرجك.

## Slide 22 — Questions (dark, thank-you)
Munassiq — every claim in this deck has a captured run behind it.
SDAIA Academy — Building AI Agent Systems · 16–20 August 2026 · Abdulaziz Mulia

**Notes [08:55 · 5ث]:** شكرًا لكم — أسئلتكم.

## Slide 23 — Appendix divider (dark, gold "Appendix")
Q&A slides below — answers to expected questions; not presented in sequence.

## Slide 24 — Q · "Is the model really calling tools, or is that hardcoded?"
- Every tool uses its arguments: two different inputs → two different outputs — asserted in tests (the rubric's own trap).
- CALENDAR mutates on the model's call; the outbox file's bytes equal the approved text.
- Negative proof: the reliability tests re-ran with a **planted invalid API key** — 5 passed with zero network, so the no-LLM mechanics claims are honest; any hidden call would have 401'd.

## Slide 25 — Q · "What if the process dies while waiting for approval?"
- State is SQLite on disk. Kill the process after interrupt() → a **new process** reopens the same thread_id and `Command(resume=...)` completes.
- Demonstrated in the spike across two separate OS processes; from_conn_string's context-manager trap documented (the singleton avoids it).

## Slide 26 — Q · "Why did behavior differ between providers?"
- Same model, two hosts: the primary routed one clean handoff; the second host's internal routing sometimes ping-ponged transfers and once leaked the reasoning channel into content.
- Engineering response: explicit stop rule in the supervisor prompt · output_mode="full_history" so the supervisor relays the worker's answer, not the transfer receipt · final evidence captured on the primary.
- The tests assert the handoff **happened**, not how many times — behavior contracts, not provider trivia.

## Slide 27 — Q · "Where exactly did the tokens go?"
Per-node table (from LangSmith): evaluate_draft 21.7s max · run_tool_with_llm_recovery 35.3s (two calls by design) · classify_request 11.4s · compose_draft 3.3s.
Free-tier math: 200K TPD/model · a full agentic request ≈ 5–10K tokens · one live suite run ≈ 30–50K — why the offline/live split exists.
