import json
from pathlib import Path
from abc import ABC, abstractmethod
from mistralai.client import Mistral
from src.rag.pipeline import OrientIAPipeline


# A minimal neutral prompt for the mistral_raw baseline.
#
# Rationale (Phase E.1 asymmetry fix):
# Until Run 9 the baseline shared the optimized SYSTEM_PROMPT (src/prompt/
# system.py v3.1) with our_rag. That prompt carries our custom rules
# (anti-confession, forced Plan A/B/C, distinct cities, interdisciplinary
# bypass, fact-check markers, comparison tables), all of which were
# designed to maximise our_rag's performance under the rubric. Giving
# the same rules to mistral_raw cripples its free generation mode and
# inflates our advantage artificially — effectively training on the test.
#
# For a fair baseline we give mistral_raw the kind of prompt a generic
# orientation chatbot would ship with: it describes the task and asks
# for precise, useful answers, but imposes no custom rules that
# happen to align with our evaluation rubric.
NEUTRAL_MISTRAL_PROMPT = """Tu es un conseiller d'orientation pour les lycéens et étudiants en France.

Réponds aux questions des étudiants de façon claire et détaillée, en
t'appuyant sur tes connaissances du système éducatif français
(Parcoursup, licences, masters, grandes écoles, BTS, BUT, écoles
d'ingénieurs, formations professionnelles, etc.).

Quand tu proposes des formations ou des métiers, donne des informations
utiles pour décider : noms précis d'établissements, villes, types de
diplômes, niveaux d'accès, débouchés. Garde un ton bienveillant et
professionnel.
"""


class System(ABC):
    name: str

    @abstractmethod
    def answer(self, qid: str, question: str) -> str:
        ...


class OurRagSystem(System):
    """Our specialized RAG system — the subject of the INRIA thesis."""
    name = "our_rag"

    def __init__(self, pipeline: OrientIAPipeline):
        self.pipeline = pipeline

    def answer(self, qid: str, question: str) -> str:
        text, _sources = self.pipeline.answer(question)
        return text


class MistralRawSystem(System):
    """Fair baseline: same Mistral model, **neutral** generic-assistant prompt,
    NO RAG context.

    This isolates the effect of the full our_rag stack (optimized prompt +
    retrieval + reranking). If OurRagSystem scores higher than
    MistralRawSystem, the delta is attributable to our optimizations, not
    to mistral_raw being handicapped by a prompt it wasn't supposed to
    optimize for.
    """
    name = "mistral_raw"

    def __init__(self, client: Mistral, model: str = "mistral-medium-latest"):
        self.client = client
        self.model = model

    def answer(self, qid: str, question: str) -> str:
        response = self.client.chat.complete(
            model=self.model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": NEUTRAL_MISTRAL_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content


class ChatGPTRecordedSystem(System):
    """Pre-recorded ChatGPT responses loaded from a JSON file.

    The file must have a `_metadata` key (ignored by answer()) and one
    key per question id (e.g., 'A1', 'B3', 'H2'). The user manually
    records the 32 responses by pasting each question into chat.openai.com
    and copying the reply.

    DEPRECATED in Phase F.2: replaced by OpenAIBaseline which calls the
    GPT-4o API directly for fair, reproducible comparison. Kept for
    backward compatibility with Run 6-10 archives.
    """
    name = "chatgpt_recorded"

    def __init__(self, path: str | Path):
        self.data = json.loads(Path(path).read_text(encoding="utf-8"))

    def answer(self, qid: str, question: str) -> str:
        if qid not in self.data or qid == "_metadata":
            raise KeyError(f"No recorded ChatGPT response for {qid}")
        return self.data[qid]


# --- Phase F.2 — 7-system baseline matrix ---
#
# To make the comparison scientifically defensible (Phase E showed Run 10's
# +5.31 gap was partly an artifact of the shared optimized prompt giving
# mistral_raw an unfair handicap), Phase F builds a 7-system grid:
#
#   1. our_rag                  : v3.2 prompt + RAG (the full stack)
#   2. mistral_neutral          : NEUTRAL prompt, no RAG (baseline)
#   3. mistral_v3_2_no_rag      : v3.2 prompt, no RAG (isolates RAG)
#   4. gpt4o_neutral            : NEUTRAL prompt, no RAG (cross-vendor baseline)
#   5. gpt4o_v3_2_no_rag        : v3.2 prompt, no RAG (cross-vendor + our prompt)
#   6. claude_neutral           : NEUTRAL prompt, no RAG (cross-vendor baseline)
#   7. claude_v3_2_no_rag       : v3.2 prompt, no RAG (cross-vendor + our prompt)
#
# System 3 vs system 1 isolates the RAG contribution.
# Systems 5 and 7 vs 4 and 6 measure the prompt's portability across vendors.

class MistralWithCustomPromptSystem(System):
    """Same as MistralRawSystem but takes the system prompt as a
    constructor argument, so the same wrapper can serve both
    `mistral_neutral` (NEUTRAL prompt) and `mistral_v3_2_no_rag`
    (our optimized v3.2 prompt without RAG context)."""

    def __init__(
        self,
        client: Mistral,
        system_prompt: str,
        name: str,
        model: str = "mistral-medium-latest",
    ):
        self.client = client
        self.system_prompt = system_prompt
        self.model = model
        self.name = name

    def answer(self, qid: str, question: str) -> str:
        response = self.client.chat.complete(
            model=self.model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content


class OpenAIBaseline(System):
    """OpenAI GPT-4o baseline. Wraps the openai.OpenAI client.

    The OpenAI client lives in src.eval.openai_client.make_openai_client
    so that this module stays import-safe even when the openai package
    isn't installed (lazy import via the constructor injection pattern).
    """

    def __init__(
        self,
        client,
        model: str,
        system_prompt: str,
        name: str,
    ):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.name = name

    def answer(self, qid: str, question: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content


class ClaudeBaseline(System):
    """Anthropic Claude baseline. Wraps anthropic.Anthropic client.

    Note: Claude treats the system prompt as a top-level argument
    (not a message), so the API shape differs slightly from
    Mistral/OpenAI. Output: response.content[0].text.
    """

    def __init__(
        self,
        client,
        model: str,
        system_prompt: str,
        name: str,
        max_tokens: int = 4000,
    ):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.name = name
        self.max_tokens = max_tokens

    def answer(self, qid: str, question: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": question}],
        )
        return response.content[0].text
