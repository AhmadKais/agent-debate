"""Pro and Con debater agents — argue opposite sides of the debate topic."""

from src.agents.base_agent import BaseAgent
from src.agents.prompts import CON_SYSTEM_PROMPT, PRO_SYSTEM_PROMPT
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog
from src.tools.search import SEARCH_TOOL_DEFINITION


class ProAgent(BaseAgent):
    """AXIOM — aggressive PRO debater. Uses web_search for every argument."""

    def __init__(self, gatekeeper: Gatekeeper, watchdog: Watchdog, logger: FIFOLogger):
        super().__init__(
            name="AXIOM (Pro)",
            system_prompt=PRO_SYSTEM_PROMPT,
            gatekeeper=gatekeeper,
            watchdog=watchdog,
            logger=logger,
            tools=[SEARCH_TOOL_DEFINITION],
        )


class ConAgent(BaseAgent):
    """NEMESIS — surgical CON debater. Uses web_search for every argument."""

    def __init__(self, gatekeeper: Gatekeeper, watchdog: Watchdog, logger: FIFOLogger):
        super().__init__(
            name="NEMESIS (Con)",
            system_prompt=CON_SYSTEM_PROMPT,
            gatekeeper=gatekeeper,
            watchdog=watchdog,
            logger=logger,
            tools=[SEARCH_TOOL_DEFINITION],
        )
