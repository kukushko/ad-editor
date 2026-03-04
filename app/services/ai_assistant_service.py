"""AI assistant orchestration layer.

This service executes a multi-step protocol around the LLM instead of sending
user text directly as a single prompt:
1. Planner: decompose user intent into subtasks and retrieval queries.
2. Retrieval: fetch context snippets from the local embedding index.
3. Worker(s): solve each subtask with retrieved context.
4. Synthesis: merge worker outputs into the final answer.

The module also emits readable server-side protocol logs that can be colored.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import json
import logging
import urllib.error
import urllib.request

from .rag_index_service import RAGIndexService


PLANNER_PROMPT = (
    "You are an orchestration planner for an architecture editor assistant. "
    "Given user request and recent chat history, produce JSON with fields: "
    "summary (string), subtasks (array of concise strings), retrieval_queries (array of strings). "
    "Keep 1-4 subtasks, no markdown, valid JSON only."
)

WORKER_PROMPT = (
    "You are an architecture domain assistant. "
    "Answer only the subtask using provided context snippets. "
    "If context is insufficient, explicitly say what is missing. "
    "Keep answer concise and factual."
)

SYNTHESIS_PROMPT = (
    "You are an AI assistant in an architecture data editor. "
    "Produce a helpful final answer for the user using worker outputs. "
    "Be actionable. Mention assumptions briefly."
)


@dataclass(frozen=True)
class AIProtocolResult:
    """Final assistant output plus lightweight protocol summary."""

    answer: str
    protocol_steps: List[str]


class AIAssistantService:
    """Coordinates planning, retrieval and synthesis over an OpenAI-compatible API.

    Design goals:
    - keep backend control over tool-like steps (planning/RAG/synthesis),
    - provide high observability via server logs,
    - fail with explicit runtime errors when LLM responses are malformed.
    """

    def __init__(
        self,
        rag_index_service: RAGIndexService,
        openai_base_url: str,
        openai_model: str,
        openai_api_key: str,
        rag_top_k: int = 6,
        reasoning_log_enabled: bool = True,
        reasoning_log_max_chars: int = 2400,
        reasoning_log_colors: bool = True,
    ) -> None:
        """Initialize assistant service.

        Args:
            rag_index_service: Retrieval service backed by local embedding index.
            openai_base_url: OpenAI-compatible API base URL.
            openai_model: Chat model name/path sent to /chat/completions.
            openai_api_key: Bearer key for upstream LLM endpoint.
            rag_top_k: Max snippets per request.
            reasoning_log_enabled: Enable detailed protocol logs.
            reasoning_log_max_chars: Max chars per logged field value.
            reasoning_log_colors: Enable ANSI colors in server console logs.
        """
        self.rag_index_service = rag_index_service
        self.openai_base_url = openai_base_url.rstrip("/")
        self.openai_model = openai_model
        self.openai_api_key = openai_api_key
        self.rag_top_k = max(1, rag_top_k)
        self.reasoning_log_enabled = reasoning_log_enabled
        self.reasoning_log_max_chars = max(600, reasoning_log_max_chars)
        self.reasoning_log_colors = reasoning_log_colors

        # Route protocol logs to uvicorn logger so everything appears in server output.
        self.logger = logging.getLogger("uvicorn.error")
        self.logger.setLevel(logging.INFO)

    def chat(self, architecture_id: str, messages: List[Dict[str, str]]) -> AIProtocolResult:
        """Execute the full assistant protocol for one chat turn.

        Args:
            architecture_id: Selected architecture key from UI.
            messages: Prior chat history + latest user message.

        Returns:
            Structured assistant answer and protocol step summary.
        """
        user_message = self._get_last_user_message(messages)
        history_text = self._history_text(messages)
        self._log_section(
            "AI Chat Started",
            {
                "architecture": architecture_id or "_root",
                "history_messages": len(messages),
                "latest_user_message": user_message,
            },
        )

        planner_raw = self._llm_chat(
            system_prompt=PLANNER_PROMPT,
            user_prompt=(
                f"Architecture: {architecture_id or '_root'}\n"
                f"Chat history:\n{history_text}\n\n"
                f"Latest user request:\n{user_message}"
            ),
            temperature=0.1,
            phase="planner",
        )
        plan = self._parse_plan(planner_raw, user_message)
        self._log_section(
            "Planner Output",
            {
                "summary": plan["summary"],
                "subtasks": "\n".join(f"- {item}" for item in plan["subtasks"]),
                "retrieval_queries": "\n".join(f"- {item}" for item in plan["retrieval_queries"]) or "- (none)",
            },
        )

        queries = plan["retrieval_queries"] or plan["subtasks"] or [user_message]
        status = self.rag_index_service.status(architecture_id)
        snippets = self.rag_index_service.retrieve(architecture_id, queries, top_k=self.rag_top_k)
        self._log_section(
            "RAG Retrieval",
            {
                "index_ready": str(status.ready),
                "index_stale": str(status.stale),
                "index_reason": status.reason,
                "query_count": str(len(queries)),
                "snippet_count": str(len(snippets)),
                "sources": "\n".join(f"- {snippet['source']}" for snippet in snippets) or "- (none)",
            },
        )

        worker_outputs: List[str] = []
        for idx, subtask in enumerate(plan["subtasks"], start=1):
            worker_output = self._llm_chat(
                system_prompt=WORKER_PROMPT,
                user_prompt=(
                    f"Subtask {idx}: {subtask}\n\n"
                    f"Context snippets:\n{self._format_snippets(snippets)}\n\n"
                    f"Original user request:\n{user_message}"
                ),
                temperature=0.2,
                phase=f"worker-{idx}",
            )
            worker_outputs.append(f"Subtask {idx}: {subtask}\nResult: {worker_output}")

        final_answer = self._llm_chat(
            system_prompt=SYNTHESIS_PROMPT,
            user_prompt=(
                f"User request:\n{user_message}\n\n"
                f"Plan summary: {plan['summary']}\n\n"
                f"Worker outputs:\n{chr(10).join(worker_outputs)}"
            ),
            temperature=0.3,
            phase="synthesis",
        )

        steps = [
            f"plan: {plan['summary']}",
            f"subtasks: {len(plan['subtasks'])}",
            f"retrieval snippets: {len(snippets)}",
            "synthesis: completed",
        ]
        self._log_section(
            "AI Chat Finished",
            {
                "protocol_steps": " | ".join(steps),
                "final_answer_preview": final_answer,
            },
        )

        return AIProtocolResult(answer=final_answer.strip(), protocol_steps=steps)

    def _llm_chat(self, system_prompt: str, user_prompt: str, temperature: float, phase: str) -> str:
        """Call upstream OpenAI-compatible chat endpoint.

        This method validates basic response shape and returns assistant text.

        Args:
            system_prompt: System role prompt.
            user_prompt: User role prompt.
            temperature: Sampling temperature.
            phase: Protocol phase label used in logs.

        Raises:
            RuntimeError: For transport errors or malformed response payload.
        """
        payload = {
            "model": self.openai_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        self._log_section(
            f"LLM Request [{phase}]",
            {
                "url": f"{self.openai_base_url}/chat/completions",
                "model": self.openai_model,
                "temperature": str(temperature),
                "auth": self._mask_api_key(self.openai_api_key),
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            },
        )

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.openai_base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            self._log_section(f"LLM Error [{phase}]", {"error": f"HTTP {exc.code}", "details": details})
            raise RuntimeError(f"LLM HTTP error {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            self._log_section(f"LLM Error [{phase}]", {"error": f"Connection error: {exc.reason}"})
            raise RuntimeError(f"LLM connection error: {exc.reason}") from exc

        choices = body.get("choices") or []
        if not choices:
            self._log_section(f"LLM Error [{phase}]", {"error": "LLM response did not include choices"})
            raise RuntimeError("LLM response did not include choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            self._log_section(f"LLM Error [{phase}]", {"error": "LLM response content is empty"})
            raise RuntimeError("LLM response content is empty")

        self._log_section(
            f"LLM Response [{phase}]",
            {
                "choices": str(len(choices)),
                "assistant_content": content,
            },
        )
        return content

    def _parse_plan(self, planner_raw: str, fallback_user_message: str) -> Dict[str, Any]:
        """Parse planner output JSON with robust fallback.

        Planner is asked to return JSON, but model output may include markdown
        fences or malformed JSON. This method normalizes and provides safe fallback.
        """
        cleaned = planner_raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "summary": "single-step fallback planning",
                "subtasks": [fallback_user_message],
                "retrieval_queries": [fallback_user_message],
            }

        summary = payload.get("summary")
        subtasks = payload.get("subtasks")
        queries = payload.get("retrieval_queries")

        norm_subtasks = [str(x).strip() for x in (subtasks or []) if str(x).strip()][:4]
        if not norm_subtasks:
            norm_subtasks = [fallback_user_message]

        norm_queries = [str(x).strip() for x in (queries or []) if str(x).strip()][:6]

        return {
            "summary": str(summary or "planned decomposition").strip(),
            "subtasks": norm_subtasks,
            "retrieval_queries": norm_queries,
        }

    def _format_snippets(self, snippets: List[Dict[str, str]]) -> str:
        """Format retrieval snippets as compact plain text for worker prompts."""
        if not snippets:
            return "No relevant local snippets found."
        return "\n\n".join(
            f"[{idx}] source={snippet['source']} line={snippet.get('line', '?')}\n{snippet['snippet']}"
            for idx, snippet in enumerate(snippets, start=1)
        )

    def _get_last_user_message(self, messages: List[Dict[str, str]]) -> str:
        """Return the latest non-empty user message from history."""
        for message in reversed(messages):
            if message.get("role") == "user" and str(message.get("content", "")).strip():
                return str(message["content"])
        raise RuntimeError("No user message found in request")

    def _history_text(self, messages: List[Dict[str, str]], limit: int = 8) -> str:
        """Convert recent messages into readable text block for planner prompt."""
        recent = messages[-limit:]
        parts: List[str] = []
        for message in recent:
            role = str(message.get("role", "unknown"))
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            parts.append(f"{role}: {content}")
        return "\n".join(parts)

    def _log_section(self, title: str, fields: Dict[str, str]) -> None:
        """Emit one human-friendly protocol section into server logs."""
        if not self.reasoning_log_enabled:
            return
        title_kind = self._title_kind(title)
        painted_title = self._paint(f"===== {title} =====", title_kind)
        lines = [painted_title]
        for key, value in fields.items():
            safe_value = self._truncate_for_log(value)
            lines.append(self._paint(f"{key}:", "key"))
            lines.append(safe_value)
        lines.append(self._paint("=" * (len(title) + 12), title_kind))
        self.logger.info("\n".join(lines))

    def _truncate_for_log(self, value: Any) -> str:
        """Trim long log values to keep server logs readable."""
        text = str(value).strip()
        if len(text) <= self.reasoning_log_max_chars:
            return text
        cut = text[: self.reasoning_log_max_chars]
        return f"{cut}\n... [truncated {len(text) - self.reasoning_log_max_chars} chars]"

    def _mask_api_key(self, key: str) -> str:
        """Return masked API key preview safe for logs."""
        if not key:
            return "(empty)"
        if len(key) <= 6:
            return "*" * len(key)
        return f"{key[:3]}***{key[-3:]}"

    def _title_kind(self, title: str) -> str:
        """Map section title to log color style kind."""
        lowered = title.lower()
        if "llm request" in lowered:
            return "request"
        if "llm response" in lowered:
            return "response"
        if "error" in lowered:
            return "error"
        if "planner" in lowered:
            return "planner"
        if "rag retrieval" in lowered:
            return "retrieval"
        if "finished" in lowered:
            return "done"
        return "section"

    def _paint(self, text: str, kind: str) -> str:
        """Apply ANSI style by section kind if colored logs are enabled.

        ANSI references:
        - https://en.wikipedia.org/wiki/ANSI_escape_code
        """
        if not self.reasoning_log_colors:
            return text
        colors = {
            "request": "\033[96m",   # cyan
            "response": "\033[92m",  # green
            "error": "\033[91m",     # red
            "planner": "\033[93m",   # yellow
            "retrieval": "\033[94m", # blue
            "done": "\033[95m",      # magenta
            "section": "\033[90m",   # gray
            "key": "\033[1m",        # bold
        }
        reset = "\033[0m"
        color = colors.get(kind)
        if not color:
            return text
        return f"{color}{text}{reset}"
