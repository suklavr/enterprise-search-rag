"""Configuration from the environment / `.env`. Mode selection is per component: the embedder and generator use OpenAI
when `OPENAI_API_KEY` is set; the store uses Pinecone when BOTH keys are set (`RAG_MODE=pinecone` forces it, `local`
forbids it). Keys are `SecretStr`, so a logged `Settings` shows `**********`; `describe()` reports only presence."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: SecretStr | None = None
    pinecone_api_key: SecretStr | None = None
    pinecone_index: str = "enterprise-search"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_namespace: str = "demo"
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536
    chat_model: str = "gpt-4o-mini"
    docs_api_token: SecretStr | None = None          # only the optional docs.cybcube.com crawler uses this
    rag_mode: Literal["auto", "local", "pinecone"] = "auto"
    corpus_dir: Path = Path("corpus")
    index_dir: Path = Path("data/index")
    eval_path: Path = Path("eval/queries.jsonl")
    static_dir: Path = Path("static")
    chunk_words: int = 350
    chunk_overlap: int = 60
    default_alpha: float = 0.5
    default_top_k: int = 5

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value())

    @property
    def pinecone_key_present(self) -> bool:
        return bool(self.pinecone_api_key and self.pinecone_api_key.get_secret_value())

    @property
    def store_mode(self) -> Literal["local", "pinecone"]:
        """auto = Pinecone only when BOTH keys are set: a Pinecone index built from hash embeddings would be junk, and
        the index dimension is fixed at creation."""
        if self.rag_mode == "local":
            return "local"
        if self.rag_mode == "pinecone":
            return "pinecone"
        return "pinecone" if (self.pinecone_key_present and self.openai_enabled) else "local"

    def openai_key(self) -> str:
        return self.openai_api_key.get_secret_value() if self.openai_api_key else ""

    def pinecone_key(self) -> str:
        return self.pinecone_api_key.get_secret_value() if self.pinecone_api_key else ""

    def describe(self) -> dict:
        """Safe to print: names and booleans only, never values."""
        return {"store": self.store_mode, "embedder": self.embed_model if self.openai_enabled else "hash (local, lexical)",
                "generator": self.chat_model if self.openai_enabled else "extractive (local)",
                "openai_key": self.openai_enabled, "pinecone_key": self.pinecone_key_present, "index": self.pinecone_index}
