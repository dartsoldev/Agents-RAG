"""Call OpenAI with typed outputs, bounded context and storage disabled."""

from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel

from backend.config import settings

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


class Citation(BaseModel):
    chunk_id: str
    quote: str


class Answer(BaseModel):
    answer: str
    insufficient: bool
    citations: list[Citation]


class Verification(BaseModel):
    supported: bool
    reason: str


def client():
    return OpenAI(api_key=settings.openai_api_key, timeout=60, max_retries=2)


def structured(prompt_name, content, output_type):
    response = client().responses.parse(
        model=settings.openai_model,
        store=False,
        input=[
            {
                "role": "system",
                "content": (PROMPTS / prompt_name).read_text(encoding="utf-8"),
            },
            {"role": "user", "content": content},
        ],
        text_format=output_type,
        max_output_tokens=3500,
    )
    if response.output_parsed is None:
        raise ValueError("AI did not return a valid structured answer; attorney review required")
    return response.output_parsed


def embed(texts):
    response = client().embeddings.create(model=settings.openai_embedding_model, input=texts)
    return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
