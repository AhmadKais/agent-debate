"""CLI entry point — thin UI layer. All debate logic lives in src/sdk.py."""

import json
import os
import sys
from pathlib import Path

from src.core.config import load_config
from src.sdk import DebateSDK

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║              AI AGENT DEBATE SYSTEM  v1.0                    ║
║        Pro vs Con  |  Judged by THE ARBITER                  ║
╚══════════════════════════════════════════════════════════════╝
"""

MENU = """
  1. Start Debate
  2. View Latest Logs
  3. Show Token Budget Status
  4. Exit

  Enter choice: """


def print_separator(label: str = "") -> None:
    width = 64
    if label:
        pad = (width - len(label) - 2) // 2
        print(f"\n{'─' * pad} {label} {'─' * pad}\n")
    else:
        print("─" * width)


def view_logs(log_dir: str = "logs") -> None:
    logs = sorted(Path(log_dir).glob("debate_*.log"))
    if not logs:
        print("  No log files found.")
        return
    latest = logs[-1]
    print(f"\n  Showing: {latest.name}\n")
    with open(latest) as f:
        for line in f.readlines()[-30:]:
            try:
                entry = json.loads(line)
                print(f"  [{entry['level']:7}] {entry['source']}: {entry['msg'][:100]}")
            except Exception:
                print(f"  {line.rstrip()}")


def _on_argument(side: str, name: str, argument: str, ping: int, tokens_used: int) -> None:
    print_separator(f"Ping {ping} — {name}")
    print(f"  {argument}\n")
    print(f"  [Tokens used: {tokens_used:,}]")


def run_debate() -> None:
    sdk = DebateSDK()
    cfg = sdk.cfg

    print_separator("DEBATE TOPIC")
    print(f"  {cfg['debate_topic']}\n")
    print(f"  Rounds (pings per side): {cfg['max_pings']}")
    print(f"  Token budget: {cfg['token_budget']:,}")
    print_separator()

    result = sdk.run(on_argument=_on_argument)
    verdict = result["verdict"]

    print_separator("FINAL VERDICT")
    print(f"  WINNER: {verdict.get('winner', '?').upper()}")
    print(f"  Score  — Pro: {verdict.get('score_pro', '?')}  |  Con: {verdict.get('score_con', '?')}")
    print(f"\n  Reason: {verdict.get('reason', '')}")
    if verdict.get("summary"):
        print(f"\n  Summary: {verdict['summary']}")

    usage = result["token_usage"]
    print(f"\n  Total tokens used: {usage['total_tokens']:,} / {usage['budget']:,}")
    print("  Transcript saved to: logs/transcript_latest.json")
    print_separator()


def main() -> None:
    os.chdir(Path(__file__).parent)
    print(BANNER)

    while True:
        choice = input(MENU).strip()

        if choice == "1":
            run_debate()
        elif choice == "2":
            cfg = load_config()
            view_logs(log_dir=cfg.get("log_dir", "logs"))
        elif choice == "3":
            cfg = load_config()
            print(f"\n  Budget: {cfg['token_budget']:,} tokens total")
            print("  (Run a debate first to see live usage)")
        elif choice == "4":
            print("\n  Goodbye.\n")
            sys.exit(0)
        else:
            print("  Invalid choice. Try again.")


if __name__ == "__main__":
    main()
