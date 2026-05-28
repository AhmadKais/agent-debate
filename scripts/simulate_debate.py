"""
Standalone debate simulation (no API key needed).
Runs the full orchestration loop with realistic mock arguments and prints
the complete debate to stdout exactly as the terminal UI would show it.
"""
import json
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-mock-key-for-simulation")

from src.agents.debater_agent import ConAgent, ProAgent
from src.agents.judge_agent import JudgeAgent
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog

TOPIC = "Lionel Messi is the greatest footballer of all time, superior to Cristiano Ronaldo"

# ---------------------------------------------------------------------------
# PRO side (AXIOM) — argues FOR Messi
# ---------------------------------------------------------------------------
PRO_RESPONSES = [
    json.dumps({
        "argument": (
            "The numbers are not even close. Messi has won 8 Ballon d'Or awards — the most "
            "in history. Ronaldo has 5. Messi finished his La Liga career with 474 goals in "
            "520 games, a ratio Ronaldo never matched in Spain despite playing for the most "
            "financially powerful club on earth. But statistics alone undersell Messi. He "
            "doesn't just score — he creates. His 362 La Liga assists dwarf Ronaldo's 131. "
            "Messi is simultaneously the greatest scorer AND the greatest playmaker of his "
            "generation. Ronaldo is a phenomenal striker. Messi is a complete footballer."
        ),
        "references_used": [
            "https://www.transfermarkt.com/lionel-messi/leistungsdaten",
            "https://www.ballon-dor.com/history",
        ],
    }),
    json.dumps({
        "argument": (
            "NEMESIS brings up Champions League goals — fine. Messi won the Champions League "
            "with Barcelona playing the most beautiful football in history: the Pep Guardiola "
            "era of 2009-2011 where Barca dismantled every opponent with Messi as the engine. "
            "Meanwhile, let us talk about international football — the ultimate test. Messi "
            "won the 2021 Copa América, ending Argentina's 28-year trophy drought, AND the "
            "2022 World Cup, the most coveted prize in football. He was Player of the Tournament "
            "at the World Cup at age 35. Ronaldo has won nothing with Portugal at a senior "
            "tournament. Zero. The World Cup separates legends from icons."
        ),
        "references_used": [
            "https://www.fifa.com/worldcup/qatar2022/awards",
            "https://www.conmebol.com/copaamerica2021",
        ],
    }),
    json.dumps({
        "argument": (
            "NEMESIS pivots to athleticism and physicality — the last refuge of the Ronaldo "
            "argument. Yes, Ronaldo has a magnificent physique. But football is not bodybuilding. "
            "Messi's low centre of gravity, balance, and close control at full speed are "
            "superhuman gifts that cannot be manufactured in a gym. Andrés Iniesta, Xavi, "
            "Zlatan Ibrahimović, and Pep Guardiola — men who played and coached BOTH players — "
            "unanimously say Messi is the better footballer. When your peers vote you GOAT, "
            "the argument is over."
        ),
        "references_used": [
            "https://www.theguardian.com/football/messi-goat-peer-votes",
            "https://bleacherreport.com/messi-ibrahimovic-interview",
        ],
    }),
    json.dumps({
        "argument": (
            "NEMESIS claims Ronaldo's trophies across multiple leagues prove more. This "
            "argument backfires spectacularly. Messi won 10 La Liga titles — the most "
            "competitive domestic league of the 2000s-2010s era. He did this while facing "
            "a Ronaldo-era Real Madrid that spent a billion euros on their squad. Ronaldo "
            "left the moment the competition got too hard. Messi stayed, dragged average "
            "squads to titles on pure individual brilliance, and STILL ended his Barca "
            "career as the all-time top scorer. Loyalty under pressure is not weakness — "
            "it is character."
        ),
        "references_used": [
            "https://www.espn.com/soccer/story/messi-laliga-titles",
            "https://www.marca.com/messi-vs-ronaldo-trophies",
        ],
    }),
    json.dumps({
        "argument": (
            "Final argument: the 2022 World Cup is Messi's definitive masterpiece. Argentina "
            "vs France in the final was the greatest World Cup final in history. Messi scored "
            "twice in normal time, once in extra time, converted his penalty in the shootout, "
            "and delivered the most watched moment in football history. At 35, against the "
            "best players in the world, he performed his greatest game. Ronaldo at 35 was "
            "benched by his club, cried in public, and never won a major tournament. "
            "The World Cup is the GOAT's trophy. Messi has it. Ronaldo does not."
        ),
        "references_used": [
            "https://www.fifa.com/worldcup/qatar2022/final",
            "https://www.bbc.com/sport/football/messi-world-cup-2022",
        ],
    }),
]

# ---------------------------------------------------------------------------
# CON side (NEMESIS) — argues FOR Ronaldo
# ---------------------------------------------------------------------------
CON_RESPONSES = [
    json.dumps({
        "argument": (
            "AXIOM waves Ballon d'Or trophies like they are objective truth. They are not — "
            "they are voted by journalists. In 2010, Xavi Hernández was robbed to give Messi "
            "his third. In 2012, Ronaldo outscored Messi in La Liga yet lost the award. "
            "The Ballon d'Or is a popularity contest, not a performance metric. Let us use "
            "real numbers: Ronaldo has scored 894 career goals — the highest in football "
            "history. He did it at Manchester United, Real Madrid, AND Juventus, dominating "
            "THREE different leagues in THREE different countries. Messi has never proven "
            "himself outside Spain until his twilight years."
        ),
        "references_used": [
            "https://www.transfermarkt.com/cristiano-ronaldo/leistungsdaten",
            "https://www.guinnessworldrecords.com/cristiano-ronaldo-goals",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM's 'World Cup' argument is the weakest case for Messi. He needed 5 "
            "attempts and needed to be bailed out by Di María, Mac Allister, and Julián "
            "Álvarez — a supporting cast Argentina deliberately built around him. Ronaldo "
            "dragged Portugal to the 2016 Euro title almost single-handedly, scoring 3 goals, "
            "then won the inaugural UEFA Nations League in 2019. Moreover, Ronaldo scored "
            "140 Champions League goals — 17 more than Messi — including a hat-trick at "
            "41 years old for Portugal. He performs on the biggest stages. Every. Single. Time."
        ),
        "references_used": [
            "https://www.uefa.com/uefachampionsleague/history/rankings/players/goals_scored",
            "https://www.uefa.com/uefaeuro/history/winners",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM quotes peers who prefer Messi — cherry-picked opinions. Let me quote "
            "facts. Ronaldo won Premier League, La Liga, AND Serie A titles. He adapted his "
            "game across radically different footballing cultures and dominated every one. "
            "Messi at PSG was invisible — two largely underwhelming seasons where he failed "
            "to impose himself on Ligue 1. He fled to the MLS retirement league in Miami. "
            "Ronaldo, at the same age, moved to Saudi Arabia and immediately broke the "
            "Saudi Pro League scoring record. Same age, completely different impact. "
            "Adaptability is greatness. Messi is a one-league wonder."
        ),
        "references_used": [
            "https://www.lequipe.fr/messi-psg-stats",
            "https://www.arabnews.com/ronaldo-saudi-league-record",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM calls Messi's body a 'superhuman gift.' This is exactly the problem. "
            "Messi was born with extraordinary natural talent and a perfect build for "
            "dribbling. Ronaldo was born an average player. He was not the most talented "
            "teenager at Sporting Lisbon. He became the greatest through iron discipline, "
            "relentless training, and a refusal to accept physical limitations. He reinvented "
            "himself from a tricky winger into a lethal striker after 30. That mental "
            "strength and self-made greatness is more admirable — and more instructive — "
            "than being born gifted."
        ),
        "references_used": [
            "https://www.sportingnews.com/ronaldo-training-discipline",
            "https://www.theathlete.com/ronaldo-self-made-story",
        ],
    }),
    json.dumps({
        "argument": (
            "My closing argument: consistency over two decades across every competition. "
            "Ronaldo has scored 50+ goals in a season NINE times. He has scored 30+ goals "
            "in 17 consecutive seasons. He has scored in 5 different World Cups. He scored "
            "a free-kick hat-trick against Spain at the 2018 World Cup at age 33. "
            "The argument that Messi is GOAT rests on one tournament in 2022. Ronaldo's "
            "case rests on 22 years of elite performance across every competition, every "
            "league, every stage. Longevity at the summit is the truest measure of greatness. "
            "By that measure, Ronaldo is untouchable."
        ),
        "references_used": [
            "https://www.transfermarkt.com/cristiano-ronaldo/leistungsdaten",
            "https://www.fifaindex.com/ronaldo-world-cup-goals",
        ],
    }),
]

JUDGE_ROUTE = json.dumps({"route_to": "Con"})

JUDGE_VERDICT = json.dumps({
    "winner": "Pro",
    "score_pro": 79,
    "score_con": 74,
    "reason": (
        "Both debaters made elite arguments in what is genuinely the closest debate in "
        "football history. NEMESIS landed real blows — the multi-league dominance point "
        "and the 'self-made greatness' argument were compelling. However, AXIOM's trump "
        "card proved decisive: the 2022 World Cup. NEMESIS attempted to diminish it by "
        "citing Messi's supporting cast, but every World Cup winner has a supporting cast "
        "— Ronaldo never even reached a final to test his. AXIOM's argument that the "
        "World Cup is the ultimate differentiator was never convincingly refuted. "
        "Messi's 2022 performance — at 35, in the greatest final ever played — is the "
        "single most persuasive exhibit in this debate. Pro wins by a narrow but clear margin."
    ),
    "summary": (
        "A ferocious 5-round debate on the greatest footballer of all time. Pro argued "
        "Ballon d'Or dominance, creative supremacy, peer endorsement, and the 2022 World "
        "Cup. Con argued raw goal records, multi-league adaptability, self-made greatness, "
        "and 22-year consistency. Pro edges it on the strength of the World Cup argument "
        "and the quality of Messi's creative output — but this one was close."
    ),
})

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

WIDTH = 66

def separator(label=""):
    if label:
        pad = (WIDTH - len(label) - 2) // 2
        print(f"\n{'─' * pad} {label} {'─' * (WIDTH - len(label) - 2 - pad)}\n")
    else:
        print("─" * WIDTH)


def show_argument(name, raw, ping, tokens_used, budget):
    try:
        data = json.loads(raw)
        arg = data.get("argument", raw)
        refs = data.get("references_used", [])
    except (ValueError, json.JSONDecodeError):
        arg = raw
        refs = []

    separator(f"Ping {ping} — {name}")
    for line in _wrap(arg, 62):
        print(f"  {line}")
    print()
    if refs:
        print("  References:")
        for r in refs:
            print(f"    • {r}")
    print(f"\n  [Tokens used: {tokens_used:,} / {budget:,}]")
    return arg


def _wrap(text, width):
    words = text.split()
    lines, current = [], []
    for w in words:
        if sum(len(x) + 1 for x in current) + len(w) > width:
            lines.append(" ".join(current))
            current = [w]
        else:
            current.append(w)
    if current:
        lines.append(" ".join(current))
    return lines


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------

def run_debate():
    print("\n" + "═" * WIDTH)
    print("  AI AGENT DEBATE SYSTEM  v1.0".center(WIDTH))
    print("  Pro vs Con  |  Judged by THE ARBITER".center(WIDTH))
    print("═" * WIDTH)

    separator("DEBATE TOPIC")
    print(f"  {TOPIC}\n")
    print("  Rounds (pings per side): 5")
    print("  Token budget: 150,000")
    separator()

    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp, max_files=20, max_lines=500)
        gatekeeper = Gatekeeper(token_budget=150_000)
        watchdog = Watchdog(timeout_seconds=30, max_retries=3, logger=logger)

        pro_iter = iter(PRO_RESPONSES)
        con_iter = iter(CON_RESPONSES)
        judge_calls = {"n": 0}

        def fake_message(text, in_tok=120, out_tok=180):
            block = SimpleNamespace(type="text", text=text)
            usage = SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok)
            return SimpleNamespace(content=[block], usage=usage, stop_reason="end_turn")

        def judge_side_effect(**kwargs):
            judge_calls["n"] += 1
            if judge_calls["n"] > 10:
                return fake_message(JUDGE_VERDICT, 400, 300)
            return fake_message(JUDGE_ROUTE)

        pro_client = MagicMock()
        con_client = MagicMock()
        judge_client = MagicMock()
        pro_client.messages.create.side_effect = (
            lambda **kw: fake_message(next(pro_iter, PRO_RESPONSES[-1]))
        )
        con_client.messages.create.side_effect = (
            lambda **kw: fake_message(next(con_iter, CON_RESPONSES[-1]))
        )
        judge_client.messages.create.side_effect = judge_side_effect

        clients = iter([pro_client, con_client, judge_client])

        with patch("anthropic.Anthropic", side_effect=lambda **kw: next(clients)):
            pro = ProAgent(gatekeeper, watchdog, logger)
            con = ConAgent(gatekeeper, watchdog, logger)
            judge = JudgeAgent(gatekeeper, watchdog, logger)

        transcript = []
        max_pings = 5

        # Opening argument — Pro
        pro_raw = pro.generate_response(
            f'The debate topic is: "{TOPIC}"\n'
            "You are arguing the PRO side. Open with your strongest argument. "
            "Use web_search to find real evidence."
        )
        pro_arg = show_argument(pro.name, pro_raw, 1, gatekeeper.total_tokens, 150_000)
        judge.observe("Pro", pro_arg)
        transcript.append({"ping": 1, "side": "Pro", "argument": pro_arg})

        for ping in range(1, max_pings + 1):
            con_raw = con.generate_response(
                f'Ping {ping}: The Pro side just argued:\n"{pro_arg}"\n\n'
                "Tear it apart and make your strongest CON counter-argument."
            )
            con_arg = show_argument(con.name, con_raw, ping, gatekeeper.total_tokens, 150_000)
            judge.observe("Con", con_arg)
            transcript.append({"ping": ping, "side": "Con", "argument": con_arg})

            if ping == max_pings:
                break

            pro_raw = pro.generate_response(
                f'Ping {ping}: The Con side just argued:\n"{con_arg}"\n\n'
                "Refute it decisively and advance your PRO argument."
            )
            pro_arg = show_argument(pro.name, pro_raw, ping + 1, gatekeeper.total_tokens, 150_000)
            judge.observe("Pro", pro_arg)
            transcript.append({"ping": ping + 1, "side": "Pro", "argument": pro_arg})

        # Final verdict
        verdict = judge.declare_winner()
        separator("FINAL VERDICT")
        winner = verdict.get("winner", "?")
        sp = verdict.get("score_pro", "?")
        sc = verdict.get("score_con", "?")
        reason = verdict.get("reason", "")
        summary = verdict.get("summary", "")

        print(f"  WINNER : {winner.upper()}")
        print(f"  Score  — Pro (AXIOM): {sp}  |  Con (NEMESIS): {sc}\n")
        print("  Reason:")
        for line in _wrap(reason, 62):
            print(f"    {line}")
        if summary:
            print("\n  Summary:")
            for line in _wrap(summary, 62):
                print(f"    {line}")
        separator()
        print(f"  Total tokens consumed: {gatekeeper.total_tokens:,} / 150,000")
        print(f"  Transcript entries   : {len(transcript)}")
        separator()

        return transcript, verdict


if __name__ == "__main__":
    run_debate()
