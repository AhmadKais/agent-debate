"""Base agent: shared LLM call logic, tool execution, token tracking, watchdog.

All API calls go through Gatekeeper.execute() — never call the Anthropic
client directly. This enforces the API gateway pattern from §5.1.
"""

import json

import anthropic

from src.core.config import get_api_key, load_config
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog


class BaseAgent:
    """Common LLM call logic, tool execution, token tracking, and watchdog wrapping.

    All subagents (Pro, Con, Judge) extend this class.
    Every API call is routed through Gatekeeper.execute() — the single
    audit and enforcement point for cost control.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        gatekeeper: Gatekeeper,
        watchdog: Watchdog,
        logger: FIFOLogger,
        tools: list[dict] | None = None,
    ):
        """Initialise agent with shared infrastructure and load model from config."""
        self.name = name
        self.system_prompt = system_prompt
        self.gatekeeper = gatekeeper
        self.watchdog = watchdog
        self.logger = logger
        self.tools = tools or []
        cfg = load_config()
        self.model = cfg["model"]
        self._max_tool_rounds: int = cfg.get("max_tool_rounds", 5)
        self.max_tokens: int = 500  # overridable per-agent (JudgeAgent uses 2048 for verdict)
        self._client = anthropic.Anthropic(api_key=get_api_key())
        self.history: list[dict] = []

    def _call_api(self, messages: list[dict]) -> anthropic.types.Message:
        """Send messages to Claude via the Gatekeeper API gateway.

        All budget checking and token recording happens inside
        gatekeeper.execute() — this method never calls the client directly.
        """
        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.system_prompt,
            "messages": messages,
        }
        if self.tools:
            kwargs["tools"] = self.tools
        return self.gatekeeper.execute(self._client.messages.create, **kwargs)

    def _handle_tool_use(self, response: anthropic.types.Message, depth: int = 0) -> str:
        """Execute tool calls recursively until Claude returns a text response.

        Claude sometimes chains multiple searches before writing the argument.
        _MAX_TOOL_ROUNDS depth cap prevents runaway loops.
        Token recording is handled by gatekeeper.execute() inside _call_api.
        """
        from src.tools.search import web_search

        if depth >= self._max_tool_rounds:
            self.logger.warning(self.name, "Max tool rounds reached — extracting text as-is")
            return self._extract_text(response)

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                self.logger.info(self.name, f"Tool call: {block.name}({block.input})")
                if block.name == "web_search":
                    results = web_search(block.input["query"])
                    trimmed = [
                        {"title": r["title"], "url": r["url"], "snippet": r["snippet"][:200]}
                        for r in results
                    ]
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(trimmed),
                    })

        if not tool_results:
            return self._extract_text(response)

        self.history.append({"role": "assistant", "content": response.content})
        self.history.append({"role": "user", "content": tool_results})

        follow_up = self.watchdog.run(self._call_api, self.history, source=self.name)

        if follow_up.stop_reason == "tool_use":
            return self._handle_tool_use(follow_up, depth=depth + 1)

        return self._extract_text(follow_up)

    def _extract_text(self, response: anthropic.types.Message) -> str:
        """Pull the first text block from a Claude response."""
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove markdown code fences that LLMs sometimes wrap JSON responses in.

        Agents are prompted to output raw JSON, but occasionally return
        ```json ... ``` blocks. Stripping keeps history and returned values clean.
        """
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            return "\n".join(inner).strip()
        return stripped

    def generate_response(self, user_message: str) -> str:
        """Send a user message, execute any tool calls, return clean text response.

        Budget checking and token recording are handled inside gatekeeper.execute()
        via _call_api — no explicit check_budget/record calls needed here.
        """
        self.history.append({"role": "user", "content": user_message})

        response = self.watchdog.run(self._call_api, self.history, source=self.name)
        self.logger.info(
            self.name,
            f"Tokens: in={response.usage.input_tokens} out={response.usage.output_tokens}",
        )

        if response.stop_reason == "tool_use":
            text = self._handle_tool_use(response)
        else:
            text = self._extract_text(response)

        text = self._strip_markdown(text)
        self.history.append({"role": "assistant", "content": text})
        return text
