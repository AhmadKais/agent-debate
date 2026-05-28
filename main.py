import json
import os
import sys
from pathlib import Path

from src.agents.debater_agent import ConAgent, ProAgent
from src.agents.judge_agent import JudgeAgent
from src.core.config import load_config
from src.core.gatekeeper import BudgetExceededError, Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog

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


def run_debate() -> None:
    cfg = load_config()
    topic: str = cfg["debate_topic"]
    max_pings: int = cfg["max_pings"]

    logger = FIFOLogger(
        log_dir="logs",
        max_files=cfg["log_max_files"],
        max_lines=cfg["log_max_lines"],
    )
    gatekeeper = Gatekeeper(token_budget=cfg["token_budget"])
    watchdog = Watchdog(
        timeout_seconds=cfg["timeout_seconds"],
        max_retries=cfg["max_retries"],
        logger=logger,
    )

    pro = ProAgent(gatekeeper, watchdog, logger)
    con = ConAgent(gatekeeper, watchdog, logger)
    judge = JudgeAgent(gatekeeper, watchdog, logger)

    print_separator("DEBATE TOPIC")
    print(f"  {topic}\n")
    print(f"  Rounds (pings per side): {max_pings}")
    print(f"  Token budget: {cfg['token_budget']:,}")
    print_separator()

    transcript: list[dict] = []

    def display_argument(side: str, name: str, raw: str, ping: int) -> str:
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            argument = data.get("argument", raw)
            refs = data.get("references_used", [])
        except (ValueError, json.JSONDecodeError):
            argument = raw
            refs = []

        print_separator(f"Ping {ping} — {name}")
        print(f"  {argument}\n")
        if refs:
            print("  References:")
            for r in refs:
                print(f"    • {r}")
        budget = gatekeeper.status()
        print(f"\n  [Tokens used: {budget['total_tokens']:,} / {budget['budget']:,}]")
        return argument

    try:
        opening = (
            f"The debate topic is: \"{topic}\"\n"
            "You are arguing the PRO side. Open with your strongest argument. "
            "Use web_search if you want to cite real evidence."
        )

        pro_raw = pro.generate_response(opening)
        pro_arg = display_argument("Pro", pro.name, pro_raw, ping=1)
        judge.observe("Pro", pro_arg)
        transcript.append({"ping": 1, "side": "Pro", "argument": pro_arg})

        for ping in range(1, max_pings + 1):
            try:
                con_prompt = (
                    f"Ping {ping}: The Pro side just argued:\n\"{pro_arg}\"\n\n"
                    "Tear it apart and make your strongest counter-argument for the CON side."
                )
                con_raw = con.generate_response(con_prompt)
                con_arg = display_argument("Con", con.name, con_raw, ping=ping)
                judge.observe("Con", con_arg)
                transcript.append({"ping": ping, "side": "Con", "argument": con_arg})

                if ping == max_pings:
                    break

                pro_prompt = (
                    f"Ping {ping}: The Con side just argued:\n\"{con_arg}\"\n\n"
                    "Refute it decisively and advance your PRO argument further."
                )
                pro_raw = pro.generate_response(pro_prompt)
                pro_arg = display_argument("Pro", pro.name, pro_raw, ping=ping + 1)
                judge.observe("Pro", pro_arg)
                transcript.append({"ping": ping + 1, "side": "Pro", "argument": pro_arg})

            except BudgetExceededError as e:
                print(f"\n  [BUDGET EXCEEDED] {e}")
                logger.error("main", str(e))
                break

        print_separator("FINAL VERDICT")
        verdict = judge.declare_winner()
        winner = verdict.get("winner", "Unknown")
        reason = verdict.get("reason", "")
        score_pro = verdict.get("score_pro", "?")
        score_con = verdict.get("score_con", "?")
        summary = verdict.get("summary", "")

        print(f"  WINNER: {winner.upper()}")
        print(f"  Score  — Pro: {score_pro}  |  Con: {score_con}")
        print(f"\n  Reason: {reason}")
        if summary:
            print(f"\n  Summary: {summary}")
        print_separator()

        _save_transcript(transcript, verdict, topic)

    except BudgetExceededError as e:
        print(f"\n  [BUDGET EXCEEDED] {e}")
    except KeyboardInterrupt:
        print("\n\n  Debate interrupted by user.")


def _save_transcript(transcript: list[dict], verdict: dict, topic: str) -> None:
    path = Path("logs") / "transcript_latest.json"
    path.parent.mkdir(exist_ok=True)
    with open(path, "w") as f:
        json.dump({"topic": topic, "transcript": transcript, "verdict": verdict}, f, indent=2)
    print(f"\n  Full transcript saved to: {path}")


def main() -> None:
    os.chdir(Path(__file__).parent)
    print(BANNER)

    while True:
        choice = input(MENU).strip()

        if choice == "1":
            run_debate()
        elif choice == "2":
            view_logs()
        elif choice == "3":
            cfg = load_config()
            print(f"\n  Budget: {cfg['token_budget']:,} tokens total")
            print("  (Start a debate first to see live usage)")
        elif choice == "4":
            print("\n  Goodbye.\n")
            sys.exit(0)
        else:
            print("  Invalid choice. Try again.")


if __name__ == "__main__":
    main()
