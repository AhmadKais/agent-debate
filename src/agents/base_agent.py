import json

import anthropic

from src.core.config import get_api_key, load_config
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog


class BaseAgent:
    """Common LLM call logic, tool execution, token tracking, and watchdog wrapping."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        gatekeeper: Gatekeeper,
        watchdog: Watchdog,
        logger: FIFOLogger,
        tools: list[dict] | None = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.gatekeeper = gatekeeper
        self.watchdog = watchdog
        self.logger = logger
        self.tools = tools or []
        cfg = load_config()
        self.model = cfg["model"]
        self._client = anthropic.Anthropic(api_key=get_api_key())
        self.history: list[dict] = []

    def _call_api(self, messages: list[dict]) -> anthropic.types.Message:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 1024,
            "system": self.system_prompt,
            "messages": messages,
        }
        if self.tools:
            kwargs["tools"] = self.tools
        return self._client.messages.create(**kwargs)

    def _handle_tool_use(self, response: anthropic.types.Message, messages: list[dict]) -> str:
        """Process tool_use blocks, execute tools, and get the final text response."""
        from src.tools.search import web_search

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                self.logger.info(self.name, f"Tool call: {block.name}({block.input})")
                if block.name == "web_search":
                    results = web_search(block.input["query"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(results),
                    })

        if not tool_results:
            return self._extract_text(response)

        # Persist tool interaction in history so future turns have full context
        self.history.append({"role": "assistant", "content": response.content})
        self.history.append({"role": "user", "content": tool_results})

        follow_up = self.watchdog.run(self._call_api, self.history, source=self.name)
        self.gatekeeper.record(
            follow_up.usage.input_tokens,
            follow_up.usage.output_tokens,
        )
        return self._extract_text(follow_up)

    def _extract_text(self, response: anthropic.types.Message) -> str:
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    def generate_response(self, user_message: str) -> str:
        self.gatekeeper.check_budget()
        self.history.append({"role": "user", "content": user_message})

        response = self.watchdog.run(self._call_api, self.history, source=self.name)
        self.gatekeeper.record(response.usage.input_tokens, response.usage.output_tokens)
        self.logger.info(
            self.name,
            f"Tokens used: in={response.usage.input_tokens} out={response.usage.output_tokens}",
        )

        if response.stop_reason == "tool_use":
            # _handle_tool_use appends tool interaction to self.history internally
            text = self._handle_tool_use(response, self.history)
        else:
            text = self._extract_text(response)
            self.history.append({"role": "assistant", "content": text})

        return text
