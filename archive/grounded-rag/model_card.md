# 🔎 Model Card: GroundedRAG

## 1. Model Name

**GroundedRAG 1.0** — a retrieval-augmented, self-checking question-answering
system. It answers questions about a document collection, grounds every answer in
retrieved passages with citations, verifies its own answer, and abstains when the
documents don't support one.

---

## 2. Intended Use

**Goal:** Give trustworthy, source-cited answers about a specific set of
documents (notes, reference material, PDFs) — and to *refuse* rather than guess
when the answer isn't in those documents.

**Good for:**
- Studying/reference Q&A over a curated, trusted document set.
- Demonstrating a reliable RAG pipeline (retrieval + grounding + self-check).
- Learning how guardrails and evaluation make an AI system dependable.

**Not intended for:**
- Open-domain questions outside the indexed documents (it will abstain).
- High-stakes decisions (medical, legal, financial) without human review.
- A source of truth beyond the quality of the documents it was given.

---

## 3. How the Model Works

For every question, GroundedRAG runs a multi-step **agentic pipeline** rather
than a single model call:

1. **Guardrail** — validate the input (reject empty or over-long questions).
2. **Plan** — turn the question into focused search queries.
3. **Retrieve** — find the most similar document chunks using TF-IDF cosine
   similarity (vector search).
4. **Guardrail** — if the best match scores below a threshold, abstain.
5. **Answer** — answer using *only* the retrieved chunks, with citations.
6. **Verify** — a separate self-check confirms every claim is supported by the
   cited chunks.
7. **Retry / Abstain** — if the answer isn't grounded, re-plan and retry; if it
   still isn't grounded, abstain safely.

The model backend is swappable: **Claude (`claude-opus-4-8`)** for planning,
answering, and verification, or a **deterministic offline backend** (extractive
answers + lexical grounding checks) that needs no API key or network.

---

## 4. Data

The knowledge base is a small, curated set of five Markdown documents about AI
concepts (RAG, vector search, prompting, evaluation, guardrails) in `data/docs/`,
split into 13 retrievable chunks. The evaluation set (`data/eval/qa_eval.jsonl`)
is a gold set of 10 questions — 8 answerable from the documents and 2
deliberately out-of-scope — used to measure the system's behavior. Answers are
only ever as good as the documents provided; the system does not use outside
knowledge.

---

## 5. Evaluation

Run with `python -m src.ragqa.cli eval`. On the bundled corpus (offline backend):

| Metric | Result | Meaning |
|--------|--------|---------|
| Abstention accuracy | **100% (10/10)** | Answers answerable questions, refuses out-of-scope ones |
| Groundedness rate | **100% (8/8)** | Answered questions are verified as supported by sources |
| Retrieval hit rate | **100% (8/8)** | Retrieval surfaced an expected source document |
| Keyword recall | **88%** | Answers contained the expected key facts |

The suite also includes **27 automated tests** (`pytest`), all passing, run fully
offline for reproducibility.

---

## 6. Responsible-AI Reflection

### What are the limitations or biases in my system?

**Limitations:**
- **Lexical retrieval.** TF-IDF matches wording, not deeper meaning, so a
  question phrased very differently from the source text may retrieve poorly —
  even when the answer is present.
- **Small, curated corpus.** Answers are only as good as the indexed documents;
  the system cannot answer anything outside them (by design, it abstains).
- **Extractive offline answers.** The offline backend stitches answers from
  source sentences, so they read less fluently than Claude's and can miss a
  distinctive term (this is the cause of the 88% keyword recall).
- **Threshold sensitivity.** The abstention threshold is tuned for this corpus; a
  badly set threshold makes the system over-refuse or over-answer.
- **Not for high-stakes use.** Even a grounded answer only reflects the provided
  documents, which may themselves be incomplete or wrong.

**Biases:**
- **Corpus bias — the biggest one.** The system faithfully mirrors whatever is in
  `data/docs/`. If the source documents are one-sided, outdated, or wrong, the
  answers will be too — and, worse, the citations make those answers *look*
  authoritative. Grounding removes hallucination bias but introduces
  *source bias*: the system is exactly as fair, complete, and accurate as its
  documents.
- **Frequency/phrasing bias.** TF-IDF and the extractive backend both favor
  common query terms, so passages and phrasings that use frequent words are
  surfaced over equally-relevant but differently-worded ones. This can
  systematically under-serve questions asked in less common language.
- **Threshold bias.** A single global abstention threshold can under-serve
  legitimate questions whose vocabulary happens to overlap weakly with the docs,
  refusing them while answering others of equal merit.

### Could my AI be misused, and how would I prevent it?

Yes. The most realistic misuse is **manufacturing false authority**: point the
system at biased, misleading, or fabricated documents, and it will produce
confident, *cited* answers that lend those sources unearned credibility — the
citations make misinformation look verified. A second risk is **prompt injection
through documents**: a malicious file in the corpus could contain instructions
intended to hijack the model's behavior. A third is simply **over-reliance** —
users trusting answers on high-stakes topics without checking the sources.

Preventions, some already built in and some operational:
- **Citations on every claim** so a human can trace and verify each answer
  against its source rather than taking it on faith.
- **Abstention guardrails** (retrieval threshold + grounding self-check) so the
  system refuses rather than fabricating when evidence is weak.
- **Source curation + human review** — the corpus is a trust boundary; only
  vetted documents should be indexed, and the evaluation report and per-answer
  traces are designed to be read by a person.
- **Input validation** (length limits, empty-input rejection) to reduce the
  attack surface.
- **Scope and framing** — the model card explicitly states the system is *not*
  for high-stakes decisions and answers only reflect the provided documents.
- **Future hardening** — treat retrieved document text as untrusted data, not
  instructions, to defend against prompt injection.

### What surprised me while testing my AI's reliability?

- **Abstention was the hardest thing to get right — and the most important.**
  Teaching the system to confidently say *"I don't have enough information"* took
  more tuning than making it answer. It's also what separates a trustworthy
  assistant from a confident liar.
- **Reliability lived in a single number.** Whether an out-of-scope question was
  refused or answered came down to a retrieval score of 0.087 versus a threshold
  of 0.12 — a reminder that "safe behavior" can hinge on one tunable value, and
  that the value has to be *measured*, not guessed.
- **A unit-test-clean system still failed the evaluation.** The individual
  functions all passed their tests, yet the *end-to-end* evaluation caught a
  behavioral bug (see below). Evaluating the whole pipeline's behavior found
  something that testing the parts did not.

### My collaboration with AI (one helpful, one flawed suggestion)

I built this project as a pair-programming collaboration with an AI coding
assistant (Claude). I set the direction and requirements — a RAG system with an
advanced integrated AI feature, guardrails, logging, tests, and an evaluation
harness — and the assistant helped design and implement the modules. Crucially,
**I did not just accept the output**: I installed and ran the code, ran the tests
and evaluation harness, read the actual answers, and fixed what was wrong. The AI
accelerated the *writing*; the *verification* was mine.

**One helpful suggestion.** The assistant proposed a **two-backend design**: the
real Claude backend *and* a deterministic offline backend behind the same
interface, selected automatically based on whether an API key is present. This
was genuinely valuable — the whole project and all 27 tests run and pass on any
machine with no API key and no network, so a reviewer can reproduce it instantly,
while Claude is still there for high-quality answers. It solved reproducibility
without weakening the system.

**One flawed suggestion.** The AI-written configuration had a real bug. It set a
new default for the retrieval abstention threshold on the config *dataclass*, but
a separate `load_config()` function was still **hard-coding the old value**, so
the change silently had no effect. The symptom only appeared when the evaluation
harness failed: the out-of-scope question "What is the boiling point of water?"
that *should* have been refused was being answered. I traced it to the duplicated
default, fixed the value `load_config()` actually used, and the evaluation went
green. The lesson stuck: AI-generated code can look correct and still be subtly
wrong, and **running the evaluation is what caught it — not reading the code**.

---

## 7. Future Work

1. Add a dense-embedding retriever (e.g. sentence-transformers) behind the same
   retriever interface to capture meaning, not just wording.
2. Stream Claude's answer token-by-token in the CLI and web UI.
3. Add an LLM-as-judge grader and expand the gold evaluation set.
4. Cache planning/verification results to reduce cost and latency.
