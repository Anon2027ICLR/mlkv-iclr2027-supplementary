#!/usr/bin/env python3
"""Measure the static trailing-block token counts for the template survey.

Records T01-T22 were collected and locked in
docs/template-survey-report.md (commit 60d3daf); the measurement rules
were preregistered in docs/iclr-template-survey-preregister.md (commit
813bcad) BEFORE this script first ran. The trailing-block strings below
are transcribed verbatim from the locked report; T06 and T18 were
independently re-rendered from their permalinked sources and reproduce
the report's character counts exactly (348 and 1,005).

Rule: unfilled placeholders are deleted (empty-string instantiation), so
every count is a lower bound; tokenization is add_special_tokens=False.

  UV_NO_SYNC=1 uv run python scripts/template_survey_measure.py
"""
from __future__ import annotations

import re
import sys

# (id, name, category, trailing block verbatim; None = grows-only record)
RECORDS = [
    ("T01", "LangChain RetrievalQA completion", "A", "\nHelpful Answer:"),
    ("T02", "LangChain RetrievalQA chat", "A", ""),
    ("T03", "LangChain hub retrieval-qa-chat", "A", ""),
    ("T04", "LlamaIndex DEFAULT_TEXT_QA", "A", "\nAnswer: "),
    ("T05", "LlamaIndex CHAT_TEXT_QA user body", "A", "\nAnswer: "),
    ("T06", "LlamaIndex DEFAULT_REFINE", "A",
     "\nWe have provided an existing answer: {existing_answer}\nWe have "
     "the opportunity to refine the existing answer (only if needed) with "
     "some more context below.\n------------\n{context_msg}\n------------\n"
     "Given the new context, refine the original answer to better answer "
     "the query. If the context isn't useful, return the original answer.\n"
     "Refined Answer: "),
    ("T07", "LlamaIndex CHAT_REFINE", "A",
     "\nOriginal Answer: {existing_answer}\nNew Answer: "),
    ("T08", "Haystack PromptBuilder example", "A", "\n        Answer:\n        "),
    ("T09", "RAGFlow chat assembly", "A", ""),
    ("T10", "OpenAI Structured Outputs", "B", ""),
    ("T11", "OpenAI function calling turn 1", "B", ""),
    ("T12", "OpenAI JSON mode example", "B",
     " Please respond in the format {winner: ...}"),
    ("T13", "Anthropic tool use turn 1", "B", ""),
    ("T14", "Instructor canonical", "B", ""),
    ("T15", "Outlines canonical", "B", ""),
    ("T16", "Guidance gen_json", "B", ""),
    ("T17", "LangChain ReAct static suffix", "C", "\nThought:{agent_scratchpad}"),
    ("T18", "SWE-agent instance template", "C",
     "\n</pr_description>\n\nCan you help me implement the necessary "
     "changes to the repository so that the requirements specified in the "
     "<pr_description> are met?\nI've already taken care of all changes to "
     "any of the test files described in the <pr_description>. This means "
     "you DON'T have to modify the testing logic or any of the tests in "
     "any way!\nYour task is to make the minimal changes to non-tests "
     "files in the {{working_dir}} directory to ensure the "
     "<pr_description> is satisfied.\nFollow these steps to resolve the "
     "issue:\n1. As a first step, it might be a good idea to find and "
     "read code relevant to the <pr_description>\n2. Create a script to "
     "reproduce the error and execute it with `python <filename.py>` "
     "using the bash tool, to confirm the error\n3. Edit the sourcecode "
     "of the repo to resolve the issue\n4. Rerun your reproduce script "
     "and confirm that the error is fixed!\n5. Think about edgecases and "
     "make sure your fix handles them as well\nYour thinking should be "
     "thorough and so it's fine if it's very long."),
    ("T19", "OpenHands mid-loop assembly", "C", None),
    ("T20", "lm-eval-harness XQuAD en", "D", "\n\nAnswer:"),
    ("T21", "lm-eval-harness XQuAD ar", "D", "\n\nإجابة:"),
    ("T22o", "Belebele official zero-shot", "D",
     "\n###\nChoices:\n(A) {A}\n(B) {B}\n(C) {C}\n(D) {D}\n###\nAnswer:\n"),
    ("T22h", "Belebele harness default", "D",
     "\nA: {{mc_answer1}}\nB: {{mc_answer2}}\nC: {{mc_answer3}}\n"
     "D: {{mc_answer4}}\nAnswer:"),
]

# Preregistered character counts from the locked report; a transcription
# mismatch here means THIS file is wrong, not the report.
EXPECTED_CHARS = {"T01": 16, "T04": 9, "T05": 9, "T06": 348, "T07": 48,
                  "T08": 25, "T12": 43, "T17": 27, "T18": 1005, "T20": 9,
                  "T21": 8, "T22o": 58, "T22h": 80}

PLACEHOLDER = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{[^{}]*\}")


def main() -> int:
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-4B")

    bad = 0
    for tid, want in EXPECTED_CHARS.items():
        got = next(len(r[3]) for r in RECORDS if r[0] == tid)
        if got != want:
            print(f"TRANSCRIPTION MISMATCH {tid}: {got} chars vs report {want}")
            bad += 1
    if bad:
        return 1

    print(f"{'ID':5} {'cat':3} {'chars':>6} {'tokens':>7} {'>32':>4} {'>64':>4}  name")
    crossings = {32: [], 64: []}
    for tid, name, cat, block in RECORDS:
        if block is None:
            print(f"{tid:5} {cat:3} {'--':>6} {'grows':>7} {'--':>4} {'--':>4}  {name} (no static form)")
            continue
        cleaned = PLACEHOLDER.sub("", block)
        n = len(tok(cleaned, add_special_tokens=False)["input_ids"]) if cleaned else 0
        c32, c64 = n > 32, n > 64
        for t, yes in ((32, c32), (64, c64)):
            if yes:
                crossings[t].append(tid)
        print(f"{tid:5} {cat:3} {len(block):6} {n:7} {str(c32):>4} {str(c64):>4}  {name}")

    print(f"\ncrosses 32: {crossings[32] or 'none'}")
    print(f"crosses 64: {crossings[64] or 'none'}")
    print("\npreregistered checks:")
    t06 = next(r for r in RECORDS if r[0] == "T06")
    t18 = next(r for r in RECORDS if r[0] == "T18")
    n06 = len(tok(PLACEHOLDER.sub("", t06[3]), add_special_tokens=False)["input_ids"])
    n18 = len(tok(PLACEHOLDER.sub("", t18[3]), add_special_tokens=False)["input_ids"])
    singles = {"T01", "T04", "T05", "T08"}
    n_singles = {tid: len(tok(PLACEHOLDER.sub("", b), add_special_tokens=False)["input_ids"])
                 for tid, _, _, b in RECORDS if tid in singles}
    print(f"  pred1 single-shot RAG all <32: {n_singles} -> "
          f"{'HOLD' if all(v < 32 for v in n_singles.values()) else 'MISS'}")
    print(f"  pred2 T06 >= 32: {n06} -> {'HOLD' if n06 >= 32 else 'MISS'}")
    print(f"  pred3 T18 >= 64: {n18} -> {'HOLD' if n18 >= 64 else 'MISS'}")
    print(f"  kill (T06<32 and T18<32): "
          f"{'FIRES' if n06 < 32 and n18 < 32 else 'does not fire'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
