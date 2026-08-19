// مولد عرض المُنسِّق — بنية STAR على تصميم onboarding-agent المرجعي
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5

// ألوان التصميم المرجعي
const NAVY = "1E2A45";
const NAVY2 = "16203A";
const GOLD = "F2A900";
const INK = "1A2233";
const MUT = "5A6478";
const LINE = "D8DEE9";
const GREEN_BG = "E9F6EC", GREEN_BD = "2E7D32", GREEN_TX = "1B5E20";
const RED_BG = "FDECEA", RED_BD = "C0392B", RED_TX = "8E2620";
const AMB_BG = "FFF6DF", AMB_BD = "B7791F", AMB_TX = "7A5310";
const BLUE_BG = "EDF2FB", BLUE_BD = "3457A0", BLUE_TX = "24406E";

const HEAD = "Arial";
const BODY = "Calibri";
const MONO = "Courier New";

const W = 13.33, H = 7.5, MX = 0.55;

function notes(slide, t) { slide.addNotes(t); }

function title(slide, txt, opts = {}) {
  slide.addText(txt, {
    x: MX, y: 0.32, w: W - 2 * MX, h: 0.85,
    fontFace: HEAD, fontSize: 27, bold: true, color: NAVY,
    align: "left", margin: 0, ...opts,
  });
}

function divider(letter, word, sub, noteTxt) {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText(letter, { x: 0.9, y: 1.15, w: 4.4, h: 3.4, fontFace: HEAD, fontSize: 220, bold: true, color: GOLD, margin: 0 });
  s.addText(word, { x: 1.0, y: 4.6, w: 8, h: 0.9, fontFace: HEAD, fontSize: 40, bold: true, color: "FFFFFF", margin: 0 });
  if (sub) s.addText(sub, { x: 1.0, y: 5.5, w: 10.5, h: 0.9, fontFace: BODY, fontSize: 16, color: "C9D3E8", margin: 0 });
  if (noteTxt) notes(s, noteTxt);
  return s;
}

function callout(slide, x, y, w, h, txt, kind, opts = {}) {
  const map = { green: [GREEN_BG, GREEN_BD, GREEN_TX], red: [RED_BG, RED_BD, RED_TX], amber: [AMB_BG, AMB_BD, AMB_TX], blue: [BLUE_BG, BLUE_BD, BLUE_TX] };
  const [bg, bd, tx] = map[kind];
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.06, fill: { color: bg }, line: { color: bd, width: 1 } });
  slide.addText(txt, { x: x + 0.14, y: y + 0.06, w: w - 0.28, h: h - 0.12, fontFace: BODY, fontSize: opts.fontSize || 12.5, color: tx, margin: 0, valign: "middle", bold: !!opts.bold });
}

function mono(slide, x, y, w, h, lines, opts = {}) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.05, fill: { color: "F4F6FA" }, line: { color: LINE, width: 1 } });
  slide.addText(lines.map((t, i) => ({ text: t, options: { breakLine: i < lines.length - 1 } })), {
    x: x + 0.15, y: y + 0.08, w: w - 0.3, h: h - 0.16,
    fontFace: MONO, fontSize: opts.fontSize || 11, color: opts.color || "233047", margin: 0, valign: "top",
  });
}

function bullets(slide, x, y, w, h, items, opts = {}) {
  slide.addText(items.map((it, i) => ({
    text: typeof it === "string" ? it : it.text,
    options: {
      bullet: opts.noBullet ? false : { code: "2022", indent: 10 },
      breakLine: i < items.length - 1,
      bold: typeof it === "object" && !!it.bold,
      color: (typeof it === "object" && it.color) || INK,
      paraSpaceAfter: opts.gap == null ? 8 : opts.gap,
    },
  })), { x, y, w, h, fontFace: BODY, fontSize: opts.fontSize || 13.5, color: INK, margin: 0, valign: "top", align: "left" });
}

function tbl(slide, x, y, w, header, rows, colW, opts = {}) {
  const rws = [
    header.map(hc => ({ text: hc, options: { bold: true, color: "FFFFFF", fill: { color: NAVY }, fontFace: BODY, fontSize: opts.hSize || 12 } })),
    ...rows.map((r, ri) => r.map(c => (typeof c === "object" ? c : {
      text: c, options: { color: INK, fontFace: BODY, fontSize: opts.fSize || 11.5, fill: { color: ri % 2 ? "F4F6FA" : "FFFFFF" } },
    }))),
  ];
  slide.addTable(rws, { x, y, w, colW, border: { type: "solid", color: LINE, pt: 0.75 }, margin: 0.04, valign: "middle" });
}

function statBox(slide, x, y, w, big, small) {
  slide.addShape("roundRect", { x, y, w, h: 1.25, rectRadius: 0.07, fill: { color: "FFFFFF" }, line: { color: NAVY, width: 1.25 } });
  slide.addText(big, { x: x + 0.1, y: y + 0.08, w: w - 0.2, h: 0.7, fontFace: HEAD, fontSize: 30, bold: true, color: NAVY, align: "center", margin: 0 });
  slide.addText(small, { x: x + 0.1, y: y + 0.78, w: w - 0.2, h: 0.42, fontFace: BODY, fontSize: 10.5, color: MUT, align: "center", margin: 0 });
}

// ---------------------------------------------------------------- Slide 1
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText("CAPSTONE · TRACK A · SUPERVISOR + WORKERS", { x: MX, y: 0.5, w: 9, h: 0.4, fontFace: HEAD, fontSize: 12, bold: true, color: GOLD, charSpacing: 2, margin: 0 });
  s.addText("Munassiq (المُنسِّق)\nAssociation Office Assistant", { x: MX, y: 1.0, w: 11.5, h: 1.9, fontFace: HEAD, fontSize: 42, bold: true, color: "FFFFFF", margin: 0 });
  s.addText("A supervisor and three specialist agents on a LangGraph Functional API core.\nEvery irreversible act waits for a human. Every claim has a captured run behind it.", { x: MX, y: 3.0, w: 10.8, h: 1.0, fontFace: BODY, fontSize: 16, color: "C9D3E8", margin: 0 });
  s.addText("Abdulaziz Mulia (عبدالعزيز مُليا) — github.com/AK7Amin", { x: MX, y: 4.35, w: 10, h: 0.5, fontFace: HEAD, fontSize: 16, bold: true, color: GOLD, margin: 0 });
  s.addText("SDAIA Academy — Building AI Agent Systems · Cohort 16–20 August 2026 · Riyadh", { x: MX, y: 6.6, w: 11, h: 0.4, fontFace: BODY, fontSize: 12, color: "9FB0CE", margin: 0 });
  notes(s, "[00:00 · 25ث] السلام عليكم. مشروعي «المُنسِّق»: مساعد مكتب جمعية — مشرف يوزع على ثلاثة عمال متخصصين، بذاكرة تعيش عبر المحادثات، وبوابة موافقة بشرية قبل أي فعل لا يرتد. كل رقم في هذا العرض وراءه تشغيلة حقيقية ملتقطة في المستودع.");
}

// ---------------------------------------------------------------- Slide 2 (S)
divider("S", "Situation", "What the office lives today, and why it does not scale.", "[00:25 · 8ث] أعرض على بنية STAR: الوضع، فالمهمة، فالبناء، فالنتيجة.");

// ---------------------------------------------------------------- Slide 3
{
  const s = pres.addSlide();
  title(s, "The office inbox is scattered, manual, and unforgiving");
  tbl(s, MX, 1.25, 7.1,
    ["What arrives daily", "What happens today", "The cost"],
    [
      ["سؤال سياسة: «كم مدة مراجعة المحتوى؟»", "an employee digs through documents", "minutes lost; answers vary"],
      ["طلب حجز اجتماع", "a calendar updated by hand", "conflicts and forgetting"],
      ["بريد إلى المتطوعين", "drafted and sent directly", { text: "a wrong send cannot be recalled", options: { bold: true, color: RED_TX, fontFace: BODY, fontSize: 11.5, fill: { color: RED_BG } } }],
    ],
    [2.6, 2.4, 2.1]);
  s.addText("What breaks in practice", { x: 8.0, y: 1.25, w: 4.7, h: 0.4, fontFace: HEAD, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  bullets(s, 8.0, 1.7, 4.75, 2.6, [
    "The knowledge lives in documents nobody re-reads.",
    "Preferences repeat in every conversation — nothing remembers.",
    "The riskiest step (sending) is the least guarded.",
  ], { fontSize: 13 });
  callout(s, MX, 5.9, W - 2 * MX, 0.8, "الإرسال الخاطئ باسم الجمعية هو الخطأ الذي لا تصلحه معذرة.", "red", { fontSize: 14, bold: true });
  notes(s, "[00:33 · 40ث] مكتب الجمعية يستقبل ثلاثة أنواع طلبات يوميًا: أسئلة سياسات، وحجوزات، ومراسلات. كلها يدوية، لا شيء يتذكر تفضيلات أحد، وأخطر خطوة — الإرسال باسم الجمعية — هي الأقل حراسة.");
}

// ---------------------------------------------------------------- Slide 4
{
  const s = pres.addSlide();
  title(s, "Why a plain chatbot makes it worse");
  const items = [
    ["1", "It answers policy from its imagination.", "No retrieval means confident, wrong, unattributable answers about real procedures."],
    ["2", "It forgets across threads.", "State dies with the tab; “our preferred day” gets re-asked forever."],
    ["3", "It acts without a gate.", "A model that can draft can send — and sending is irreversible."],
  ];
  items.forEach((it, i) => {
    const y = 1.35 + i * 1.15;
    const s2 = pres; // noop
    pres; // keep linter quiet
    // circle number
    const sl = s;
    sl.addShape("ellipse", { x: MX, y: y + 0.08, w: 0.55, h: 0.55, fill: { color: NAVY }, line: { color: NAVY, width: 1 } });
    sl.addText(it[0], { x: MX, y: y + 0.08, w: 0.55, h: 0.55, fontFace: HEAD, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
    sl.addText(it[1], { x: MX + 0.75, y, w: 6.6, h: 0.4, fontFace: HEAD, fontSize: 15.5, bold: true, color: INK, margin: 0 });
    sl.addText(it[2], { x: MX + 0.75, y: y + 0.4, w: 6.6, h: 0.6, fontFace: BODY, fontSize: 12.5, color: MUT, margin: 0 });
  });
  s.addText("Design consequences", { x: 8.35, y: 1.3, w: 4.4, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  callout(s, 8.35, 1.75, 4.4, 0.95, "Retrieval before answering — a real RAG pipeline over the policy corpus.", "blue");
  callout(s, 8.35, 2.85, 4.4, 0.95, "Memory must outlive the thread — a separate durable Store, not chat history.", "blue");
  callout(s, 8.35, 3.95, 4.4, 0.95, "interrupt() before anything irreversible — a human owns the send.", "blue");
  notes(s, "[01:13 · 30ث] روبوت محادثة ساذج يزيد الطين بلة: يجيب عن السياسات من خياله، وينسى كل شيء بين محادثة وأخرى، ويرسل بلا إذن. من هنا جاءت القرارات المعمارية الثلاثة المقابلة.");
}

// ---------------------------------------------------------------- Slide 5 (T)
divider("T", "Task", "What we set out to build — and the constraints we refused to relax.", "[01:43 · 6ث] المهمة والقيود التي التزمناها.");

// ---------------------------------------------------------------- Slide 6
{
  const s = pres.addSlide();
  title(s, "The brief, and the constraints we refused to relax");
  s.addText("The rubric became the acceptance criteria", { x: MX, y: 1.2, w: 6, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  tbl(s, MX, 1.65, 5.7,
    ["#", "Section", "Pts"],
    [
      ["1", "Agent fundamentals — real tools + structured output", "15"],
      ["2", "Multi-agent routing (LLM decides)", "15"],
      ["3", "RAG pipeline + written justification", "15"],
      ["4", "Context & state (checkpointer + Store)", "15"],
      ["5", "Human-in-the-loop (interrupt + resume)", "10"],
      ["6", "Functional API + 2 error strategies", "15"],
      ["7", "Workflow pattern, named", "10"],
      ["8", "LangSmith observability", "5"],
    ],
    [0.45, 4.45, 0.8], { fSize: 10.5, hSize: 11 });
  callout(s, MX, 6.55, 5.7, 0.55, "Pass at 60 — and no section below 40% of its points.", "amber", { bold: true });
  s.addText("Five constraints written before any code", { x: 6.7, y: 1.2, w: 6.1, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  bullets(s, 6.7, 1.68, 6.05, 5.4, [
    { text: "Real tool calls only — a function that ignores its arguments is not a tool.", bold: false },
    "Routing decided by the LLM via structured output — keyword matching is not routing.",
    "Long-term memory = a separate Store, proven across threads — a growing chat list does not count.",
    "interrupt() AND resume both demonstrated — the human's text passes verbatim, no model in between.",
    "All corpus documents synthetic (privacy rule R021) — no real association data near any model.",
  ], { fontSize: 13, gap: 12 });
  notes(s, "[01:49 · 35ث] الروبرك نفسه صار معيار القبول: ثمانية أقسام ولا قسم تحت 40%. وكتبنا خمسة قيود قبل أول سطر كود — أهمها: التوجيه قرار النموذج لا مطابقة كلمات، والذاكرة الطويلة مخزن منفصل يُثبَت عبر المحادثات، ووثائق تركيبية بالكامل التزامًا بخصوصية الجمعية.");
}

// ---------------------------------------------------------------- Slide 7 (A)
divider("A", "Action", "The system: entrypoint, tasks, supervisor, memory, gate.", "[02:24 · 6ث] البناء: الغراف، العمال، الذاكرة، البوابة.");

// ---------------------------------------------------------------- Slide 8 (architecture)
{
  const s = pres.addSlide();
  title(s, "Architecture: one entrypoint, everything else is a task");
  const bx = (x, y, w, h, txt, fill, txcol, fs) => {
    s.addShape("roundRect", { x, y, w, h, rectRadius: 0.06, fill: { color: fill }, line: { color: NAVY, width: 1 } });
    s.addText(txt, { x: x + 0.05, y, w: w - 0.1, h, fontFace: BODY, fontSize: fs || 11, bold: true, color: txcol, align: "center", valign: "middle", margin: 0 });
  };
  // أبعاد الشكل لا تقبل السالب — نطبّع ونستعمل flipH/flipV لاتجاه السهم
  const arrow = (x1, y1, x2, y2) => s.addShape("line", {
    x: Math.min(x1, x2), y: Math.min(y1, y2),
    w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: x2 < x1, flipV: y2 < y1,
    line: { color: MUT, width: 1.5, endArrowType: "triangle" },
  });
  bx(MX, 1.45, 1.5, 0.6, "User", "FFFFFF", INK);
  bx(2.5, 1.3, 3.6, 0.9, "@entrypoint munassiq_app\nSqliteSaver + SqliteStore", NAVY, "FFFFFF", 11);
  arrow(2.05, 1.75, 2.5, 1.75);
  bx(2.5, 2.55, 1.7, 0.55, "load_memories", "EDF2FB", BLUE_TX, 9.5);
  bx(4.4, 2.55, 1.7, 0.55, "detect_and_store", "EDF2FB", BLUE_TX, 9.5);
  bx(2.5, 3.25, 3.6, 0.55, "classify_request → TriageDecision (Pydantic)", "EDF2FB", BLUE_TX, 9.5);
  arrow(4.3, 2.2, 4.3, 2.55);
  // correspondence branch
  bx(1.0, 4.35, 2.9, 0.7, "draft_correspondence\nEvaluator-Optimizer ×2", "FFF6DF", AMB_TX, 9.5);
  bx(4.1, 4.35, 1.6, 0.7, "interrupt()\nhuman gate", "FDECEA", RED_TX, 10);
  bx(5.9, 4.35, 1.7, 0.7, "send_final\nverbatim → outbox", "E9F6EC", GREEN_TX, 9.5);
  arrow(3.3, 3.8, 2.4, 4.35); arrow(3.9, 5.0 - 0.3, 4.1, 4.7); arrow(5.7, 4.7, 5.9, 4.7);
  // supervisor branch
  bx(8.0, 4.35, 2.2, 0.7, "Supervisor\nOrchestrator-Worker", NAVY, "FFFFFF", 10);
  arrow(5.1, 3.8, 8.6, 4.35);
  bx(7.2, 5.55, 1.7, 0.55, "calendar_agent", "F4F6FA", INK, 9.5);
  bx(9.0, 5.55, 1.7, 0.55, "knowledge_agent → RAG", "F4F6FA", INK, 9);
  bx(10.8, 5.55, 1.9, 0.55, "correspondence_agent", "F4F6FA", INK, 9);
  arrow(8.7, 5.05, 8.0, 5.55); arrow(9.1, 5.05, 9.8, 5.55); arrow(10.0, 5.05, 11.6, 5.55);
  bullets(s, 10.35, 1.3, 2.45, 2.9, [
    "Entrypoint body is pure glue — every LLM call and side effect lives inside a @task; nothing re-executes on resume.",
    "Supervisor holds no checkpointer — durable state belongs to the entrypoint alone.",
  ], { fontSize: 10.5, gap: 8 });
  callout(s, MX, 6.55, W - 2 * MX, 0.55, "Two named patterns: Orchestrator-Worker (the supervisor) · Evaluator-Optimizer (the drafting loop).", "green", { bold: true });
  notes(s, "[02:30 · 45ث] المعمارية: نقطة دخول وظيفية واحدة تملك الحالة — checkpointer للسياق القصير وStore دائم للحقائق. جسمها غراء نقي: كل نداء نموذج داخل @task وإلا أعيد تنفيذه عند الاستئناف. التصنيف مخرج مهيكل، والمراسلات تمر بحلقة تقييم قبل بوابة الموافقة، وبقية الطلبات لمشرف Orchestrator-Worker بثلاثة عمال.");
}

// ---------------------------------------------------------------- Slide 9 (routing)
{
  const s = pres.addSlide();
  title(s, "Routing is a model decision, printed as proof");
  s.addText("TriageDecision — parsed by code, never by string matching", { x: MX, y: 1.25, w: 6.4, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  mono(s, MX, 1.7, 6.3, 1.9, [
    "class TriageDecision(BaseModel):",
    "    worker: Literal[\"calendar\",",
    "        \"knowledge\", \"correspondence\"]",
    "    needs_human_approval: bool",
    "    summary: str",
  ], { fontSize: 12 });
  bullets(s, MX, 3.85, 6.3, 1.7, [
    "with_structured_output — the object is read by code paths, so the type is the contract.",
    "The evaluator's verdict and the memory detector use the same discipline.",
  ], { fontSize: 12.5 });
  s.addText("Captured evidence — the live handoff", { x: 7.2, y: 1.25, w: 5.5, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  mono(s, 7.2, 1.7, 5.55, 1.35, [
    "كل نداءات الأدوات في الرحلة:",
    "['transfer_to_calendar_agent',",
    " 'transfer_back_to_supervisor']",
  ], { fontSize: 12 });
  callout(s, 7.2, 3.25, 5.55, 1.15, "The round trip is the proof the grader asks for — the LLM chose the worker; the handoff back is expected, not a bug.", "green", { fontSize: 12.5 });
  callout(s, MX, 6.05, W - 2 * MX, 0.7, "The rubric's most common architecture failure — if \"email\" in question — never appears in this codebase.", "amber", { fontSize: 13 });
  notes(s, "[03:15 · 25ث] التوجيه قرار نموذج بمخرج Pydantic يقرؤه الكود. والدليل المطبوع: نداء التحويل ورجوعه — الرحلتان متوقعتان، وهذا حرفيًا ما يطلبه المقيم.");
}

// ---------------------------------------------------------------- Slide 10 (RAG)
{
  const s = pres.addSlide();
  title(s, "RAG that actually reads Arabic");
  bullets(s, MX, 1.3, 6.4, 2.5, [
    "Pipeline: 3 synthetic policy docs → split 500/50 → multilingual MiniLM (fastembed — local, free, no key) → Chroma → retrieve.",
    { text: "The trap we caught by testing: the default English embedding model silently fails on Arabic — it retrieved unrelated passages.", bold: true },
    "Architecture justified in writing: 2-Step vs Agentic vs Hybrid — Agentic fits: the worker decides when to search.",
  ], { fontSize: 13, gap: 10 });
  s.addText("The verbatim-fact test", { x: 7.2, y: 1.3, w: 5.5, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  mono(s, 7.2, 1.75, 5.55, 1.6, [
    "Q: كم مدة مراجعة المحتوى قبل النشر؟",
    "top passage ← سياسة-النشر.md",
    "✓ يحوي حرفيًا: «ثلاثة أيام عمل»",
  ], { fontSize: 12 });
  callout(s, 7.2, 3.55, 5.55, 1.2, "A retriever that returns nothing is the rubric's #1 RAG failure — this test makes it impossible to miss.", "green", { fontSize: 12.5 });
  callout(s, MX, 6.05, W - 2 * MX, 0.7, "Rebuilds recreate the collection — the index never duplicates itself (a real bug the full test suite caught).", "blue", { fontSize: 13 });
  notes(s, "[03:40 · 35ث] خط RAG يقرأ العربية فعلًا — الموديل الافتراضي فشل بصمت واصطدناه باختبار حقيقة مزروعة: سؤال المدة يسترجع «ثلاثة أيام عمل» حرفيًا من وثيقة السياسة. والتبرير المكتوب اختار Agentic RAG لأن العامل هو من يقرر متى يبحث.");
}

// ---------------------------------------------------------------- Slide 11 (memory + screenshot)
{
  const s = pres.addSlide();
  title(s, "Memory that survives the thread");
  s.addImage({ path: "../docs/assets/trace-memory-cross-thread.png", x: MX, y: 1.3, w: 8.6, h: 4.51 });
  bullets(s, 9.4, 1.4, 3.35, 3.6, [
    "Write in thread-1: «تذكّر أن اليوم المفضل لاجتماعاتنا هو الخميس»",
    "store.search() proves the write landed.",
    "Recall in thread-2 — a different conversation — with memories_used carrying the fact.",
  ], { fontSize: 12, gap: 10 });
  callout(s, MX, 6.1, W - 2 * MX, 0.7, "The test asserts on the Store, not on the model's phrasing — hard evidence, not vibes.", "green", { bold: true, fontSize: 13 });
  notes(s, "[04:15 · 25ث] الذاكرة الطويلة مخزن SQLite منفصل: نكتب الحقيقة في محادثة، ونقرؤها من محادثة أخرى مختلفة تمامًا — والـtrace يعرض الحقن في memories_used. الاختبار يفحص المخزن نفسه لا صياغة النموذج.");
}

// ---------------------------------------------------------------- Slide 12 (HITL)
{
  const s = pres.addSlide();
  title(s, "The human gate: nothing irreversible without approval");
  s.addText("PAUSED — the interrupt payload", { x: MX, y: 1.25, w: 6, h: 0.35, fontFace: HEAD, fontSize: 13, bold: true, color: RED_TX, margin: 0 });
  mono(s, MX, 1.62, 6.0, 1.8, [
    "{'__interrupt__': [{",
    "  'action': 'راجع المسودة واعتمدها أو عدّلها',",
    "  'draft': '...مسودة بريد التأجيل...',",
    "  'evaluation_score': 9 }]}",
  ], { fontSize: 11 });
  s.addText("RESUMED — the human's text, verbatim", { x: 6.85, y: 1.25, w: 6, h: 0.35, fontFace: HEAD, fontSize: 13, bold: true, color: GREEN_TX, margin: 0 });
  mono(s, 6.85, 1.62, 5.9, 1.8, [
    "Command(resume='النص المعتمد من المشرف",
    "  البشري: الفعالية مؤجلة لأسبوع.')",
    "→ reply == human text  ✓",
    "→ outbox file bytes == human text  ✓",
  ], { fontSize: 11 });
  bullets(s, MX, 3.75, 11.9, 1.3, [
    "The human's edit IS the sent text — it reaches the outbox byte-for-byte, with no model in between.",
    "Proven three ways: unit (no-LLM mechanics over real SqliteSaver) · live integration · notebook cells with both outputs.",
  ], { fontSize: 13, gap: 8 });
  callout(s, MX, 5.3, W - 2 * MX, 0.8, "Pausing but never resuming is the most common half-finished capstone deliverable — both halves are captured here, with outputs.", "amber", { fontSize: 13, bold: true });
  notes(s, "[04:40 · 30ث] بوابة الإنسان: قبل أي إرسال يقف الغراف بـinterrupt عارضًا المسودة، ونص المعتمد البشري يصل الصادر حرفيًا بلا مرور على أي نموذج. الشقان — التوقف والاستئناف — ملتقطان بمخرجيهما.");
}

// ---------------------------------------------------------------- Slide 13 (reliability)
{
  const s = pres.addSlide();
  title(s, "Reliability: four error classes, each with its own answer");
  tbl(s, MX, 1.3, W - 2 * MX,
    ["Error class", "Strategy", "Where"],
    [
      ["Transient (network, 5xx)", "RetryPolicy(max_attempts=3) — a real policy object, no hand-rolled sleep loops", "fetch_external_resource"],
      ["LLM-recoverable (bad tool input)", "error text fed back to the model in a correction message, bounded retries", "run_tool_with_llm_recovery"],
      ["User-fixable", "interrupt() — the approval gate doubles as the pattern", "munassiq_app"],
      ["Unexpected", "propagate for debugging — printed as type + message only, never raw tracebacks", "everywhere"],
    ],
    [3.0, 6.4, 2.8], { fSize: 11.5 });
  s.addText("Provider quirks we caught live — one retry helper (invoke_structured) absorbs all three:", { x: MX, y: 4.75, w: 12, h: 0.4, fontFace: HEAD, fontSize: 13.5, bold: true, color: NAVY, margin: 0 });
  callout(s, MX, 5.25, 3.95, 1.0, "a bare -2.0 returned instead of the object → pydantic ValidationError", "red", { fontSize: 11.5 });
  callout(s, 4.7, 5.25, 3.95, 1.0, "a response with no 'parsed' field at all → ValueError", "red", { fontSize: 11.5 });
  callout(s, 8.85, 5.25, 3.93, 1.0, "server-side output_parse_failed → BadRequestError 400", "red", { fontSize: 11.5 });
  notes(s, "[05:10 · 30ث] الموثوقية: أربع فئات خطأ لكلٍّ علاجها — وأهم درس حي: المزودون أنفسهم يرمون نزوات مخرج مهيكل؛ رصدنا ثلاثة أشكال فعلية ولففناها بمعيد محاولة واحد موثق.");
}

// ---------------------------------------------------------------- Slide 14 (evaluator-optimizer)
{
  const s = pres.addSlide();
  title(s, "Evaluator-Optimizer — named, bounded, measured");
  const step = (x, txt, fill, tx) => {
    s.addShape("roundRect", { x, y: 1.6, w: 2.15, h: 0.85, rectRadius: 0.07, fill: { color: fill }, line: { color: NAVY, width: 1 } });
    s.addText(txt, { x: x + 0.05, y: 1.6, w: 2.05, h: 0.85, fontFace: BODY, fontSize: 11, bold: true, color: tx, align: "center", valign: "middle", margin: 0 });
  };
  step(MX, "compose_draft\n3.3s", "EDF2FB", BLUE_TX);
  step(3.2, "evaluate_draft\nDraftVerdict · up to 21.7s", "FFF6DF", AMB_TX);
  step(5.85, "improve_draft\n(if not approved)", "EDF2FB", BLUE_TX);
  step(8.5, "evaluate again\n(≤ 2 rounds)", "FFF6DF", AMB_TX);
  step(11.13, "interrupt()\nhuman gate", "FDECEA", RED_TX);
  [2.75, 5.4, 8.05, 10.7].forEach(x => s.addShape("line", { x, y: 2.0, w: 0.4, h: 0, line: { color: MUT, width: 1.75, endArrowType: "triangle" } }));
  bullets(s, MX, 3.0, 11.9, 1.9, [
    "The verdict is a Pydantic object (score / approved / feedback) — approval is read from the field, never sniffed from text. The test plants «معتمدة» inside a rejection's feedback to prove it.",
    "The loop always finishes BEFORE the human gate — every draft a human sees has been judged.",
    { text: "What the trace showed: the structured judge is ~7× slower than the writer (21.7s vs 3.3s) — constrained output makes the model plan harder.", bold: true },
  ], { fontSize: 13, gap: 10 });
  notes(s, "[05:40 · 25ث] النمط المسمى: Evaluator-Optimizer — صياغة فتقييم بحكم مهيكل فتحسين، بجولتين كحد أقصى وقبل بوابة الموافقة دائمًا. والـtrace كشف مفاجأة: الحَكم أبطأ من الكاتب سبع مرات.");
}

// ---------------------------------------------------------------- Slide 15 (LangSmith)
{
  const s = pres.addSlide();
  title(s, "Observability: the trap, the verifier, the finding");
  callout(s, MX, 1.3, 12.23, 0.95, "The env var is LANGCHAIN_TRACING_V2 — the lookalike LANGSMITH_TRACING_V2 fails SILENTLY. Our config raises on the wrong name, and a test enforces the raise.", "red", { fontSize: 13, bold: true });
  bullets(s, MX, 2.55, 6.2, 2.6, [
    "wait_for_recent_run(): polling with a deadline (not a single racy query) — prints id / name / status only.",
    "Redaction at the source: the query selects three fields, so message contents never enter memory.",
    "Every run in this deck's numbers is queryable in the munassiq-capstone project.",
  ], { fontSize: 12.5, gap: 10 });
  s.addText("What the trace actually showed", { x: 7.2, y: 2.55, w: 5.5, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  tbl(s, 7.2, 3.0, 5.55,
    ["node", "took"],
    [
      ["evaluate_draft (max)", "21.7s"],
      ["run_tool_with_llm_recovery (2 calls)", "35.3s"],
      ["classify_request", "11.4s"],
      ["compose_draft", "3.3s"],
    ],
    [3.9, 1.65], { fSize: 11 });
  callout(s, MX, 6.15, W - 2 * MX, 0.65, "Findings, not vibes: the bottleneck is judging, not writing — and the recovery loop's two calls are visible by design.", "green", { fontSize: 13 });
  notes(s, "[06:05 · 25ث] التتبع: الاسم الصحيح للمتغير محروس باختبار لأن الخطأ فيه صامت. والقيمة الحقيقية: الـtrace أعطانا قياسات — عنق الزجاجة في التقييم لا الصياغة.");
}

// ---------------------------------------------------------------- Slide 16 (R)
divider("R", "Result", "Verified numbers, and where every one of them comes from.", "[06:30 · 5ث] النتيجة بالأرقام الموثقة.");

// ---------------------------------------------------------------- Slide 17 (numbers)
{
  const s = pres.addSlide();
  title(s, "Verified numbers — every one traced to its source");
  statBox(s, MX, 1.3, 2.9, "40", "tests — 31 offline · 9 live (api-marked)");
  statBox(s, 3.65, 1.3, 2.9, "15/15", "notebook cells executed · zero errors");
  statBox(s, 6.75, 1.3, 2.9, "14", "closure suite passed (integration+reliability+tracing+supervisor)");
  statBox(s, 9.85, 1.3, 2.9, "~$0", "total model cost (free tiers + cents on fallback)");
  tbl(s, MX, 3.0, W - 2 * MX,
    ["Claim", "Verified by"],
    [
      ["Integration test green — without its xfail marker", "closure-run.log (sanitized, committed) · 241s live run"],
      ["Cross-thread long-term memory", "test_memory.py::test_cross_thread_store + the LangSmith trace"],
      ["Human's resume text lands verbatim in the outbox", "test_hitl.py — byte equality on the outbox file"],
      ["Both interrupt halves captured with outputs", "notebook §5 — two cells, two outputs"],
      ["No secret / absolute path / identity in the repo", "tools/leak_scan.py — exit 0 over 33 tracked files, gate before every push"],
    ],
    [6.1, 6.1], { fSize: 11.5 });
  notes(s, "[06:35 · 30ث] الأرقام: أربعون اختبارًا، النوتبوك كامل التنفيذ بلا أخطاء، حزمة الإغلاق 14 ناجحًا، والتكلفة صفر تقريبًا. كل ادعاء في العمود الأيسر يقابله ملف أو سجل أو اختبار في الأيمن.");
}

// ---------------------------------------------------------------- Slide 18 (battle scars)
{
  const s = pres.addSlide();
  title(s, "What production actually taught us — the battle scars");
  const rows = [
    ["404", "The course model does not exist on our account", "a pre-build spike caught it → swapped to gpt-oss-120b, documented in the write-up", "green"],
    ["200K", "Groq's free daily quota ran out mid-build", "offline/live test split (-m \"not api\") · mechanics proven with stub tasks over the real infrastructure — zero build hours lost", "green"],
    ["✕", "Smaller models failed structured output qualitatively", "mangled tool names; booleans as strings — eliminated by evidence, not preference", "amber"],
    ["⇄", "A second host varied: transfer ping-pong, one reasoning leak", "stop rule in the supervisor prompt · output_mode=full_history · final evidence captured on the primary provider", "amber"],
  ];
  rows.forEach((r, i) => {
    const y = 1.35 + i * 1.18;
    s.addShape("roundRect", { x: MX, y, w: 1.15, h: 1.0, rectRadius: 0.07, fill: { color: NAVY }, line: { color: NAVY, width: 1 } });
    s.addText(r[0], { x: MX, y, w: 1.15, h: 1.0, fontFace: HEAD, fontSize: 17, bold: true, color: GOLD, align: "center", valign: "middle", margin: 0 });
    s.addText(r[1], { x: 1.95, y: y + 0.04, w: 10.8, h: 0.4, fontFace: HEAD, fontSize: 13.5, bold: true, color: INK, margin: 0 });
    s.addText(r[2], { x: 1.95, y: y + 0.46, w: 10.8, h: 0.52, fontFace: BODY, fontSize: 11.5, color: MUT, margin: 0 });
  });
  callout(s, MX, 6.35, W - 2 * MX, 0.6, "None of this was in the plan. All of it is in the run log — docs/plan/…/RUN-LOG.md.", "green", { bold: true, fontSize: 13 });
  notes(s, "[07:05 · 40ث] أصدق شريحة في العرض: ما علمتنا إياه البيئة الحقيقية. نموذج الدورة 404 فاصطاده سبايك مبكر؛ الحصة المجانية نفدت منتصف البناء ففصلنا الاختبارات الحية وأثبتنا الآليات بلا نماذج؛ النماذج الأصغر سقطت نوعيًا بالدليل؛ ومستضيف بديل ذبذب السلوك فعالجناه بقاعدة توقف وبالتقاط الدليل النهائي على المزود الأصلي. كل حادثة موثقة في سجل التشغيل.");
}

// ---------------------------------------------------------------- Slide 19 (how it was built)
{
  const s = pres.addSlide();
  title(s, "How it was built — the part that transfers to your projects");
  bullets(s, MX, 1.35, 7.3, 4.8, [
    { text: "Spikes before plans — risky assumptions burned down with throwaway code against the real APIs.", bold: true },
    "A four-angle critique (architecture, rubric, security, reliability) ran before the first line of code — 8 blockers died on paper, where they cost minutes.",
    "Ten vertical slices, each: a red test committed first → the minimal green → central re-verification (an agent's word is not evidence).",
    "A leak-scan gate before every push: key patterns, absolute paths, machine identity — it once flagged the author's own name.",
    "Final review, two independent axes + a mechanical pass → 5 more blockers found and fixed before delivery.",
  ], { fontSize: 13.5, gap: 14 });
  s.addText("The delivery discipline", { x: 8.3, y: 1.35, w: 4.4, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  callout(s, 8.3, 1.8, 4.45, 1.25, "Red commit carries the first failure line; green commit carries the minimal fix — the history reads as proof.", "blue");
  callout(s, 8.3, 3.2, 4.45, 1.25, "Write-ups are written FROM results, not plans — the one contradiction found in review was fixed before push.", "blue");
  callout(s, 8.3, 4.6, 4.45, 1.25, "Evidence is captured from clean state — kernel restarted, top-to-bottom, outputs saved.", "blue");
  notes(s, "[07:45 · 30ث] طريقة البناء نفسها قابلة للنقل: سبايكات قبل الخطة، نقد رباعي قبل الكود أسقط ثمانية عوائق على الورق، عشر شرائح رأسية لكل منها اختبار أحمر فأخضر، وبوابة فحص تسرب قبل كل دفع — أمسكت مرة اسمي أنا.");
}

// ---------------------------------------------------------------- Slide 20 (grader map)
{
  const s = pres.addSlide();
  title(s, "Where the grader finds the proof");
  tbl(s, MX, 1.3, W - 2 * MX,
    ["Rubric section", "Implementation", "Test", "Notebook"],
    [
      ["1 · Agent fundamentals", "src/munassiq/tools.py", "test_tools.py", "§2"],
      ["2 · Multi-agent routing", "supervisor.py + workers.py", "test_supervisor.py", "§3"],
      ["3 · RAG pipeline", "rag.py (+ written justification)", "test_rag.py", "§4"],
      ["4 · Context & state", "memory.py (Saver + Store)", "test_memory.py", "§5"],
      ["5 · Human-in-the-loop", "app.py (interrupt/resume)", "test_hitl.py", "§6"],
      ["6 · Functional API + errors", "app.py + workers.py", "test_reliability.py", "§7"],
      ["7 · Named pattern", "Evaluator-Optimizer in app.py", "test_reliability.py", "§8"],
      ["8 · LangSmith", "tracing.py + verify_trace.py", "test_tracing.py", "§9"],
    ],
    [3.1, 4.3, 2.9, 1.9], { fSize: 11 });
  mono(s, MX, 6.15, 8.2, 0.85, [
    "pytest -m \"not api\"     # 31 tests, no keys burned",
    "pytest && jupyter notebook munassiq_capstone.ipynb",
  ], { fontSize: 11.5 });
  s.addText("github.com/AK7Amin/TestCapstone", { x: 9.0, y: 6.3, w: 3.8, h: 0.5, fontFace: HEAD, fontSize: 13, bold: true, color: NAVY, margin: 0 });
  notes(s, "[08:15 · 20ث] كل قسم روبرك له صف: ملفه واختباره وخليته في النوتبوك. والمستودع يعمل عندكم: الاختبارات المحلية بلا مفاتيح، ثم الحية، ثم النوتبوك.");
}

// ---------------------------------------------------------------- Slide 21 (not built)
{
  const s = pres.addSlide();
  title(s, "Not built — declared honestly");
  bullets(s, MX, 1.4, 7.4, 3.2, [
    "No FastAPI serving layer — the rubric does not ask for one.",
    "No UI — the notebook and the tests are the interfaces.",
    "No real e-mail transport — the outbox directory is the terminal, by design.",
    "No deployment — documented as the next step, not claimed as done.",
  ], { fontSize: 14, gap: 12 });
  s.addText("Documented next steps", { x: 8.4, y: 1.4, w: 4.3, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  callout(s, 8.4, 1.85, 4.35, 1.1, "PostgresSaver / PostgresStore for multi-instance durable state.", "blue");
  callout(s, 8.4, 3.1, 4.35, 1.1, "/ask + /approve endpoints — the course's Day-5 production path.", "blue");
  callout(s, MX, 5.6, W - 2 * MX, 0.95, "An honest gap costs a few points. A claim your own output contradicts costs credibility across the whole submission.", "amber", { bold: true, fontSize: 14 });
  notes(s, "[08:35 · 20ث] وما لم نبنه نعلنه: لا خدمة ولا واجهة ولا بريد حقيقي — الروبرك لا يطلبها، وخطتها التالية موثقة. الفجوة الصادقة أرخص من ادعاء يكذّبه مخرجك.");
}

// ---------------------------------------------------------------- Slide 22 (questions)
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText("THANK YOU", { x: MX, y: 2.1, w: 6, h: 0.5, fontFace: HEAD, fontSize: 14, bold: true, color: GOLD, charSpacing: 3, margin: 0 });
  s.addText("Questions", { x: MX, y: 2.6, w: 9, h: 1.2, fontFace: HEAD, fontSize: 54, bold: true, color: "FFFFFF", margin: 0 });
  s.addText("Munassiq — every claim in this deck has a captured run behind it.", { x: MX, y: 4.0, w: 10, h: 0.5, fontFace: BODY, fontSize: 16, color: "C9D3E8", margin: 0 });
  s.addText("SDAIA Academy — Building AI Agent Systems · 16–20 August 2026 · Abdulaziz Mulia — github.com/AK7Amin", { x: MX, y: 6.6, w: 12, h: 0.4, fontFace: BODY, fontSize: 12, color: "9FB0CE", margin: 0 });
  notes(s, "[08:55 · 5ث] شكرًا لكم — أسئلتكم.");
}

// ---------------------------------------------------------------- Slide 23 (appendix divider)
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText("Appendix", { x: 0.9, y: 2.6, w: 8, h: 1.4, fontFace: HEAD, fontSize: 60, bold: true, color: GOLD, margin: 0 });
  s.addText("Answers to expected questions. Not presented in sequence.", { x: 0.95, y: 4.1, w: 9, h: 0.6, fontFace: BODY, fontSize: 16, color: "C9D3E8", margin: 0 });
}

// ---------------------------------------------------------------- Slide 24 (Q1)
{
  const s = pres.addSlide();
  title(s, "Q · “Is the model really calling tools, or is that hardcoded?”", { fontSize: 23 });
  bullets(s, MX, 1.35, 7.3, 3.4, [
    "Every tool uses its arguments: two different inputs must produce two different outputs — asserted in tests (this is the rubric's own trap, quoted).",
    "CALENDAR mutates on the model's call; the outbox file's bytes equal the approved text exactly.",
    "The trace shows the tool call with its arguments — nothing is pre-scripted.",
  ], { fontSize: 13.5, gap: 12 });
  s.addText("The negative proof", { x: 8.3, y: 1.35, w: 4.4, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  callout(s, 8.3, 1.8, 4.45, 2.3, "The reliability tests were re-run with a planted INVALID API key: 5 passed with zero network. Any hidden model call would have failed with 401 — so the “no-LLM mechanics” claims are honest by construction.", "green", { fontSize: 12.5 });
}

// ---------------------------------------------------------------- Slide 25 (Q2)
{
  const s = pres.addSlide();
  title(s, "Q · “What if the process dies while waiting for approval?”", { fontSize: 23 });
  bullets(s, MX, 1.35, 7.3, 3.6, [
    "State is SQLite on disk — SqliteSaver for the thread, SqliteStore for long-term facts.",
    "Kill the process after interrupt(): a NEW OS process reopens the same thread_id and Command(resume=…) completes the run.",
    "Demonstrated in a spike across two separate processes before the architecture was committed.",
  ], { fontSize: 13.5, gap: 12 });
  callout(s, 8.3, 1.8, 4.45, 2.3, "A documented trap: SqliteSaver.from_conn_string() is a context manager — it closes the connection on exit. The build uses a singleton over sqlite3.connect() instead; the notebook shows the two-process pattern for reference.", "amber", { fontSize: 12.5 });
}

// ---------------------------------------------------------------- Slide 26 (Q3)
{
  const s = pres.addSlide();
  title(s, "Q · “Why did behavior differ between providers?”", { fontSize: 24 });
  bullets(s, MX, 1.35, 12.2, 3.2, [
    "Same open model, two hosts: the primary routed one clean handoff every time; the second host's internal routing sometimes ping-ponged transfers, and once leaked the model's reasoning channel into the visible answer.",
    "Engineering response: an explicit stop rule in the supervisor prompt · output_mode=\"full_history\" so the supervisor relays the worker's answer rather than the transfer receipt · the final evidence run captured on the primary provider.",
    "The tests assert the handoff HAPPENED — not how many times. Behavior contracts, not provider trivia.",
  ], { fontSize: 13.5, gap: 12 });
  callout(s, MX, 5.2, W - 2 * MX, 0.9, "MUNASSIQ_PROVIDER / MUNASSIQ_MODEL swap hosts with zero code changes — the incident became a feature.", "green", { bold: true, fontSize: 13.5 });
}

// ---------------------------------------------------------------- Slide 27 (Q4)
{
  const s = pres.addSlide();
  title(s, "Q · “Where exactly did the tokens go?”", { fontSize: 24 });
  tbl(s, MX, 1.35, 6.2,
    ["Node", "Observed"],
    [
      ["evaluate_draft (max)", "21.7s — the judge outweighs the writer"],
      ["run_tool_with_llm_recovery", "35.3s — two model calls by design"],
      ["classify_request", "11.4s"],
      ["compose_draft", "3.3s"],
    ],
    [2.6, 3.6], { fSize: 11.5 });
  s.addText("Free-tier arithmetic", { x: 7.1, y: 1.35, w: 5.6, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  bullets(s, 7.1, 1.8, 5.6, 3.2, [
    "200K tokens/day per model on the free tier — 8K per minute.",
    "One agentic request ≈ 5–10K tokens (memory + triage + supervisor + worker round trip).",
    "One live suite run ≈ 30–50K — which is exactly why the offline/live split (-m \"not api\") exists.",
  ], { fontSize: 12.5, gap: 10 });
}

pres.writeFile({ fileName: "munassiq-capstone.pptx" }).then(() => console.log("DECK WRITTEN"));
