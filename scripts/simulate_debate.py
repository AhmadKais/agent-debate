"""
Standalone simulation of the Soviet Union debate (no API key needed).
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

TOPIC = "The Soviet Union was a force for good in the world"

# ---------------------------------------------------------------------------
# Realistic mock arguments — Soviet Union PRO side (AXIOM)
# ---------------------------------------------------------------------------
PRO_RESPONSES = [
    json.dumps({
        "argument": (
            "The Soviet Union industrialized an agrarian backwater into a superpower in under "
            "two decades — a feat no capitalist nation achieved at that speed. By 1957, the USSR "
            "launched Sputnik, the first satellite in human history. By 1961, Yuri Gagarin became "
            "the first human in space. These are not the achievements of a purely evil empire — "
            "they are the triumphs of a society that mobilized collective human potential on an "
            "unprecedented scale. Literacy went from 30% in 1917 to 99% by 1970. Healthcare was "
            "free and universal. Life expectancy doubled. Judge NEMESIS on outcomes, not ideology."
        ),
        "references_used": [
            "https://en.wikipedia.org/wiki/Soviet_space_program",
            "https://ourworldindata.org/literacy",
        ],
    }),
    json.dumps({
        "argument": (
            "NEMESIS screams 'Gulag' — conveniently forgetting that the United States ran "
            "Jim Crow apartheid during the same era and conducted the Tuskegee experiments on "
            "its own citizens. Every great power has atrocities. The question is the balance sheet. "
            "The USSR defeated Nazi Germany — absorbing 27 million deaths to save European "
            "civilization while the West dithered. Without the Red Army, NEMESIS would be "
            "debating in German. That sacrifice alone places the Soviet Union on the right side "
            "of history's most important conflict."
        ),
        "references_used": [
            "https://www.bbc.com/news/world-europe-26079957",
            "https://encyclopedia.ushmm.org/content/en/article/soviet-union",
        ],
    }),
    json.dumps({
        "argument": (
            "NEMESIS clings to the Holodomor without acknowledging that the famine was "
            "exacerbated by drought and global grain market collapse — conditions that also "
            "killed millions in British India and colonial Africa under capitalist management. "
            "Meanwhile, the Soviet Union gave the world the first legally mandated 8-hour "
            "workday, paid maternity leave, and free higher education — rights that Western "
            "workers had to fight for decades to obtain. The USSR exported progress."
        ),
        "references_used": [
            "https://www.ilo.org/global/about-the-ilo/history",
            "https://www.jstor.org/stable/holodomor-historiography",
        ],
    }),
    json.dumps({
        "argument": (
            "NEMESIS invokes Afghanistan — yet the US has waged more foreign wars since 1945 "
            "than any nation on earth. Vietnam: 3 million dead. Iraq: 1 million dead. The Soviet "
            "intervention in Afghanistan was brutal, yes — but it was also a Cold War proxy "
            "conflict ignited by US-funded Mujahideen. The USSR's military record outside its "
            "borders pales in comparison to NATO's body count. Selective moral outrage is not "
            "an argument — it is hypocrisy."
        ),
        "references_used": [
            "https://watson.brown.edu/costsofwar",
            "https://nsarchive.gwu.edu/afghanistan",
        ],
    }),
    json.dumps({
        "argument": (
            "My final argument: the Soviet Union's greatest legacy is the global left. Every "
            "workers' right you enjoy today — the weekend, minimum wage, occupational safety — "
            "exists because capitalists feared Soviet-style revolution. The USSR did not merely "
            "benefit its own citizens; its existence forced Western governments to treat their "
            "workers as human beings rather than disposable machinery. That counterfactual "
            "benefit to billions of non-Soviet workers is the Soviet Union's most underrated "
            "contribution to human welfare."
        ),
        "references_used": [
            "https://www.theguardian.com/commentisfree/labor-rights-soviet-threat",
            "https://www.brookings.edu/cold-war-welfare-state",
        ],
    }),
]

# ---------------------------------------------------------------------------
# Realistic mock arguments — Soviet Union CON side (NEMESIS)
# ---------------------------------------------------------------------------
CON_RESPONSES = [
    json.dumps({
        "argument": (
            "AXIOM romanticizes Soviet industrialization while burying its price tag: the Gulag "
            "Archipelago. Between 1918 and 1956, an estimated 18 million people were processed "
            "through Soviet forced labor camps. The 'achievements' AXIOM celebrates — the steel, "
            "the rockets, the canals — were built on slave labor. Sputnik was launched on the "
            "backs of zeks who froze to death in Siberia. Celebrating Soviet 'progress' without "
            "acknowledging its human cost is like praising the pyramids while ignoring the "
            "enslaved people who built them."
        ),
        "references_used": [
            "https://www.annefrank.org/en/topics/gulag/",
            "https://www.hoover.org/research/gulag-history",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM's whataboutism about Jim Crow is a debater's trick, not an argument. "
            "We are evaluating the Soviet Union — not the United States. The Holodomor of "
            "1932-33 killed between 3.5 and 7 million Ukrainians through deliberate, engineered "
            "famine. Stalin confiscated grain from starving villages to fund industrialization "
            "and silence nationalist resistance. This was not a drought — Soviet officials "
            "actively prevented famine relief and blacklisted villages that failed quotas. "
            "A force for good does not manufacture famines to crush dissent."
        ),
        "references_used": [
            "https://www.holodomor.ca/what-is-the-holodomor/",
            "https://www.wilsoncenter.org/article/holodomor-archives",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM praises 'free education' while omitting that Soviet universities were "
            "ideological indoctrination factories where Lysenkoist pseudoscience was mandated "
            "state doctrine, resulting in the collapse of Soviet genetics and agricultural "
            "science for a generation. Thousands of real scientists were imprisoned or executed "
            "for teaching evolution and Mendelian genetics. Free education that destroys the "
            "truth is not a gift — it is a weapon against the mind."
        ),
        "references_used": [
            "https://www.britannica.com/science/Lysenkoism",
            "https://www.nature.com/articles/d41586-017-07656-4",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM deflects on Afghanistan by counting American casualties elsewhere. "
            "Let us stay focused: the Soviet invasion of Afghanistan from 1979 to 1989 "
            "killed 1-2 million Afghans, created 5 million refugees, and deployed chemical "
            "weapons against civilian populations. The Budapest 1956 and Prague 1968 "
            "invasions crushed democratic movements with tanks. The Iron Curtain was not "
            "a metaphor — it was a wall with snipers to shoot anyone trying to leave. "
            "Good forces do not imprison entire nations."
        ),
        "references_used": [
            "https://www.amnesty.org/en/latest/research/soviet-afghanistan/",
            "https://www.bbc.com/news/world-europe-prague-spring",
        ],
    }),
    json.dumps({
        "argument": (
            "AXIOM's final gambit — 'the USSR made capitalism kinder' — is the most desperate "
            "argument yet. It concedes that the Soviet system itself was not good, and instead "
            "claims credit for scaring other countries into treating workers better. By this "
            "logic, we should thank smallpox for the invention of vaccines. The Soviet Union "
            "collapsed because its own people rejected it. In 1991, not a single Soviet citizen "
            "took to the streets to save the USSR. That referendum was unanimous: the Soviet "
            "Union was not a force for good, and its own population knew it best."
        ),
        "references_used": [
            "https://www.pewresearch.org/global/2011/12/05/confidence-in-democracy-and-capitalism-wanes-in-former-soviet-union/",
            "https://academic.oup.com/book/soviet-collapse",
        ],
    }),
]

JUDGE_ROUTE = json.dumps({"route_to": "Con"})

JUDGE_VERDICT = json.dumps({
    "winner": "Con",
    "score_pro": 71,
    "score_con": 82,
    "reason": (
        "Both debaters were sharp, but NEMESIS landed more decisive blows. AXIOM's "
        "arguments consistently deflected to American crimes rather than defending Soviet "
        "actions on their own merits — a rhetorical pattern that signals a weak case. "
        "NEMESIS pinned AXIOM with concrete, specific evidence: engineered famine data, "
        "Gulag prisoner counts, the Lysenko affair, and the 1991 collapse as a final "
        "popular verdict. AXIOM's most persuasive moment — the WWII sacrifice argument — "
        "was strong, but a single heroic act does not redeem seven decades of political "
        "terror. NEMESIS wins on weight of evidence and logical consistency."
    ),
    "summary": (
        "A fierce 5-round debate on the Soviet Union's historical legacy. Pro argued "
        "industrialization, WWII sacrifice, and the pressure the USSR placed on Western "
        "labor rights. Con countered with the Gulag, the Holodomor, Lysenkoism, military "
        "invasions, and the 1991 popular rejection. Con wins by a clear margin."
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

def run_soviet_debate():
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
    run_soviet_debate()
