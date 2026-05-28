from duckduckgo_search import DDGS


def web_search(query: str, max_results: int = 3) -> list[dict]:
    """Return a list of {title, url, snippet} dicts from DuckDuckGo."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
    return results


SEARCH_TOOL_DEFINITION = {
    "name": "web_search",
    "description": (
        "Search the web for up-to-date information to support your argument. "
        "Use it to find statistics, expert opinions, or recent news."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string",
            }
        },
        "required": ["query"],
    },
}
