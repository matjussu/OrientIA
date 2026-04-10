import json
from pathlib import Path
from abc import ABC, abstractmethod
from mistralai.client import Mistral
from src.prompt.system import SYSTEM_PROMPT
from src.rag.pipeline import OrientIAPipeline


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
    """Ablation baseline: same Mistral model, same system prompt, NO RAG context.

    This isolates the effect of retrieval+reranking. If OurRagSystem scores
    higher than MistralRawSystem, the delta is attributable to the RAG
    pipeline (data + retrieval + reranking), not the model or the prompt.
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
                {"role": "system", "content": SYSTEM_PROMPT},
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
    """
    name = "chatgpt_recorded"

    def __init__(self, path: str | Path):
        self.data = json.loads(Path(path).read_text(encoding="utf-8"))

    def answer(self, qid: str, question: str) -> str:
        if qid not in self.data or qid == "_metadata":
            raise KeyError(f"No recorded ChatGPT response for {qid}")
        return self.data[qid]
