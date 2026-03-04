from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import json
import logging
import math
import re

from .spec_service import SpecService


@dataclass(frozen=True)
class IndexStatus:
    ready: bool
    stale: bool
    reason: str
    architecture_id: str
    index_path: str
    indexed_files: int
    indexed_chunks: int
    index_created_at: str | None


@dataclass(frozen=True)
class IndexBuildResult:
    ok: bool
    architecture_id: str
    index_path: str
    files_indexed: int
    chunks_indexed: int
    model_name: str
    created_at: str


class RAGIndexService:
    def __init__(
        self,
        spec_service: SpecService,
        specs_dir: Path,
        var_dir: Path,
        embedding_model: str,
    ) -> None:
        self.spec_service = spec_service
        self.specs_dir = specs_dir
        self.var_dir = var_dir
        self.embedding_model_name = embedding_model
        self.models_dir = self.var_dir / "models"
        self.index_root = self.var_dir / "index"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.index_root.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("uvicorn.error")

        self._embedder = None

    def status(self, architecture_id: str) -> IndexStatus:
        arch_key = "" if architecture_id == "_root" else architecture_id
        display_arch = architecture_id or "_root"
        index_payload = self._load_index_payload(architecture_id)
        index_path = self._index_path(architecture_id)

        if index_payload is None:
            return IndexStatus(
                ready=False,
                stale=True,
                reason="Index is missing",
                architecture_id=display_arch,
                index_path=str(index_path),
                indexed_files=0,
                indexed_chunks=0,
                index_created_at=None,
            )

        expected_model = index_payload.get("model_name")
        if expected_model != self.embedding_model_name:
            return IndexStatus(
                ready=True,
                stale=True,
                reason="Index model differs from current embedding model",
                architecture_id=display_arch,
                index_path=str(index_path),
                indexed_files=len(index_payload.get("files", [])),
                indexed_chunks=len(index_payload.get("chunks", [])),
                index_created_at=index_payload.get("created_at"),
            )

        try:
            arch_path = self.spec_service.get_arch_path(arch_key)
        except (FileNotFoundError, ValueError):
            return IndexStatus(
                ready=False,
                stale=True,
                reason="Architecture path is not available",
                architecture_id=display_arch,
                index_path=str(index_path),
                indexed_files=len(index_payload.get("files", [])),
                indexed_chunks=len(index_payload.get("chunks", [])),
                index_created_at=index_payload.get("created_at"),
            )

        current_files = self._collect_yaml_file_stats(arch_path)
        indexed_files = {item["path"]: item for item in index_payload.get("files", [])}

        if set(current_files.keys()) != set(indexed_files.keys()):
            return IndexStatus(
                ready=True,
                stale=True,
                reason="YAML file set changed",
                architecture_id=display_arch,
                index_path=str(index_path),
                indexed_files=len(index_payload.get("files", [])),
                indexed_chunks=len(index_payload.get("chunks", [])),
                index_created_at=index_payload.get("created_at"),
            )

        for rel_path, current in current_files.items():
            indexed = indexed_files.get(rel_path)
            if not indexed:
                continue
            if float(current["mtime"]) > float(indexed.get("mtime", 0.0)):
                return IndexStatus(
                    ready=True,
                    stale=True,
                    reason=f"File changed since indexing: {rel_path}",
                    architecture_id=display_arch,
                    index_path=str(index_path),
                    indexed_files=len(index_payload.get("files", [])),
                    indexed_chunks=len(index_payload.get("chunks", [])),
                    index_created_at=index_payload.get("created_at"),
                )
            if int(current["size"]) != int(indexed.get("size", -1)):
                return IndexStatus(
                    ready=True,
                    stale=True,
                    reason=f"File size changed since indexing: {rel_path}",
                    architecture_id=display_arch,
                    index_path=str(index_path),
                    indexed_files=len(index_payload.get("files", [])),
                    indexed_chunks=len(index_payload.get("chunks", [])),
                    index_created_at=index_payload.get("created_at"),
                )

        return IndexStatus(
            ready=True,
            stale=False,
            reason="Index is up to date",
            architecture_id=display_arch,
            index_path=str(index_path),
            indexed_files=len(index_payload.get("files", [])),
            indexed_chunks=len(index_payload.get("chunks", [])),
            index_created_at=index_payload.get("created_at"),
        )

    def build_index(self, architecture_id: str) -> IndexBuildResult:
        arch_key = "" if architecture_id == "_root" else architecture_id
        display_arch = architecture_id or "_root"
        arch_path = self.spec_service.get_arch_path(arch_key)
        file_stats = self._collect_yaml_file_stats(arch_path)

        chunks: List[Dict[str, Any]] = []
        for rel_path in sorted(file_stats.keys()):
            file_path = arch_path / rel_path
            try:
                text = file_path.read_text(encoding="utf-8")
            except OSError:
                continue
            for chunk in self._extract_yaml_chunks(text):
                chunks.append(
                    {
                        "source": rel_path,
                        "line": chunk["line"],
                        "text": chunk["text"],
                    }
                )

        if not chunks:
            payload = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "architecture_id": display_arch,
                "model_name": self.embedding_model_name,
                "files": list(file_stats.values()),
                "chunks": [],
            }
            self._save_index_payload(architecture_id, payload)
            return IndexBuildResult(
                ok=True,
                architecture_id=display_arch,
                index_path=str(self._index_path(architecture_id)),
                files_indexed=len(file_stats),
                chunks_indexed=0,
                model_name=self.embedding_model_name,
                created_at=payload["created_at"],
            )

        texts = [f"passage: {chunk['text']}" for chunk in chunks]
        vectors = self._encode_texts(texts)
        for chunk, vector in zip(chunks, vectors):
            chunk["embedding"] = vector

        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "architecture_id": display_arch,
            "model_name": self.embedding_model_name,
            "files": list(file_stats.values()),
            "chunks": chunks,
        }
        self._save_index_payload(architecture_id, payload)

        self.logger.info(
            "Built RAG index: architecture=%s files=%d chunks=%d model=%s path=%s",
            display_arch,
            len(file_stats),
            len(chunks),
            self.embedding_model_name,
            self._index_path(architecture_id),
        )

        return IndexBuildResult(
            ok=True,
            architecture_id=display_arch,
            index_path=str(self._index_path(architecture_id)),
            files_indexed=len(file_stats),
            chunks_indexed=len(chunks),
            model_name=self.embedding_model_name,
            created_at=payload["created_at"],
        )

    def retrieve(self, architecture_id: str, queries: List[str], top_k: int = 6) -> List[Dict[str, str]]:
        payload = self._load_index_payload(architecture_id)
        if payload is None:
            return []

        chunks = payload.get("chunks") or []
        if not chunks:
            return []

        joined_query = " ".join(item.strip() for item in queries if item.strip())
        if not joined_query:
            return []

        query_vector = self._encode_texts([f"query: {joined_query}"])[0]
        query_tokens = self._tokens(joined_query)

        scored: List[tuple[float, Dict[str, str]]] = []
        for chunk in chunks:
            embedding = chunk.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                continue
            semantic_score = self._cosine_similarity(query_vector, embedding)
            lexical_score = self._lexical_score(chunk.get("text", ""), query_tokens)
            combined = 0.8 * semantic_score + 0.2 * lexical_score

            source_stem = Path(str(chunk.get("source", ""))).stem.lower()
            if source_stem and source_stem in query_tokens:
                combined += 0.08

            if self._looks_like_link_dump(str(chunk.get("text", ""))):
                combined -= 0.12

            if combined <= 0:
                continue

            scored.append(
                (
                    combined,
                    {
                        "source": str(chunk.get("source", "")),
                        "line": str(chunk.get("line", "?")),
                        "snippet": str(chunk.get("text", "")),
                    },
                )
            )

        if not scored:
            return []

        scored.sort(key=lambda item: item[0], reverse=True)

        source_counts: Dict[str, int] = {}
        per_source_limit = 2
        selected: List[Dict[str, str]] = []
        for _, snippet in scored:
            source = snippet["source"]
            count = source_counts.get(source, 0)
            if count >= per_source_limit:
                continue
            source_counts[source] = count + 1
            selected.append(snippet)
            if len(selected) >= top_k:
                break

        return selected

    def _index_path(self, architecture_id: str) -> Path:
        name = architecture_id if architecture_id and architecture_id != "_root" else "_root"
        return self.index_root / name / "index.json"

    def _save_index_payload(self, architecture_id: str, payload: Dict[str, Any]) -> None:
        index_path = self._index_path(architecture_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = index_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(index_path)

    def _load_index_payload(self, architecture_id: str) -> Dict[str, Any] | None:
        index_path = self._index_path(architecture_id)
        if not index_path.exists():
            return None
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        return data

    def _collect_yaml_file_stats(self, arch_path: Path) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for file_path in sorted(arch_path.glob("*.yaml")):
            try:
                stat = file_path.stat()
            except OSError:
                continue
            rel_path = file_path.name
            result[rel_path] = {
                "path": rel_path,
                "mtime": float(stat.st_mtime),
                "size": int(stat.st_size),
            }
        return result

    def _extract_yaml_chunks(self, text: str, max_chunk_chars: int = 1000) -> List[Dict[str, Any]]:
        lines = text.splitlines()
        chunks: List[Dict[str, Any]] = []
        n = len(lines)
        i = 0

        while i < n:
            line = lines[i]
            if re.match(r"^\s*-\s+", line):
                indent = len(line) - len(line.lstrip(" "))
                start = i
                i += 1
                while i < n:
                    current = lines[i]
                    if re.match(r"^\s*-\s+", current):
                        current_indent = len(current) - len(current.lstrip(" "))
                        if current_indent == indent:
                            break
                    i += 1
                block = "\n".join(lines[start:i]).strip()
                if block:
                    chunks.append({"line": start + 1, "text": block[:max_chunk_chars]})
                continue
            i += 1

        if not chunks:
            window = 12
            step = 6
            for start in range(0, n, step):
                block = "\n".join(lines[start : start + window]).strip()
                if block:
                    chunks.append({"line": start + 1, "text": block[:max_chunk_chars]})
                if len(chunks) >= 20:
                    break

        return chunks

    def _encode_texts(self, texts: List[str]) -> List[List[float]]:
        embedder = self._get_embedder()
        vectors = embedder.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return [vector.tolist() for vector in vectors]

    def _get_embedder(self):
        if self._embedder is not None:
            return self._embedder

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Install dependencies before building the index."
            ) from exc

        self.logger.info(
            "Loading embedding model '%s' (cache_dir=%s)",
            self.embedding_model_name,
            self.models_dir,
        )
        try:
            self._embedder = SentenceTransformer(
                self.embedding_model_name,
                cache_folder=str(self.models_dir),
                device="cpu",
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load embedding model '{self.embedding_model_name}': {exc}") from exc

        return self._embedder

    def _tokens(self, text: str) -> List[str]:
        raw = re.findall(r"[a-zA-Z0-9_\-]{3,}", text.lower())
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "into", "about", "please", "user", "chat", "help",
            "architecture", "editor", "panel", "request", "assistant",
        }
        return [token for token in raw if token not in stop_words][:60]

    def _lexical_score(self, text: str, query_tokens: List[str]) -> float:
        lowered = text.lower()
        if not lowered or not query_tokens:
            return 0.0
        hits = sum(1 for token in query_tokens if token in lowered)
        return hits / max(1, len(query_tokens))

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _looks_like_link_dump(self, chunk_text: str) -> bool:
        lines = [line.strip() for line in chunk_text.splitlines() if line.strip()]
        if not lines:
            return False
        url_lines = sum(1 for line in lines if "http://" in line or "https://" in line)
        return (url_lines / len(lines)) >= 0.7
