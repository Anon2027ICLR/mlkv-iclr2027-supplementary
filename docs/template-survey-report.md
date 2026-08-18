# Template survey (preregister collection)

- Date written: 2026-08-18
- Collector: Grok 4.6 (xAI)
- Access-date range: 2026-08-18
- Scope: collection and documentation only. Templates were selected by the
  brief's popularity/officialness bar before layout was scored. No tokenizer
  was run. Character counts are Python `len` of the trailing block after the
  question/task placeholder, including later unfilled placeholders. They are
  not token counts and are not a `c` computation.

Inclusion was locked on the following 22 records (T01–T22). Safe
(question-last) layouts were retained.

## Summary table

| ID | name | category | question-last? | trailing-block chars | source permalink |
|---|---|---|---|---|---|
| T01 | LangChain RetrievalQA completion (`PROMPT`) | A | no | 16 | https://github.com/langchain-ai/langchain/blob/9f2d56e376ea926d334f8f99ed7c67b154c2f0bf/libs/langchain/langchain_classic/chains/question_answering/stuff_prompt.py |
| T02 | LangChain RetrievalQA chat (`CHAT_PROMPT`) | A | yes | 0 | https://github.com/langchain-ai/langchain/blob/9f2d56e376ea926d334f8f99ed7c67b154c2f0bf/libs/langchain/langchain_classic/chains/question_answering/stuff_prompt.py |
| T03 | LangChain hub `langchain-ai/retrieval-qa-chat` (official `create_retrieval_chain` example) | A | yes | 0 | https://api.smith.langchain.com/commits/langchain-ai/retrieval-qa-chat/b60afb6297176b022244feb83066e10ecadcda7b90423654c4a9d45e7a73cebc |
| T04 | LlamaIndex `DEFAULT_TEXT_QA_PROMPT_TMPL` | A | no | 9 | https://github.com/run-llama/llama_index/blob/3759b52cfb88dd966f9c4b0301a5583a6180ad1b/llama-index-core/llama_index/core/prompts/default_prompts.py |
| T05 | LlamaIndex `CHAT_TEXT_QA_PROMPT` user body | A | no | 9 | https://github.com/run-llama/llama_index/blob/3759b52cfb88dd966f9c4b0301a5583a6180ad1b/llama-index-core/llama_index/core/prompts/chat_prompts.py |
| T06 | LlamaIndex `DEFAULT_REFINE_PROMPT_TMPL` | A | no | 348 | https://github.com/run-llama/llama_index/blob/3759b52cfb88dd966f9c4b0301a5583a6180ad1b/llama-index-core/llama_index/core/prompts/default_prompts.py |
| T07 | LlamaIndex `CHAT_REFINE_PROMPT` | A | no | 48 | https://github.com/run-llama/llama_index/blob/3759b52cfb88dd966f9c4b0301a5583a6180ad1b/llama-index-core/llama_index/core/prompts/chat_prompts.py |
| T08 | Haystack `PromptBuilder` official in-source RAG pipeline example | A | no | 25 | https://github.com/deepset-ai/haystack/blob/2a0f2eda524c8b796ec88f8b404b40e0b072b645/haystack/components/builders/prompt_builder.py |
| T09 | RAGFlow chat assistant `systemInitialValue` + `async_chat` assembly | A | yes | 0 | https://github.com/infiniflow/ragflow/blob/c3153ba29471e117a7b4216c1d3cc45f3d20831f/web/src/locales/en.ts |
| T10 | OpenAI Structured Outputs (CalendarEvent example) | B | yes | 0 | https://developers.openai.com/api/docs/guides/structured-outputs |
| T11 | OpenAI function calling, first turn (`get_horoscope`) | B | yes | 0 | https://developers.openai.com/api/docs/guides/function-calling |
| T12 | OpenAI JSON mode official example | B | no | 43 | https://developers.openai.com/api/docs/guides/structured-outputs#json-mode |
| T13 | Anthropic tool-use official `get_weather` first turn | B | yes | 0 | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview |
| T14 | Instructor docs canonical `client.create` example | B | yes | 0 | https://python.useinstructor.com/ |
| T15 | Outlines README canonical `model(prompt, output_type)` example | B | yes | 0 | https://github.com/dottxt-ai/outlines/blob/7d068478851f7ba76cb53997673d57f77b2d6f84/README.md |
| T16 | Guidance README `gen_json` blood-pressure sample | B | yes | 0 | https://github.com/guidance-ai/guidance/blob/21b1d90dfbebff4b141df70c714c8af15aa5f4af/README.md |
| T17 | LangChain ReAct (`hwchase17/react` / `create_react_agent` official template) | C | no | 27 | https://github.com/langchain-ai/langchain/blob/9f2d56e376ea926d334f8f99ed7c67b154c2f0bf/libs/langchain/langchain_classic/agents/react/agent.py |
| T18 | SWE-agent `config/default.yaml` instance + next-step templates | C | no | 1005 | https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/config/default.yaml |
| T19 | OpenHands software-agent-sdk mid-loop `prepare_llm_messages` | C | no | (grows; no official rendered fixture) | https://github.com/OpenHands/software-agent-sdk/blob/98338ff37aea6627777b9978963ab727f51e4f40/openhands-sdk/openhands/sdk/agent/utils.py |
| T20 | lm-evaluation-harness XQuAD English | D | no | 9 | https://github.com/EleutherAI/lm-evaluation-harness/blob/8a07e1110d060de48cfc7a9a7987b7659060b60b/lm_eval/tasks/xquad/xquad_en.yaml |
| T21 | lm-evaluation-harness XQuAD Arabic | D | no | 8 | https://github.com/EleutherAI/lm-evaluation-harness/blob/8a07e1110d060de48cfc7a9a7987b7659060b60b/lm_eval/tasks/xquad/xquad_ar.yaml |
| T22 | Belebele official zero-shot chat (paper instructions) + harness default | D | no | 58 (official) / 80 (harness) | https://github.com/facebookresearch/belebele/blob/918890beb2290a8d3ef2d7a90369925959e1bacf/sample_zero_shot_instructions.md |

---

## T01 — LangChain RetrievalQA completion (`PROMPT`) — A

**Source.** Primary:
https://github.com/langchain-ai/langchain/blob/9f2d56e376ea926d334f8f99ed7c67b154c2f0bf/libs/langchain/langchain_classic/chains/question_answering/stuff_prompt.py
(`prompt_template`, lines 13–18). Selector used by
`BaseRetrievalQA.from_llm` at
https://github.com/langchain-ai/langchain/blob/9f2d56e376ea926d334f8f99ed7c67b154c2f0bf/libs/langchain/langchain_classic/chains/retrieval_qa/base.py
(import of `PROMPT_SELECTOR` at line 28; `from_llm` at lines 70–80:
`_prompt = prompt or PROMPT_SELECTOR.get_prompt(llm)`). Repo
`langchain-ai/langchain`: 144,446 stars, default branch `master`, HEAD
`9f2d56e376ea926d334f8f99ed7c67b154c2f0bf` on 2026-08-18. Accessed
2026-08-18.

**Verbatim template text.**

```
Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.

{context}

Question: {question}
Helpful Answer:
```

**Layout order.** `[instruction] [context] [question] [suffix]`

**The trailing block, verbatim.**

```
Helpful Answer:
```

Exact string, including the leading newline: `"\nHelpful Answer:"`

**Rough size.** 16 characters.

**Notes.** `PROMPT_SELECTOR.default_prompt` is this completion template.
Chat models are switched to T02. `RetrievalQA` is marked deprecated in
`base.py` (since 0.2.13) in favor of `create_agent`; it remains the
shipped classic default.

## T02 — LangChain RetrievalQA chat (`CHAT_PROMPT`) — A

**Source.** Same file and commit as T01, `system_template` / `messages` /
`CHAT_PROMPT` at lines 23–31. Same repo stars. Accessed 2026-08-18.

**Verbatim template text.**

System message:

```
Use the following pieces of context to answer the user's question.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
----------------
{context}
```

Human message:

```
{question}
```

**Layout order.** `[instruction] [context] [question]`

**The trailing block, verbatim.** trailing block: none (question-last)

**Rough size.** 0 characters.

**Notes.** Selected when `is_chat_model` is true. The human message is
exactly `{question}`.

## T03 — LangChain hub `langchain-ai/retrieval-qa-chat` — A

**Source.** `create_retrieval_chain` ships no QA prompt. Its official
docstring example pulls this hub prompt:
https://github.com/langchain-ai/langchain/blob/9f2d56e376ea926d334f8f99ed7c67b154c2f0bf/libs/langchain/langchain_classic/chains/retrieval.py
(lines 37–56, `hub.pull("langchain-ai/retrieval-qa-chat")`). Hub commit
body from
https://api.smith.langchain.com/commits/langchain-ai/retrieval-qa-chat/latest
on 2026-08-18, commit hash
`b60afb6297176b022244feb83066e10ecadcda7b90423654c4a9d45e7a73cebc`.
Versioned commit URL:
https://api.smith.langchain.com/commits/langchain-ai/retrieval-qa-chat/b60afb6297176b022244feb83066e10ecadcda7b90423654c4a9d45e7a73cebc
The LangSmith HTML pages for the same prompt did not return the body.
Same LangChain repo star count as T01. Accessed 2026-08-18.

**Verbatim template text.** Manifest `ChatPromptTemplate` messages:

System:

```
Answer any use questions based solely on the context below:

<context>
{context}
</context>
```

Optional `MessagesPlaceholder` `chat_history`.

Human:

```
{input}
```

**Layout order.** `[instruction] [context] [examples] [question]`
(`chat_history` mapped to `[examples]`).

**The trailing block, verbatim.** trailing block: none (question-last)

**Rough size.** 0 characters.

**Notes.** The system string is the hub text as stored (`Answer any use
questions`). The human key is `{input}`, not `{question}`.
`create_retrieval_chain` itself only assigns `context` and `answer`; the
prompt is supplied by the caller. This record is the prompt named in the
function's official example.

## T04 — LlamaIndex `DEFAULT_TEXT_QA_PROMPT_TMPL` — A

**Source.**
https://github.com/run-llama/llama_index/blob/3759b52cfb88dd966f9c4b0301a5583a6180ad1b/llama-index-core/llama_index/core/prompts/default_prompts.py
(lines 99–111). Selector
https://github.com/run-llama/llama_index/blob/3759b52cfb88dd966f9c4b0301a5583a6180ad1b/llama-index-core/llama_index/core/prompts/default_prompt_selectors.py
(`DEFAULT_TEXT_QA_PROMPT_SEL`, lines 45–48:
`default_template=DEFAULT_TEXT_QA_PROMPT`). Repo `run-llama/llama_index`:
51,720 stars, HEAD `3759b52cfb88dd966f9c4b0301a5583a6180ad1b` on
2026-08-18. Accessed 2026-08-18.

**Verbatim template text.**

```
Context information is below.
---------------------
{context_str}
---------------------
Given the context information and not prior knowledge, answer the query.
Query: {query_str}
Answer: 
```

**Layout order.** `[instruction] [context] [question] [suffix]`

**The trailing block, verbatim.**

```
Answer: 
```

Exact string, including the leading newline and trailing space: `"\nAnswer: "`

**Rough size.** 9 characters.

**Notes.** This is the selector default (non-chat, non-Cohere).

## T05 — LlamaIndex `CHAT_TEXT_QA_PROMPT` user body — A

**Source.**
https://github.com/run-llama/llama_index/blob/3759b52cfb88dd966f9c4b0301a5583a6180ad1b/llama-index-core/llama_index/core/prompts/chat_prompts.py
(`TEXT_QA_SYSTEM_PROMPT` lines 17–29; user body lines 31–46). Selected
for chat models by `DEFAULT_TEXT_QA_PROMPT_SEL` conditionals. Same repo
stars and commit as T04. Accessed 2026-08-18.

**Verbatim template text.**

System:

```
You are an expert Q&A system that is trusted around the world.
Always answer the query using the provided context information, and not prior knowledge.
Some rules to follow:
1. Never directly reference the given context in your answer.
2. Avoid statements like 'Based on the context, ...' or 'The context information ...' or anything along those lines.
```

User:

```
Context information is below.
---------------------
{context_str}
---------------------
Given the context information and not prior knowledge, answer the query.
Query: {query_str}
Answer: 
```

**Layout order.** `[system] [instruction] [context] [question] [suffix]`

**The trailing block, verbatim.**

Exact string: `"\nAnswer: "`

**Rough size.** 9 characters.

**Notes.** The chat user body still carries the `Answer: ` suffix. A
parallel `CHAT_CONTENT_QA_PROMPT` Rich template ends with
`Query: {{ query_str }}\nAnswer:`.

## T06 — LlamaIndex `DEFAULT_REFINE_PROMPT_TMPL` — A

**Source.** Same `default_prompts.py` commit as T04, lines 81–96. Selector
`DEFAULT_REFINE_PROMPT_SEL` defaults to this template. Accessed
2026-08-18.

**Verbatim template text.**

```
The original query is as follows: {query_str}
We have provided an existing answer: {existing_answer}
We have the opportunity to refine the existing answer (only if needed) with some more context below.
------------
{context_msg}
------------
Given the new context, refine the original answer to better answer the query. If the context isn't useful, return the original answer.
Refined Answer: 
```

**Layout order.** `[question] [instruction] [context] [instruction] [suffix]`

**The trailing block, verbatim.**

```
We have provided an existing answer: {existing_answer}
We have the opportunity to refine the existing answer (only if needed) with some more context below.
------------
{context_msg}
------------
Given the new context, refine the original answer to better answer the query. If the context isn't useful, return the original answer.
Refined Answer: 
```

Exact string (348 characters):

```
"\nWe have provided an existing answer: {existing_answer}\nWe have the opportunity to refine the existing answer (only if needed) with some more context below.\n------------\n{context_msg}\n------------\nGiven the new context, refine the original answer to better answer the query. If the context isn't useful, return the original answer.\nRefined Answer: "
```

**Rough size.** 348 characters.

**Notes.** The query placeholder is first. Later unfilled placeholders
`{existing_answer}` and `{context_msg}` are included in the character
count. The block scales with the existing answer and extra context at
runtime.

## T07 — LlamaIndex `CHAT_REFINE_PROMPT` — A

**Source.** Same `chat_prompts.py` commit as T05, `CHAT_REFINE_PROMPT_TMPL_MSGS`
lines 140–156. Selected for chat models by `DEFAULT_REFINE_PROMPT_SEL`.
Accessed 2026-08-18.

**Verbatim template text.** Single user message:

```
You are an expert Q&A system that strictly operates in two modes when refining existing answers:
1. **Rewrite** an original answer using the new context.
2. **Repeat** the original answer if the new context isn't useful.
Never reference the original answer or context directly in your answer.
When in doubt, just repeat the original answer.
New Context: {context_msg}
Query: {query_str}
Original Answer: {existing_answer}
New Answer: 
```

**Layout order.** `[instruction] [context] [question] [instruction] [suffix]`

**The trailing block, verbatim.**

Exact string: `"\nOriginal Answer: {existing_answer}\nNew Answer: "`

**Rough size.** 48 characters.

**Notes.** `{existing_answer}` is after the query. Runtime length scales
with the existing answer.

## T08 — Haystack `PromptBuilder` official in-source RAG pipeline example — A

**Source.**
https://github.com/deepset-ai/haystack/blob/2a0f2eda524c8b796ec88f8b404b40e0b072b645/haystack/components/builders/prompt_builder.py
Class docstring "In a Pipeline" example, `prompt_template` at lines
55–64. `__init__` at lines 141–154 requires `template: str` — there is
no shipped default string. Repo `deepset-ai/haystack`: 26,239 stars,
HEAD `2a0f2eda524c8b796ec88f8b404b40e0b072b645` on 2026-08-18. Accessed
2026-08-18.

**Obstacle.** Haystack has no single default QA template. This record is
the official in-source RAG pipeline example, not a hidden default.

**Verbatim template text.**

```
        Given these documents, answer the question.
        Documents:
        {% for doc in documents %}
            {{ doc.content }}
        {% endfor %}

        Question: {{query}}
        Answer:
        
```

(The source is a triple-quoted string that begins with a newline after
`prompt_template = """` and ends with the indented `Answer:` line plus
the indentation of the closing `"""`.)

**Layout order.** `[instruction] [context] [question] [suffix]`

**The trailing block, verbatim.**

Exact string: `"\n        Answer:\n        "`

**Rough size.** 25 characters.

**Notes.** A second official example in the same docstring
(`language_template`, lines 111–124) inserts
`Please provide your answer in {{ answer_language | default('English') }}`
between the question and `Answer:`. That second example is not a
separate locked record. Whitespace in the docs site YAML/Python
snippets can differ; the 25-character count is from this permalinked
source file.

## T09 — RAGFlow default chat system prompt + `async_chat` assembly — A

**Source.** Frontend shipped initial system text:
https://github.com/infiniflow/ragflow/blob/c3153ba29471e117a7b4216c1d3cc45f3d20831f/web/src/locales/en.ts
(`systemPlaceholder` line 1043; `systemInitialValue` line 1050).
Assembly:
https://github.com/infiniflow/ragflow/blob/c3153ba29471e117a7b4216c1d3cc45f3d20831f/api/db/services/dialog_service.py
(`async_chat` from line 581; system format at 832–841; citation
concatenated onto the system string at 963 / 983:
`chat_mdl.async_chat(prompt + prompt4citation, msg[1:], ...)`). Backend
`Dialog.prompt_config` default `system` is `""` in
https://github.com/infiniflow/ragflow/blob/c3153ba29471e117a7b4216c1d3cc45f3d20831f/api/db/db_models.py
Repo `infiniflow/ragflow`: 88,727 stars, HEAD
`c3153ba29471e117a7b4216c1d3cc45f3d20831f` on 2026-08-18. Accessed
2026-08-18.

**Verbatim template text.** `systemInitialValue` as stored in
`web/src/locales/en.ts`:

```
You are an intelligent assistant. Your primary function is to answer questions based strictly on the provided knowledge base.

      **Essential Rules:**
        - Your answer must be derived **solely** from this dataset: `{knowledge}`.
        - **When information is available**: Summarize the content to give a detailed answer.
        - **When information is unavailable**: Your response must contain this exact sentence: "The answer you are looking for is not found in the dataset!"
        - **Always consider** the entire conversation history.
```

`systemPlaceholder` (same file, slightly different wording and
indentation):

```
You are an intelligent assistant. Your primary function is to answer questions based strictly on the provided knowledge base.

**Essential Rules:**
  - Your answer must be derived **solely** from this dataset: {knowledge}.
  - **When information is available**: Summarize the content to give a detailed answer.
  - **When information is unavailable**: Your response must contain this exact sentence: "The answer you are looking for is not found in the knowledge base!"
  - **Always consider** the entire conversation history.
```

User turns are the conversation `messages` with
`assert messages[-1]["role"] == "user"`. Retrieved chunks replace
`{knowledge}` in the system string. If `{knowledge}` is absent and
chunks exist, the knowledge text is appended to the system string
(lines 833–836). `citation_prompt()` is concatenated onto the system
argument (`prompt + prompt4citation`), not onto the last user message.

**Layout order.** `[system] [context] [instruction] [question]`

**The trailing block, verbatim.** trailing block: none (question-last)

**Rough size.** 0 characters.

**Notes.** Knowledge and the citation prompt live in the system message,
which is passed as the first argument of `async_chat` and therefore
precedes `msg[1:]`. The last role in `messages` is required to be
`user`. Runtime system length scales with retrieved chunks and, when
quoting is on, with `rag/prompts/citation_prompt.md`. The backend DB
default `system` is the empty string; the UI initial value above is
what a newly created assistant is shown.

## T10 — OpenAI Structured Outputs (CalendarEvent) — B

**Source.** Official vendor docs, accessed 2026-08-18:
https://developers.openai.com/api/docs/guides/structured-outputs
(and `.md` sibling
https://developers.openai.com/api/docs/guides/structured-outputs.md).
The page is the current vendor document as of that date (no git
commit). Popularity: OpenAI vendor documentation (selection bar).

**Verbatim template text.** Canonical Python example on that page:

```python
response = client.responses.parse(
    model="gpt-5.6",
    input=[
        {"role": "system", "content": "Extract the event information."},
        {
            "role": "user",
            "content": "Alice and Bob are going to a science fair on Friday.",
        },
    ],
    text_format=CalendarEvent,
)
```

The schema is the Pydantic model `CalendarEvent` (`name`, `date`,
`participants`) supplied via `text_format` / `text.format` /
`json_schema`, not as message text.

**Layout order.** `[instruction] [question]`

**The trailing block, verbatim.** trailing block: none (question-last)

**Rough size.** 0 characters.

**Notes.** The docs state that Structured Outputs is supplied in
`text.format` (`json_schema`) or via function calling, not by appending
the schema after the user message. Other official examples on the same
page (math tutor, research-paper extraction, UI generation, moderation)
are the same layout: system instruction, user task last, schema in
`text.format`. The page does not print any hidden system text that the
API may inject for `json_schema`.

## T11 — OpenAI function calling, first turn — B

**Source.** Official vendor docs, accessed 2026-08-18:
https://developers.openai.com/api/docs/guides/function-calling
Python `get_horoscope` example. Same vendor bar as T10.

**Verbatim template text.** First request in the official Python
example:

```python
input_list = [{"role": "user", "content": "What is my horoscope? I am an Aquarius."}]

response = client.responses.create(
    model="gpt-5.6",
    tools=tools,
    input=input_list,
)
```

`tools` is a JSON-schema function definition (`get_horoscope` /
`sign`) passed as the `tools` parameter, not as a message.

**Layout order.** `[schema] [question]`
(schema in the API `tools` field; the only message is the user task.)

**The trailing block, verbatim.** trailing block: none (question-last)

**Rough size.** 0 characters.

**Notes.** The same page states: "Under the hood, functions are injected
into the system message in a syntax the model has been trained on."
That injected system text is not printed. The documented second request
appends `response.output` and a `function_call_output` item after the
original user message; the official sample output string is
`"{sign}: Next Tuesday you will befriend a baby otter."` That follow-up
is not a separate locked record. Schema size is user-supplied and
scales with the tool list.

## T12 — OpenAI JSON mode official example — B

**Source.** Same Structured Outputs page, JSON mode section, accessed
2026-08-18:
https://developers.openai.com/api/docs/guides/structured-outputs#json-mode

**Verbatim template text.** Official JavaScript/Python example input:

System:

```
You are a helpful assistant designed to output JSON.
```

User:

```
Who won the world series in 2020? Please respond in the format {winner: ...}
```

API field: `text: { format: { type: "json_object" } }`.

**Layout order.** `[instruction] [question] [schema]`

**The trailing block, verbatim.**

```
 Please respond in the format {winner: ...}
```

Exact string: `" Please respond in the format {winner: ...}"` (leading
space).

**Rough size.** 43 characters.

**Notes.** The docs require the string `JSON` to appear somewhere in
the context when JSON mode is on. The format instruction in this
canonical example is inside the user message, after the question. The
`json_object` field is not itself message text.

## T13 — Anthropic tool-use official `get_weather` first turn — B

**Source.** Official vendor docs, accessed 2026-08-18:
https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
Python client-tool round trip.

**Verbatim template text.** First request:

```python
tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a given location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state, e.g. San Francisco, CA",
                }
            },
            "required": ["location"],
        },
    }
]
messages = [{"role": "user", "content": "What's the weather in San Francisco?"}]
```

**Layout order.** `[schema] [question]`
(schema in the `tools` parameter.)

**The trailing block, verbatim.** trailing block: none (question-last)

**Rough size.** 0 characters.

**Notes.** Pricing table on the same page lists an extra automatic tool-use
system prompt (token counts only; wording not shown). The official
follow-up request appends the assistant `tool_use` block and a user
`tool_result` whose content in the docs is exactly
`15 degrees Celsius, partly cloudy` (33 characters). That follow-up is
not a separate locked record. Schema size is user-supplied.

## T14 — Instructor docs canonical example — B

**Source.** Official docs, accessed 2026-08-18:
https://python.useinstructor.com/
("Extract Structured Data" / OpenAI provider example). Repo
`567-labs/instructor` (same as `instructor-ai/instructor`): 13,744
stars, HEAD `6754a32b1e35d57dfd94aea8099be68478f1e133` on 2026-08-18.
The docs page is the canonical prompt shown in their docs.

**Verbatim template text.**

```python
person = client.create(
    response_model=Person,
    messages=[
        {"role": "user", "content": "Extract: John is a 30-year-old software engineer"}
    ],
)
```

and the OpenAI provider tab:

```python
res = client.create(
    response_model=ExtractUser,
    messages=[{"role": "user", "content": "John Doe is 30 years old."}],
)
```

**Layout order.** `[question]`

**The trailing block, verbatim.** trailing block: none (question-last)

**Rough size.** 0 characters.

**Notes.** The schema is `response_model`, not concatenated after the
user message in the documented examples. Whether a given `Mode` later
injects a schema into messages is not exhibited as the canonical prompt
on the inspected page.

## T15 — Outlines README canonical example — B

**Source.**
https://github.com/dottxt-ai/outlines/blob/7d068478851f7ba76cb53997673d57f77b2d6f84/README.md
Quickstart section. Repo `dottxt-ai/outlines`: 15,641 stars, HEAD
`7d068478851f7ba76cb53997673d57f77b2d6f84` on 2026-08-18. Accessed
2026-08-18.

**Verbatim template text.**

```python
sentiment = model(
    "Analyze: 'This product completely changed my life!'",
    Literal["Positive", "Negative", "Neutral"]
)

temperature = model("What's the boiling point of water in Celsius?", int)
```

**Layout order.** `[question]`

**The trailing block, verbatim.** trailing block: none (question-last)

**Rough size.** 0 characters.

**Notes.** The output type is the second argument of `model(...)`, not
text appended after the prompt. Later README examples follow the same
`model(prompt, ProductReview)` pattern.

## T16 — Guidance README `gen_json` sample — B

**Source.**
https://github.com/guidance-ai/guidance/blob/21b1d90dfbebff4b141df70c714c8af15aa5f4af/README.md
"Generating JSON" section. Repo `guidance-ai/guidance`: 21,713 stars,
HEAD `21b1d90dfbebff4b141df70c714c8af15aa5f4af` on 2026-08-18. Accessed
2026-08-18.

**Verbatim template text.**

```python
with system():
    lm += "You are a doctor taking a patient's blood pressure taken from their arm"

with user():
    lm += "Report the blood pressure"

with assistant():
    lm += gen_json(name="bp", schema=BloodPressure)
```

**Layout order.** `[instruction] [question]`

**The trailing block, verbatim.** trailing block: none (question-last)

**Rough size.** 0 characters.

**Notes.** `gen_json(..., schema=BloodPressure)` is on the assistant
side. The user/task string has nothing after it. Schema size is
user-supplied.

## T17 — LangChain ReAct — C

**Source.** Official example template inside `create_react_agent`:
https://github.com/langchain-ai/langchain/blob/9f2d56e376ea926d334f8f99ed7c67b154c2f0bf/libs/langchain/langchain_classic/agents/react/agent.py
(lines 90–124). Identical `SUFFIX` in
https://github.com/langchain-ai/langchain/blob/9f2d56e376ea926d334f8f99ed7c67b154c2f0bf/libs/langchain/langchain_classic/agents/mrkl/prompt.py
(lines 12–15). Hub prompt `hwchase17/react` pulled in the same
docstring (`hub.pull("hwchase17/react")`, line 68); latest hub commit
on 2026-08-18:
https://api.smith.langchain.com/commits/hwchase17/react/latest
hash `d15fe3c426f1c4b3f37c9198853e4a86e20c425ca7f4752ec0c9b0e97ca7ea4d`,
template identical to the in-source example. Scratchpad assembly:
https://github.com/langchain-ai/langchain/blob/9f2d56e376ea926d334f8f99ed7c67b154c2f0bf/libs/langchain/langchain_classic/agents/format_scratchpad/log.py
(`format_log_to_str`, lines 4–23). Wired at
`create_react_agent` lines 143–148:
`agent_scratchpad=lambda x: format_log_to_str(x["intermediate_steps"])`.
Same LangChain star count as T01. Accessed 2026-08-18.

**Verbatim template text.** Official example / hub body:

```
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}
```

`format_log_to_str` (defaults `observation_prefix="Observation: "`,
`llm_prefix="Thought: "`):

```python
thoughts = ""
for action, observation in intermediate_steps:
    thoughts += action.log
    thoughts += f"\n{observation_prefix}{observation}\n{llm_prefix}"
return thoughts
```

**Layout order.** `[instruction] [schema] [question] [suffix] [tool-output]`
(`{tools}` / `{tool_names}` mapped to `[schema]`;
`{agent_scratchpad}` is the growing `[suffix][tool-output]` after
`{input}`).

**The trailing block, verbatim.** After the `{input}` placeholder, the
static template is:

```
Thought:{agent_scratchpad}
```

Exact string, including the leading newline: `"\nThought:{agent_scratchpad}"`

**Rough size.** 27 characters for the static suffix including the
unfilled `{agent_scratchpad}` placeholder. At runtime the scratchpad
grows by `"\nObservation: " + observation + "\nThought: "` per step.

**Notes.** The user's question is rendered at `Question: {input}` near
the end of the prompt. Every later observation is written into
`agent_scratchpad` after that already-rendered question. Mid-loop
re-prefill is `prompt | llm` on the rebuilt scratchpad. No unit-test
fixture dumping a fully rendered multi-step prompt string was retrieved
from the repo on this access date.

## T18 — SWE-agent `config/default.yaml` — C

**Source.** Official default config:
https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/config/default.yaml
(`system_template` line 6; `instance_template` lines 8–27 with
`{{problem_statement}}` at line 15; `next_step_template` lines 28–30;
`parse_function: function_calling` at line 65). History assembly:
https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/agents.py
(`TemplateConfig.next_step_template` default `"Observation: {{observation}}"`
at line 67; `add_instance_template_to_history` at line 748;
`add_step_to_history` at line 714; `_add_templated_messages_to_history`
at line 675). Repo `SWE-agent/SWE-agent`: 20,073 stars, HEAD
`3ea751c087f32b16e039a2233dd6eefecef325d5` on 2026-08-18. Accessed
2026-08-18.

Worked example (shipped demonstration trajectory, not invented):
https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/trajectories/demonstrations/replay__marshmallow-code__marshmallow-1867__function_calling__install-1/marshmallow-code__marshmallow-1867.traj

**Verbatim template text.** `config/default.yaml` templates:

```
You are a helpful assistant that can interact with a computer to solve tasks.
```

```
<uploaded_files>
{{working_dir}}
</uploaded_files>
I've uploaded a python code repository in the directory {{working_dir}}. Consider the following PR description:

<pr_description>
{{problem_statement}}
</pr_description>

Can you help me implement the necessary changes to the repository so that the requirements specified in the <pr_description> are met?
I've already taken care of all changes to any of the test files described in the <pr_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!
Your task is to make the minimal changes to non-tests files in the {{working_dir}} directory to ensure the <pr_description> is satisfied.
Follow these steps to resolve the issue:
1. As a first step, it might be a good idea to find and read code relevant to the <pr_description>
2. Create a script to reproduce the error and execute it with `python <filename.py>` using the bash tool, to confirm the error
3. Edit the sourcecode of the repo to resolve the issue
4. Rerun your reproduce script and confirm that the error is fixed!
5. Think about edgecases and make sure your fix handles them as well
Your thinking should be thorough and so it's fine if it's very long.
```

```
OBSERVATION:
{{observation}}
```

**Layout order.** `[system] [context] [question] [instruction] [tool-output]`

**The trailing block, verbatim.** After `{{problem_statement}}` in
`instance_template`:

```
</pr_description>

Can you help me implement the necessary changes to the repository so that the requirements specified in the <pr_description> are met?
I've already taken care of all changes to any of the test files described in the <pr_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!
Your task is to make the minimal changes to non-tests files in the {{working_dir}} directory to ensure the <pr_description> is satisfied.
Follow these steps to resolve the issue:
1. As a first step, it might be a good idea to find and read code relevant to the <pr_description>
2. Create a script to reproduce the error and execute it with `python <filename.py>` using the bash tool, to confirm the error
3. Edit the sourcecode of the repo to resolve the issue
4. Rerun your reproduce script and confirm that the error is fixed!
5. Think about edgecases and make sure your fix handles them as well
Your thinking should be thorough and so it's fine if it's very long.
```

**Rough size.** 1005 characters for that static instance-template
suffix (including the unfilled `{{working_dir}}` later in the suffix).

**Notes.** Mid-loop: `add_step_to_history` appends an assistant action
and then a user/tool message from `next_step_template`. Each new
observation is therefore after the already-emitted instance message
that contains the problem statement. In the shipped function-calling
marshmallow demonstration, `history[1]` is the instance/user message
(issue "TimeDelta serialization precision") and `history[3]` is the
first post-action tool observation, verbatim:

```
[File: reproduce.py (1 lines total)]\r\n1:\n(Open file: /testbed/reproduce.py)\n(Current directory: /testbed)\nbash-$
```

That observation string is 112 characters. It does not include the
`OBSERVATION:` prefix from current `config/default.yaml`; the
demonstration predates or uses a different wrapping. Subsequent
history items continue to append after the issue. Observation length
is truncated at `max_observation_length` (default 100,000 characters
in `TemplateConfig`).

## T19 — OpenHands software-agent-sdk mid-loop assembly — C

**Source.** Parent project `All-Hands-AI/OpenHands`: 84,366 stars.
Public assembler on 2026-08-18 is `OpenHands/software-agent-sdk`
(1,004 stars; the `All-Hands-AI/OpenHands` tree is a
frontend/control-plane repo and no longer contains CodeActAgent prompt
assembly). HEAD
`98338ff37aea6627777b9978963ab727f51e4f40`.

- `prepare_llm_messages`:
  https://github.com/OpenHands/software-agent-sdk/blob/98338ff37aea6627777b9978963ab727f51e4f40/openhands-sdk/openhands/sdk/agent/utils.py
  (lines 568–631)
- `LLMConvertibleEvent.events_to_messages`:
  https://github.com/OpenHands/software-agent-sdk/blob/98338ff37aea6627777b9978963ab727f51e4f40/openhands-sdk/openhands/sdk/event/base.py
  (line 108)
- `ObservationEvent.to_llm_message`:
  https://github.com/OpenHands/software-agent-sdk/blob/98338ff37aea6627777b9978963ab727f51e4f40/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py
  (lines 66–72, `role="tool"`)
- `MessageEvent.to_llm_message`:
  https://github.com/OpenHands/software-agent-sdk/blob/98338ff37aea6627777b9978963ab727f51e4f40/openhands-sdk/openhands/sdk/event/llm_convertible/message.py

Accessed 2026-08-18.

**Verbatim template text.** There is no single static QA string. The
assembler is:

```python
def prepare_llm_messages(view, condenser=None, additional_messages=None, llm=None):
    llm_convertible_events = view.events
    # optional condenser may replace events
    messages = LLMConvertibleEvent.events_to_messages(llm_convertible_events)
    if additional_messages:
        messages.extend(additional_messages)
    return messages
```

`events_to_messages` walks events in order. Non-action events call
`event.to_llm_message()`. `ObservationEvent.to_llm_message` returns:

```python
return Message(
    role="tool",
    content=list(self.observation.to_llm_content) + list(self.extended_content),
    name=self.tool_name,
    tool_call_id=self.tool_call_id,
)
```

**Layout order.** `[system] [question] [tool-output]`
(user `MessageEvent` precedes later `ObservationEvent`s, which become
`role="tool"` messages).

**The trailing block, verbatim.** After the user's `MessageEvent`, every
later `ObservationEvent` / `UserRejectObservation` / `AgentErrorEvent`
is a tool message. No official dumped linearized mid-loop prompt
string was found in the inspected tree (see Could not verify).

**Rough size.** Not a single static character count. Each observation
is the tool result text plus optional `extended_content`.

**Notes.** Mid-loop re-prefill is the full converted history, so tool
outputs sit after the original user message. Condensation may drop or
rewrite earlier events before conversion.

## T20 — lm-evaluation-harness XQuAD English — D

**Source.**
https://github.com/EleutherAI/lm-evaluation-harness/blob/8a07e1110d060de48cfc7a9a7987b7659060b60b/lm_eval/tasks/xquad/xquad_en.yaml
Common include
https://github.com/EleutherAI/lm-evaluation-harness/blob/8a07e1110d060de48cfc7a9a7987b7659060b60b/lm_eval/tasks/xquad/xquad_common_yaml
(`doc_to_text: null` in the include; language YAML overrides it;
`generate_until: ["\n"]`). Repo
`EleutherAI/lm-evaluation-harness`: 13,691 stars, HEAD
`8a07e1110d060de48cfc7a9a7987b7659060b60b` on 2026-08-18. Accessed
2026-08-18.

**Verbatim template text.**

```
Context: {{context}}

Question: {{question}}

Answer:
```

**Layout order.** `[context] [question] [suffix]`

**The trailing block, verbatim.**

Exact string: `"\n\nAnswer:"`

**Rough size.** 9 characters.

**Notes.** Instruction words are English. XQuAD is a multilingual
extractive QA family on harness `main` (language YAMLs: ar, de, el,
en, es, hi, ro, ru, th, tr, vi, zh).

## T21 — lm-evaluation-harness XQuAD Arabic — D

**Source.**
https://github.com/EleutherAI/lm-evaluation-harness/blob/8a07e1110d060de48cfc7a9a7987b7659060b60b/lm_eval/tasks/xquad/xquad_ar.yaml
Same family and commit as T20. Accessed 2026-08-18.

**Verbatim template text.**

```
سيا: {{context}}

سؤال: {{question}}

إجابة:
```

**Layout order.** `[context] [question] [suffix]`

**The trailing block, verbatim.**

Exact string: `"\n\nإجابة:"`

**Rough size.** 8 characters.

**Notes.** Context/question/answer labels are Arabic. Sibling files on
the same commit include Thai
`บริบท: {{context}}\n\nคำถาม: {{question}}\n\nคำตอบ:` (trailing
`"\n\nคำตอบ:"`, 8 characters) and Spanish
`Contexto: {{context}}\n\nPregunta: {{question}}\n\nRespuesta:`
(trailing `"\n\nRespuesta:"`, 12 characters). Those siblings are not
separate locked records.

## T22 — Belebele official zero-shot + harness default — D

**Source.** Official zero-shot instructions (ACL 2024 benchmark repo):
https://github.com/facebookresearch/belebele/blob/918890beb2290a8d3ef2d7a90369925959e1bacf/sample_zero_shot_instructions.md
Few-shot English template also in
https://github.com/facebookresearch/belebele/blob/918890beb2290a8d3ef2d7a90369925959e1bacf/README.md
Harness default:
https://github.com/EleutherAI/lm-evaluation-harness/blob/8a07e1110d060de48cfc7a9a7987b7659060b60b/lm_eval/tasks/belebele/_default_template_yaml
`facebookresearch/belebele`: 341 stars; inclusion is the major-venue
benchmark bar, not the star bar. Harness stars as T20. Belebele HEAD
`918890beb2290a8d3ef2d7a90369925959e1bacf` on 2026-08-18. Accessed
2026-08-18.

**Verbatim template text.** Official zero-shot f-string from
`sample_zero_shot_instructions.md`:

```
{instruction}
###
Passage:
{passage}
###
Query:
{query}
###
Choices:
(A) {A}
(B) {B}
(C) {C}
(D) {D}
###
Answer:
```

The instruction used in the worked example on that page:

```
Given the following passage, query, and answer choices, output the letter corresponding to the correct answer.
```

README few-shot English template:

```
P: <passage> \n Q: <question> \n A: <mc answer 1> \n B: <mc answer 2> \n  C: <mc answer 3> \n  D: <mc answer 4> \n  Answer: <Correct answer letter>
```

Harness `_default_template_yaml`:

```
P: {{flores_passage}}
Q: {{question.strip()}}
A: {{mc_answer1}}
B: {{mc_answer2}}
C: {{mc_answer3}}
D: {{mc_answer4}}
Answer:
```

**Layout order.** Official zero-shot:
`[instruction] [context] [question] [examples] [suffix]`
(choices mapped to `[examples]`). Harness:
`[context] [question] [examples] [suffix]`.

**The trailing block, verbatim.** Official, after `{query}`:

```
###
Choices:
(A) {A}
(B) {B}
(C) {C}
(D) {D}
###
Answer:
```

Exact string:
`"\n###\nChoices:\n(A) {A}\n(B) {B}\n(C) {C}\n(D) {D}\n###\nAnswer:\n"`

Harness, after `{{question.strip()}}`:

Exact string:
`"\nA: {{mc_answer1}}\nB: {{mc_answer2}}\nC: {{mc_answer3}}\nD: {{mc_answer4}}\nAnswer:"`

**Rough size.** Official trailing block: 58 characters (placeholders
included, choice strings not instantiated). Harness trailing block: 80
characters (placeholders included). Instantiated length scales with
the four choice strings.

**Notes.** The official instruction in the paper's zero-shot writeup is
English and sits before the passage. The harness default has no
separate English instruction sentence; labels `P`/`Q`/`A`–`D`/`Answer`
are English. README also documents few-shot with English examples
regardless of target language.

---

## Could not verify

- **DSPy default RAG/QA template** (`stanfordnlp/dspy`, 37,362 stars,
  HEAD `aa9d2d0538ae67bb81d8fe56ed0daa9e9b57ac7b` on 2026-08-18).
  Meets the star bar. The framework compiles signatures rather than
  shipping one default retrieval-QA string. No single official default
  QA template was identified. Obstacle as allowed by the brief (no
  improvised stand-in).

- **Microsoft Semantic Kernel default RAG/QA template**
  (`microsoft/semantic-kernel`, 28,461 stars, HEAD
  `c028a0c7dc4f0814cdcbaba9d998f187a41197bf` on 2026-08-18). Meets the
  star bar. Prompt templates are plugin/handlebars user input. No
  single official default QA string was verified on this access date.

- **TyDiQA on EleutherAI/lm-evaluation-harness `main`.**
  `https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/8a07e1110d060de48cfc7a9a7987b7659060b60b/lm_eval/tasks/tydiqa/tydiqa.yaml`
  and `.../tydiqa/default.yaml` returned HTTP 404 on 2026-08-18. The
  closest multilingual extractive-QA family present on that commit is
  XQuAD (T20–T21). MLQA paths `lm_eval/tasks/mlqa/mlqa_en.yaml` and
  `lm_eval/tasks/mlqa/_mlqa.yaml` also 404.

- **Meta llama-cookbook / Meta Model API in-prompt schema-after-task
  example.** `meta-llama/llama-cookbook` HEAD
  `2f22a9eb030f92d0e99227e57e9a1123af1f9532` on 2026-08-18. No
  permalinked official notebook that concatenates a JSON schema after
  the user task was verified. Not recorded as a template.

- **LangChain fully rendered ReAct mid-loop prompt string.** Assembly
  and the official template are T17. A unit-test or fixture that dumps
  the fully formatted prompt after one or more observations was not
  retrieved. No invented observation text is used for a character
  count beyond the static suffix.

- **OpenHands official rendered mid-loop prompt.** Assembly is T19. No
  dumped linearized history from an official test fixture or trace was
  retrieved from `software-agent-sdk` on this access date, so no
  observation character count is claimed.

- **LangSmith HTML prompt pages.**
  `https://smith.langchain.com/hub/langchain-ai/retrieval-qa-chat` did
  not return the prompt body. The body used in T03 is from the commits
  API. Hub prompt `rlm/rag-prompt` was not included: it is not the
  named official default of `create_retrieval_chain`.

---

## Deployment-status re-check (windowed observation evictors)

Accessed 2026-08-18. Claims below are permalinked. This is a status
re-check, not a measurement.

**TensorRT-LLM.** RocketKV remains opt-in. On commit
`aede3825b7c4289575c6805614cc2fc4f4777c04`:

- `sparse_attention_config` on the LLM args object defaults to `None`:
  https://github.com/NVIDIA/TensorRT-LLM/blob/aede3825b7c4289575c6805614cc2fc4f4777c04/tensorrt_llm/llmapi/llm_args.py
  (lines 4607–4610: `sparse_attention_config: Optional[SparseAttentionConfig] = Field(default=None, ...)`).
- Enabling RocketKV requires constructing `RocketSparseAttentionConfig`
  (`algorithm` default `"rocket"`). `window_size` on that class
  defaults to 32:
  same file, `class RocketSparseAttentionConfig`,
  `window_size: Optional[int] = Field(default=32, description="The window size for RocketKV.")`.
- Feature docs:
  https://github.com/NVIDIA/TensorRT-LLM/blob/aede3825b7c4289575c6805614cc2fc4f4777c04/docs/source/features/sparse-attention.md
  (sparse attention is enabled by passing a `sparse_attention_config`;
  algorithms listed are `rocket`, `dsa`, `skip_softmax`).
- Usage:
  https://github.com/NVIDIA/TensorRT-LLM/blob/aede3825b7c4289575c6805614cc2fc4f4777c04/examples/sparse_attention/RocketKV.md
  ("To enable RocketKV, configure `RocketSparseAttentionConfig` and
  pass it to the `LLM` class constructor").
- Repo `NVIDIA/TensorRT-LLM`: 14,402 stars.

**vLLM.** Docs accessed 2026-08-18:
https://docs.vllm.ai/en/latest/design/attention_backends/
(page stamped August 18, 2026). Default backend selection is dense:
Blackwell priority FLASHINFER then FLASH_ATTN; Ampere/Hopper FLASH_ATTN
then FLASHINFER. Listed sparse backends are MiniMax M3 lightning-indexer
sparse and DeepSeek-style MLA sparse (`FLASHMLA_SPARSE`,
`FLASHINFER_MLA_SPARSE`, DeepSeek V4 sparse). No SnapKV-style
observation-window evictor is listed. Repo `vllm-project/vllm`: 89,322
stars.

**SGLang.** Issue #32657, opened 2026-07-28, still Open on 2026-08-18:
https://github.com/sgl-project/sglang/issues/32657
The RFC states the proposed unified post-hoc KV-sparsity framework
"should be default-off and should not change dense inference when no
sparse policy is configured." Explicit non-goals include physical
eviction and attention-history/observation-window policies, and name
H2O, SnapKV, and PyramidKV as outside the initial implementation.
`create_sparse_coordinator()` is described as having no serving caller
on `main`. Repo `sgl-project/sglang`: 31,998 stars, HEAD
`0111b290312aa224962397db86c04fe112539fb2` on 2026-08-18.

No additional widely used serving stack was found on this access date
that ships a SnapKV-style observation-window constant as a default-on
path.
