# Write-up draft — "Munassiq" (المُنسِّق)

> A working draft that the owner rephrases in his own voice before submission. What
> is here is fact-checked raw material, not final prose.
>
> **Governing rule**: every sentence here must be matched by something visible in the
> notebook or in the tests. Whatever has not been built yet stays a marked blank — it
> is never filled in by guesswork.

**The project**: Munassiq — an office assistant for a non-profit association, on
**Track A** (a Supervisor plus three workers: calendar, knowledge, and
correspondence).

---

## 1 — Agent fundamentals: tools that use their arguments, and structured output

**What was built**: three tools defined with `@tool` in `src/munassiq/tools.py`, and a
structured triage output `TriageDecision` obtained through `with_structured_output`.

**The decision**: every tool **actually uses its arguments** — `create_event(title,
day)` appends to the `CALENDAR` list an entry derived from both of them, so different
arguments yield a different state and a different return value. And the routing
decision is read from a validated field (`worker` drawn from a closed list,
`needs_human_approval` a boolean) rather than from free text searched with `in`.

**Why**: a tool that ignores what is passed to it is not a tool call, it is a function
that decorates the output; and the difference shows up the moment the arguments differ,
not the moment the call succeeds. Likewise, searching for a word inside free text
passes silently whenever the model phrases its decision differently, whereas a
structured field either arrives with a value from the closed list or fails validation
explicitly.

---

## 2 — Supervisor and routing: the Orchestrator-Worker pattern

**What was built**: a supervisor via `create_supervisor` in
`src/munassiq/supervisor.py` on top of three workers, each of them a full ReAct agent
in `src/munassiq/workers.py`.

**The named decision**: **Orchestrator-Worker** — a single coordinator reads the
request and delegates it to the specialist, and each worker holds the tools of its own
speciality alone. Routing is a **model decision**, not a chain of conditionals:
`create_supervisor` derives a handoff tool `transfer_to_<name>` from each worker's
name, so the delegation shows up in the messages as an explicit tool call — which is
the evidence printed in the notebook and in `tests/test_supervisor.py`.

**Why**: the office's requests are mixed in nature (booking an appointment, asking
about a policy, drafting a letter) and their tools are unalike, so a single agent
carrying all the tools confuses them. The separation is a restriction **by structure**,
not a plea in the instruction text: the calendar worker cannot even see the mail tool,
so it has no way to drift into it. And the supervisor's prompt forbids it, in words,
from answering by itself, because without that ban the model tends to satisfy the
request on its own — out comes a plausible answer with no tool call at all and an
empty calendar.

---

## 3 — RAG: choosing between 2-Step, Agentic, and Hybrid

**What was built**: a retrieval pipeline in `src/munassiq/rag.py` over the synthetic
documents in `data/corpus/` (500/50 chunking, a Chroma index, fastembed embeddings),
and a single search tool in the hands of the knowledge worker.

Three patterns were open to Munassiq: **2-Step RAG** retrieves once before every
answer and generates from it; **Agentic RAG** makes retrieval a tool in the hands of
an agent that decides for itself when to query, with what wording, and how many times;
and **Hybrid RAG** sits between them, always retrieving a first time and leaving an
additional query to the agent when needed.

The choice here is **Agentic RAG**: the office's requests are mixed in nature —
booking an appointment, drafting a letter, asking about a policy — and the supervisor
delegates each request to its own worker, so the knowledge worker alone receives
whatever deserves retrieval. The policy questions themselves also vary: some are
settled by a single result, while others have their answer split across two documents
and need a second query worded differently, and that is a decision that cannot
sensibly be fixed in advance inside a rigid pipeline.

The counterpart is stated without varnish: **2-Step** is simpler, cheaper, and steadier
in latency — one retrieval step of known cost — but it retrieves for every request,
including requests that need no retrieval at all, so it pays an embedding and context
cost on an appointment-booking request that has nothing to do with the documents.
**Hybrid** eases that partly but keeps the first retrieval mandatory. And the price of
Agentic is that the number of calls is not bounded in advance: higher latency, less
predictable cost, and behaviour that depends on the quality of the instructions —
which is why the knowledge worker was restricted to a single tool and instructed in
words to answer from the retrieved passages alone, and to say «لا أجد» ("I cannot find
it") when they are absent.

**A decision forced by experiment**: fastembed's default embedding model is English
(`bge-small-en`) and it failed on Arabic — it retrieved passages unrelated to the
question; the model adopted is `paraphrase-multilingual-MiniLM-L12-v2`. And the test
asserts on the **verbatim planted fact** in the document rather than on the
plausibility of the model's answer.

---

## 4 — Memory: two different kinds, not one kind on two scales

**What was built**: `SqliteSaver` keyed by `thread_id` for short-term memory, and a
Store namespaced by `("memories", user_id)` for long-term memory, both on disk in
`src/munassiq/memory.py`.

**The decision**: the fact is written into a store that lives **outside the thread**,
and is injected into the context on every journey **unconditionally** from the
entrypoint body. And `from_conn_string` is not used: it is a context manager that
closes the connection on leaving the `with` block, so using it outside that block
gives an object over a closed connection — it works on the first line and fails on the
second. That is why the connection is built and passed straight to the constructor.

**Why**: messages piling up in a single thread are **not** long-term memory, they are
conversation context — and this is what candidates get wrong most often. So the
acceptable evidence is threefold: a write on `nb-thread-1`, then `store.search` showing
the fact stored outside the thread, then a call from `nb-thread-2` that shares not one
message with the first. And had injection been left to a tool the model chooses to
call, recall would become a probability rather than a guarantee — what is required is
memory that works, not memory that is available.

---

## 5 — Human-in-the-loop: interrupt, then resume

**What was built**: an `interrupt` in the body of the `@entrypoint` before the
irreversible act, a resume with `Command(resume=...)` on the same thread, and then a
write into the outbox.

**The decision**: the pause presents the human with a **pre-composed** draft, so what
is reviewed is a text and not a blank; the pause sits in the entrypoint body itself,
not inside a `@task`; and what comes back from the resume travels **verbatim** to the
outbox without passing through any model (the function `send_approved_email` is not a
`@tool` at all, so it is out of the model's reach).

**Why**: a `@task` is a unit that is re-run or restored whole, so pausing in the middle
of one means re-executing everything before it on resume. And any pass through a model
after approval would have changed a character — and then what came out would no longer
be the human's text. That is why the test asserts **exact equality**, not containment,
between the resume text and the contents of the outbox file. And no real e-mail is sent
in this project: "sending" means writing into the local `data/outbox/`.

---

## 6 — Functional API and the two error strategies

**What was built**: one `@entrypoint` and a set of `@task`s, with two strategies for
handling errors in `src/munassiq/workers.py`: `RetryPolicy(max_attempts=3)` on the task
for transient failure, and feeding the error text back into the model's context as a
correction message for input error.

**The decision**: the entrypoint body is **pure glue** — a condition, `@task` calls, and
the collection of their results; every model call and every side effect lives inside a
`@task`.

**Why**: the reason is mechanical, not cosmetic — on resume after an `interrupt` the
entrypoint body is re-executed from its start, while the results of completed `@task`s
are read from the checkpointer and are not re-run; so a line that calls a model outside
a `@task` means a duplicated bill and a different result from the one the decision was
built on. As for separating the two strategies, it is because the **owner of the fix**
differs, not because the errors differ in severity: nobody owns the fix for a transient
failure and time alone repairs it, so the attempts are left to LangGraph and appear
numbered in the checkpointer and in the trace, instead of being hidden by a
`try/except` loop inside a single, apparently successful call — and once they are
exhausted the exception **propagates** rather than being swallowed. With an input error,
by contrast, blind repetition resends the same input so the same error recurs forever;
the remedy is for the error text to become information inside the model's context that
it learns from.

The correction loop's cap is a **parameter**, not a hard-coded ceiling:
`run_tool_with_llm_recovery(..., max_attempts=2)`. Two is the deliberate default under a
free daily token budget — the cost of every extra round is one full model call — and a
deployment with a paid tier raises it in one argument, with no code change.

---

## 7 — The named pattern: Evaluator-Optimizer

**What was built**: a loop inside `draft_correspondence`: a generator writes the draft,
then an evaluator issues a **structured** verdict (`DraftVerdict`, with the fields
`score`, `approved`, and `feedback`), then an optimizer rewrites it using the feedback
if it was rejected, and it is evaluated again — under a hard cap of two rounds.

**The named decision**: **Evaluator-Optimizer**, with the whole loop running **before**
the human pause and folded inside a single `@task`, and the decision read from the
`approved` field alone.

**Why**: a letter going out in the association's name has an acceptance standard that
can be said out loud — it conveys everything that was asked, adds nothing that was not
in the request, in concise formal Arabic, with a greeting and a closing — and that is
exactly the success condition for this pattern: a critic able to say what should be
fixed and how, not merely "make it better". The hard cap exists because an evaluator
that is never convinced runs an endless loop. Reading from the structured field matters
because a rejecting verdict may mention the word "approved" as a negation or a
quotation, and then something that ought to have been improved slips through. And
folding the loop into a single `@task` makes it restore as one unit on resume instead
of having its rounds re-run.

---

## 8 — LangSmith tracing

**What was built**: tracing enabled from `.env`, a guard in `src/munassiq/tracing.py`
that fails early if tracing is off, and a polling wait for the appearance of a run born
**after** the `since` instant captured before the model call.

**The decision**: the variable name is `LANGCHAIN_TRACING_V2` literally, and the guard's
message names both the correct and the incorrect spelling. And nothing is printed from
the run but its id, its name, and its status.

**Why**: the name `LANGSMITH_TRACING_V2` looks perfectly correct and nobody complains
about it — not LangChain, not LangSmith, not the Python interpreter — but tracing is
then **off**: a silent failure discovered only through the absence of runs from the
dashboard. And capturing `since` before the call is what makes the wait evidence that
tracing works **now**, not that it worked some day. The wait is polling with a timeout
rather than a fixed sleep, because a run may appear after a second or take ten. The
redaction is deliberate: the runs' inputs and outputs carry members' texts and
correspondence.

**What the trace actually showed** (from the runs of the munassiq-capstone project, the
19 August session): the Evaluator-Optimizer loop is the real bottleneck — composing the
draft (compose_draft) took 3.3 seconds while evaluating it (evaluate_draft) reached 21.7
seconds, that is, the structured judge is about seven times slower than the writer,
because constrained Pydantic output forces the model into finer planning. The trace also
showed the tool-correction loop (run_tool_with_llm_recovery) at 35.3 seconds spanning
two consecutive model calls — the failed attempt and the correction message — which is
exactly what it was designed to do.

One point worth stating precisely: swapping the **model host** (Groq ↔ OpenRouter, same
open model) never split the observability. LangSmith is the single tracing backend for
every run in this project — all traces, across both hosts and all days, land in the one
`munassiq-capstone` project; the host swap only changes the name of the LLM node inside
a trace (`ChatGroq` vs `ChatOpenAI`), which itself is useful evidence of the swap.

---

## Declared limitation — composite requests span two turns

A request that needs retrieval AND sending in one message ("look up the leave
policy and e-mail a summary") is not served in a single turn: the classifier
routes by the dominant intent (correspondence), and the drafting path deliberately
has no retrieval tool, while the supervisor path deliberately cannot send. This
is the price of the safety property we chose — the send lives behind exactly one
human gate, and nothing reaches the outbox any other way. The evolution path is
already idiomatic in this codebase: inject `search_policies` passages into
`compose_draft` deterministically, exactly as memories are injected — enriching
the draft without ever handing send authority to a model.

## Appendix — model substitution and account limits

The course model `llama-3.3-70b-versatile` is **not available on the Groq account used**:
every call against it comes back `404`, as established by a spike before the build
began. It was replaced with the open model `openai/gpt-oss-120b`, which succeeded at
tool calls, supervisor handoffs, and structured output. Development and slice building
ran on it through **Groq** until the free daily quota (200K tokens) was exhausted; the
**final evidence run — the executed notebook and the integration test — was then
captured on the same model through a second provider (OpenRouter)** on an independent
budget. The variables `MUNASSIQ_PROVIDER` / `MUNASSIQ_MODEL` switch provider and model
with no code change. Smaller alternatives were tried when the quota ran tight and failed
qualitatively on structured output (a mangled tool name, a boolean returned as a
string); `llama-3.3-70b` itself was also tried through OpenRouter and entered a
non-terminating handoff loop in the supervisor — so `gpt-oss-120b` alone was fixed on.
A documented observation: OpenRouter's internal routing between its hosts makes the
number of handoff round trips fluctuate from one run to another (one clean handoff, or
identical repetitions) — provider behaviour, not a code fault, and the project's tests
assert that the handoff occurred, not how many times.

The Groq free-account limit is counted per model, and reaching it returns `429`; that is
why the tests that genuinely call the model were isolated behind the `api` marker, and
`pytest -m "not api"` passes without consuming any quota.
