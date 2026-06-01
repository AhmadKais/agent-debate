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

TOPIC = "Social media has done more damage to society than any religion or ideology"

# ---------------------------------------------------------------------------
# PRO side (AXIOM) — argues social media HAS done more damage
# ---------------------------------------------------------------------------
PRO_RESPONSES = [
    json.dumps({
        "argument": (
            "The evidence is clinical. Social media has driven a global mental health epidemic "
            "with no historical parallel. Since 2012 — the year smartphones and social platforms "
            "reached mass adoption — rates of depression, anxiety, and self-harm among teenagers "
            "have risen 50-150% across the US, UK, and Australia. Jonathan Haidt's research at "
            "NYU documents the direct correlation. No religion or ideology in history triggered "
            "a mental health crisis of this scale, this fast, affecting this many people. "
            "The Inquisition lasted centuries and killed tens of thousands. Instagram damaged "
            "the mental health of hundreds of millions of teenage girls in under a decade. "
            "Speed and scale matter. Social media wins this comparison decisively."
        ),
        "references_used": [
            "https://jonathanhaidt.com/anxious-generation",
            "https://www.thelancet.com/journals/lanpsy/article/social-media-mental-health",
        ],
    }),
    json.dumps({
        "argument": (
            "NEMESIS points to historical religious violence — but conveniently ignores that "
            "social media actively AMPLIFIES and accelerates that same violence today. The "
            "Rohingya genocide in Myanmar was directly facilitated by Facebook. UN investigators "
            "concluded that Facebook played a 'determining role' in spreading hate speech that "
            "led to mass murder. The 2021 Ethiopian civil war was inflamed by Facebook's "
            "algorithm promoting ethnic incitement. Social media doesn't just cause its own "
            "damage — it turbocharges every other source of ideological harm. It is a "
            "damage multiplier for the entire category NEMESIS is defending."
        ),
        "references_used": [
            "https://www.reuters.com/article/us-myanmar-facebook-un",
            "https://www.amnesty.org/facebook-rohingya-report",
        ],
    }),
    json.dumps({
        "argument": (
            "NEMESIS argues ideologies caused more structural damage. But democracy itself "
            "is now under threat from social media. The 2016 US election, Brexit, and "
            "elections across 18 countries show that coordinated disinformation campaigns "
            "on social platforms have destabilized democratic institutions. The January 6th "
            "Capitol attack was organized on Facebook and Twitter. No ideology ever had a "
            "mechanism to radicalize millions of ordinary people in their own living rooms, "
            "in real time, with algorithmic precision. Social media didn't just spread an "
            "ideology — it became the infrastructure for radicalization itself."
        ),
        "references_used": [
            "https://www.nature.com/articles/s41562-021-social-media-democracy",
            "https://www.senate.gov/jan6-report-social-media",
        ],
    }),
    json.dumps({
        "argument": (
            "NEMESIS defends religion and ideology by citing their positive contributions — "
            "hospitals, universities, social cohesion. Where are social media's equivalent "
            "contributions? Viral cat videos? The attention economy is structurally designed "
            "to maximize outrage, addiction, and division because those emotions generate "
            "clicks. No religion was engineered by a for-profit corporation optimizing "
            "engagement metrics at the expense of human wellbeing. Facebook's own internal "
            "research — leaked by Frances Haugen — showed they KNEW Instagram harmed "
            "teenage girls and chose profit over people. That is premeditated social damage."
        ),
        "references_used": [
            "https://www.wsj.com/articles/facebook-files-frances-haugen",
            "https://www.congress.gov/haugen-testimony-2021",
        ],
    }),
    json.dumps({
        "argument": (
            "My closing argument: loneliness. The American Surgeon General declared a "
            "loneliness epidemic in 2023, citing social media as a primary driver. Humans "
            "are replacing deep, nourishing relationships with shallow digital performance. "
            "Friendship rates, marriage rates, and civic participation have collapsed "
            "precisely as social media use exploded. Every ideology NEMESIS mentions — "
            "even the destructive ones — built communities, forged bonds, gave people "
            "belonging. Social media promised connection and delivered isolation at "
            "civilizational scale. That is the ultimate damage: the erosion of human "
            "society from the inside."
        ),
        "references_used": [
            "https://www.hhs.gov/surgeon-general/loneliness-epidemic",
            "https://www.pewresearch.org/social-media-loneliness-2023",
        ],
    }),
]

# ---------------------------------------------------------------------------
# CON side (NEMESIS) — argues religions/ideologies caused MORE damage
# ---------------------------------------------------------------------------
CON_RESPONSES = [
    json.dumps({
        "argument": (
            "AXIOM's mental health statistics, however concerning, pale against the body "
            "count of ideology. The 20th century alone: Communism killed an estimated "
            "100 million people through famine, gulags, and purges. Nazism killed 70 million "
            "in World War II. Colonial Christianity enabled the transatlantic slave trade — "
            "12 million people enslaved over 400 years. The Crusades, the Inquisition, "
            "sectarian conflicts from Northern Ireland to the Middle East. Social media "
            "has caused depression and anxiety. Ideologies have caused industrialized "
            "mass murder. The comparison is not even close on the metric that matters most: "
            "human lives ended."
        ),
        "references_used": [
            "https://www.britannica.com/topic/20th-century-death-toll",
            "https://www.history.com/topics/slave-trade",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM blames Facebook for the Rohingya crisis — but Facebook was merely the "
            "latest medium for hatred that existed long before any app. Myanmar's anti-Rohingya "
            "sentiment is rooted in Buddhist nationalism decades old. Remove Facebook and the "
            "hatred does not disappear — it finds another channel. The 1994 Rwandan genocide "
            "killed 800,000 people in 100 days using RADIO. Radio had no algorithm, no "
            "engagement optimization, no for-profit motive. Ideological hatred is the root "
            "cause. Social media is merely the current amplifier. Blaming the microphone "
            "for the words spoken into it is a category error."
        ),
        "references_used": [
            "https://www.bbc.com/news/world-africa-rwanda-radio-genocide",
            "https://www.hrw.org/report/myanmar-rohingya-crisis",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM claims social media is damaging democracy. But democracy survived the "
            "printing press — which spread the Protestant Reformation and caused 150 years "
            "of religious warfare across Europe. It survived radio, which brought Hitler to "
            "power. It survived television, which was called civilization's doom in the 1960s. "
            "Every new communication technology triggers a moral panic. Social media is "
            "not uniquely dangerous to democracy — it is the latest in a long line of "
            "disruptive media. Meanwhile, Marxist-Leninist ideology actually ABOLISHED "
            "democracy in 15 countries for 70 years. That is real democratic destruction."
        ),
        "references_used": [
            "https://www.theatlantic.com/technology/printing-press-reformation",
            "https://www.freedomhouse.org/democracy-decline-ideology",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM dismisses social media's benefits to score rhetorical points. Let me "
            "name them: the Arab Spring gave millions their first taste of political agency. "
            "The #MeToo movement ended the careers of hundreds of serial predators who had "
            "operated with impunity for decades. Black Lives Matter organized the largest "
            "protest movement in American history. Social media democratized information, "
            "gave voice to the voiceless, and connected diaspora communities across the "
            "world. AXIOM's framing ignores that the same platform that spreads harm also "
            "enables movements that reduce it. No tool is purely destructive."
        ),
        "references_used": [
            "https://www.pewresearch.org/social-media-arab-spring",
            "https://www.nytimes.com/metoo-social-media-impact",
        ],
    }),
    json.dumps({
        "argument": (
            "My closing argument: time horizon. Social media has existed for roughly 20 years. "
            "We are still in the acute phase of adaptation — like the first generation to "
            "experience cars, electricity, or antibiotics, all of which caused harm before "
            "society adapted. Ideology, by contrast, has had millennia to perfect its "
            "mechanisms of control, persecution, and mass violence. The Thirty Years War "
            "killed 8 million people over religion in the 1600s. The Holocaust was "
            "ideologically engineered. Social media's damage is real and serious. But to "
            "claim it surpasses centuries of theocracy, totalitarianism, and genocide is "
            "to confuse recency with magnitude. History's verdict is clear."
        ),
        "references_used": [
            "https://www.britannica.com/event/Thirty-Years-War",
            "https://www.ushmm.org/genocide-definition",
        ],
    }),
]

JUDGE_ROUTE = json.dumps({"route_to": "Con"})

JUDGE_VERDICT = json.dumps({
    "winner": "Con",
    "score_pro": 74,
    "score_con": 83,
    "reason": (
        "Both debaters made serious, well-evidenced arguments. AXIOM's case was emotionally "
        "compelling — the mental health data, the Rohingya genocide, the loneliness epidemic "
        "are all real and disturbing. However, NEMESIS made the decisive move in Round 2 by "
        "attacking the causal chain: social media amplifies pre-existing hatred, it does not "
        "create it. The Rwanda radio genocide example was devastating — 800,000 killed with "
        "no algorithm. NEMESIS also won the time-horizon argument: 20 years of social media "
        "damage versus millennia of ideological mass murder is not a close comparison by "
        "body count. AXIOM never successfully refuted the 100 million killed by 20th-century "
        "ideology. Persuasive force favors the side with the larger historical canvas. "
        "Con wins clearly."
    ),
    "summary": (
        "A sharp 5-round debate on social media versus religion and ideology as agents of "
        "societal damage. Pro argued mental health crises, democratic destabilization, "
        "the Rohingya genocide, and civilizational loneliness. Con argued 20th-century "
        "death tolls, the Rwanda radio precedent, democracy's survival of past media "
        "disruptions, and social media's democratizing benefits. Con wins on historical "
        "magnitude and causal reasoning."
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
