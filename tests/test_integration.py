"""
Full debate loop integration test — mocks the Anthropic API so no key is needed.
Verifies: orchestration flow, Judge routing, transcript saving, FIFO logging,
Gatekeeper token tracking, and final verdict parsing.
"""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import load_config
from src.core.gatekeeper import Gatekeeper
from src.core.logger import FIFOLogger
from src.core.watchdog import Watchdog
from src.agents.debater_agent import ProAgent, ConAgent
from src.agents.judge_agent import JudgeAgent


# ---------------------------------------------------------------------------
# Helpers — build fake Anthropic Message objects
# ---------------------------------------------------------------------------

def _fake_message(text: str, input_tokens: int = 50, output_tokens: int = 80):
    block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(
        content=[block],
        usage=usage,
        stop_reason="end_turn",
    )


PRO_RESPONSES = [
    json.dumps({
        "argument": (
            "Linux's package management system is unmatched. With apt, pacman, or dnf, "
            "developers install entire toolchains in seconds. On Windows you're still "
            "clicking through wizard installers in 2024. The WSL workaround proves that "
            "even Microsoft admits Linux is the superior dev environment."
        ),
        "references_used": ["https://distrowatch.com", "https://linuxfoundation.org"],
    }),
    json.dumps({
        "argument": (
            "NEMESIS claims Windows has better tooling support — that's flatly false. "
            "VS Code was built on Electron, runs identically on Linux, and the majority "
            "of cloud infrastructure runs on Linux. Deploying from a Linux dev machine "
            "means zero environment parity issues. Windows devs ship bugs caused by "
            "CRLF line endings and path separator nightmares."
        ),
        "references_used": ["https://stackexchange.com/dev-survey-2024"],
    }),
    json.dumps({
        "argument": (
            "The 'gaming' red herring NEMESIS throws out is irrelevant — we're debating "
            "SOFTWARE DEVELOPMENT, not gaming. 96.4% of the world's top 1 million servers "
            "run Linux. Every major cloud provider (AWS, GCP, Azure) defaults to Linux "
            "VMs. A developer who works on Linux is working in production-equivalent "
            "conditions from day one."
        ),
        "references_used": ["https://w3techs.com/technologies/overview/operating_system"],
    }),
    json.dumps({
        "argument": (
            "NEMESIS desperately pivots to 'driver support' — a solved problem since 2020. "
            "The Linux kernel now ships more hardware drivers than Windows. Docker runs "
            "natively on Linux without the performance overhead of Hyper-V. Git was written "
            "by Linus Torvalds FOR Linux. The entire open-source ecosystem is Linux-first."
        ),
        "references_used": ["https://kernel.org", "https://github.blog"],
    }),
    json.dumps({
        "argument": (
            "Final point: customization and control. On Linux you own your OS — no forced "
            "updates that break your build pipeline at 3am before a release. No telemetry "
            "siphoning your code to Microsoft servers. No licensing fees for CI/CD servers. "
            "Linux gives developers the sharp tool they deserve."
        ),
        "references_used": ["https://linuxfoundation.org/annual-report"],
    }),
]

CON_RESPONSES = [
    json.dumps({
        "argument": (
            "AXIOM's 'package manager' argument is 2010 nostalgia. Today, Windows has "
            "winget, Chocolatey, and Scoop — plus the entire .NET and Visual Studio "
            "ecosystem that powers enterprise development worldwide. The majority of "
            "Fortune 500 companies develop on Windows precisely because the tooling is "
            "mature, supported, and reliable."
        ),
        "references_used": ["https://docs.microsoft.com/winget", "https://chocolatey.org"],
    }),
    json.dumps({
        "argument": (
            "AXIOM cherry-picks server stats while ignoring desktop reality. Developers "
            "don't live in servers — they live in IDEs, design tools, and communication "
            "apps. Adobe Creative Suite, Microsoft Office native integration, Teams, "
            "Slack with full feature parity — all Windows-first. Linux desktop fragmentation "
            "means your devtools work differently on Ubuntu vs Fedora vs Arch."
        ),
        "references_used": ["https://jetbrains.com/developer-survey"],
    }),
    json.dumps({
        "argument": (
            "AXIOM's 'production parity' claim ignores Docker Desktop, which solved this "
            "problem entirely on Windows. Meanwhile Linux desktop gaming, Bluetooth "
            "reliability, and hardware driver support remain embarrassingly behind. "
            "A developer who can't use their full hardware is a hamstrung developer."
        ),
        "references_used": ["https://store.steampowered.com/linux"],
    }),
    json.dumps({
        "argument": (
            "The 'forced updates' argument is FUD. Windows Update for Business gives "
            "enterprises full update scheduling control. And let's talk about Linux's "
            "real problem: documentation fragmentation. Every distro, every version, "
            "different answers on Stack Overflow. Windows documentation is centralized, "
            "versioned, and backed by a $3 trillion company's support team."
        ),
        "references_used": ["https://docs.microsoft.com", "https://learn.microsoft.com"],
    }),
    json.dumps({
        "argument": (
            "AXIOM's final 'telemetry' paranoia ignores that Windows telemetry can be "
            "disabled in Enterprise editions. Meanwhile, the average Linux developer spends "
            "hours per month on system maintenance that Windows handles automatically. "
            "Time is money. Windows maximizes developer productivity where it matters: "
            "shipping software."
        ),
        "references_used": ["https://docs.microsoft.com/privacy"],
    }),
]

JUDGE_ROUTE_RESPONSE = json.dumps({"route_to": "Con"})

JUDGE_VERDICT = json.dumps({
    "winner": "Pro",
    "reason": (
        "AXIOM consistently backed claims with verifiable server statistics and ecosystem "
        "data, while NEMESIS relied on enterprise anecdotes and 'solved problem' deflections. "
        "AXIOM's point about production environment parity was never convincingly refuted. "
        "The debate favored the Pro side on persuasive force and evidence quality."
    ),
    "score_pro": 78,
    "score_con": 65,
    "summary": (
        "A sharp 5-round debate on Linux vs Windows for software development. "
        "Pro argued infrastructure dominance and dev toolchain superiority. "
        "Con argued enterprise tooling and desktop productivity. Pro edged it."
    ),
})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_env(tmp_path):
    """Provides a temp log dir + shared infrastructure objects."""
    log_dir = str(tmp_path / "logs")
    logger = FIFOLogger(log_dir=log_dir, max_files=20, max_lines=500)
    gatekeeper = Gatekeeper(token_budget=150_000)
    watchdog = Watchdog(timeout_seconds=30, max_retries=3, logger=logger)
    return logger, gatekeeper, watchdog, tmp_path


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestDebateOrchestration:
    """Tests the full debate loop with mocked Anthropic API."""

    def _build_response_side_effect(self, responses: list, fallback: str):
        """Returns a side_effect function that cycles through response list."""
        call_count = {"n": 0}

        def side_effect(**kwargs):
            idx = min(call_count["n"], len(responses) - 1)
            call_count["n"] += 1
            return _fake_message(responses[idx])

        return side_effect

    @patch("anthropic.Anthropic")
    def test_full_debate_runs_5_pings(self, mock_anthropic_cls, tmp_env):
        logger, gatekeeper, watchdog, tmp_path = tmp_env

        # Wire up mock clients per agent
        pro_client = MagicMock()
        con_client = MagicMock()
        judge_client = MagicMock()

        pro_responses_iter = iter(PRO_RESPONSES)
        con_responses_iter = iter(CON_RESPONSES)
        judge_call_count = {"n": 0}

        def judge_side_effect(**kwargs):
            judge_call_count["n"] += 1
            # Last call is declare_winner
            if judge_call_count["n"] > 10:
                return _fake_message(JUDGE_VERDICT)
            return _fake_message(JUDGE_ROUTE_RESPONSE)

        pro_client.messages.create.side_effect = (
            lambda **kw: _fake_message(next(pro_responses_iter, PRO_RESPONSES[-1]))
        )
        con_client.messages.create.side_effect = (
            lambda **kw: _fake_message(next(con_responses_iter, CON_RESPONSES[-1]))
        )
        judge_client.messages.create.side_effect = judge_side_effect

        clients = iter([pro_client, con_client, judge_client])
        mock_anthropic_cls.side_effect = lambda **kw: next(clients)

        pro = ProAgent(gatekeeper, watchdog, logger)
        con = ConAgent(gatekeeper, watchdog, logger)
        judge = JudgeAgent(gatekeeper, watchdog, logger)

        transcript = []
        max_pings = 5

        # Ping 1: Pro opens
        pro_raw = pro.generate_response(
            f'The debate topic is: "Linux is superior to Windows for software development"\n'
            "You are arguing the PRO side. Open with your strongest argument."
        )
        pro_data = json.loads(pro_raw)
        pro_arg = pro_data["argument"]
        judge.observe("Pro", pro_arg)
        transcript.append({"ping": 1, "side": "Pro", "argument": pro_arg})

        for ping in range(1, max_pings + 1):
            con_raw = con.generate_response(
                f'Ping {ping}: The Pro side just argued:\n"{pro_arg}"\n\n'
                "Tear it apart and make your strongest counter-argument."
            )
            con_data = json.loads(con_raw)
            con_arg = con_data["argument"]
            judge.observe("Con", con_arg)
            transcript.append({"ping": ping, "side": "Con", "argument": con_arg})

            if ping == max_pings:
                break

            pro_raw = pro.generate_response(
                f'Ping {ping}: The Con side just argued:\n"{con_arg}"\n\n'
                "Refute it decisively."
            )
            pro_data = json.loads(pro_raw)
            pro_arg = pro_data["argument"]
            judge.observe("Pro", pro_arg)
            transcript.append({"ping": ping + 1, "side": "Pro", "argument": pro_arg})

        verdict = judge.declare_winner()

        # Save transcript
        out = tmp_path / "transcript_latest.json"
        with open(out, "w") as f:
            json.dump({
                "topic": "Linux is superior to Windows for software development",
                "transcript": transcript,
                "verdict": verdict,
            }, f, indent=2)

        # --- Assertions ---
        assert len(transcript) == 10, f"Expected 10 exchanges (5 pings per side), got {len(transcript)}"
        assert verdict["winner"] in ("Pro", "Con"), "Winner must be Pro or Con"
        assert verdict["winner"] != "Tie", "Judge cannot declare a tie"
        assert verdict["score_pro"] != verdict["score_con"], "Scores must differ"
        assert "reason" in verdict
        assert out.exists(), "Transcript file must be saved"

    @patch("anthropic.Anthropic")
    def test_all_pro_arguments_are_valid_json(self, mock_anthropic_cls, tmp_env):
        logger, gatekeeper, watchdog, _ = tmp_env
        client = MagicMock()
        client.messages.create.side_effect = (
            lambda **kw: _fake_message(PRO_RESPONSES[0])
        )
        mock_anthropic_cls.return_value = client

        pro = ProAgent(gatekeeper, watchdog, logger)
        raw = pro.generate_response("Argue the PRO side on Linux vs Windows.")
        data = json.loads(raw)
        assert "argument" in data
        assert "references_used" in data
        assert isinstance(data["references_used"], list)

    @patch("anthropic.Anthropic")
    def test_judge_verdict_has_no_tie(self, mock_anthropic_cls, tmp_env):
        logger, gatekeeper, watchdog, _ = tmp_env
        client = MagicMock()
        client.messages.create.return_value = _fake_message(JUDGE_VERDICT)
        mock_anthropic_cls.return_value = client

        judge = JudgeAgent(gatekeeper, watchdog, logger)
        judge.debate_transcript = [
            {"side": "Pro", "argument": PRO_RESPONSES[0]},
            {"side": "Con", "argument": CON_RESPONSES[0]},
        ]
        verdict = judge.declare_winner()
        assert verdict["winner"] in ("Pro", "Con")
        assert verdict["score_pro"] != verdict["score_con"]

    @patch("anthropic.Anthropic")
    def test_gatekeeper_tracks_tokens_across_agents(self, mock_anthropic_cls, tmp_env):
        logger, gatekeeper, watchdog, _ = tmp_env
        client = MagicMock()
        client.messages.create.return_value = _fake_message(
            PRO_RESPONSES[0], input_tokens=100, output_tokens=200
        )
        mock_anthropic_cls.return_value = client

        pro = ProAgent(gatekeeper, watchdog, logger)
        pro.generate_response("Argue the PRO side.")
        pro.generate_response("Refute the CON side.")

        assert gatekeeper.total_input_tokens == 200
        assert gatekeeper.total_output_tokens == 400
        assert gatekeeper.total_tokens == 600

    @patch("anthropic.Anthropic")
    def test_logger_creates_structured_entries(self, mock_anthropic_cls, tmp_env):
        logger, gatekeeper, watchdog, tmp_path = tmp_env
        client = MagicMock()
        client.messages.create.return_value = _fake_message(PRO_RESPONSES[0])
        mock_anthropic_cls.return_value = client

        pro = ProAgent(gatekeeper, watchdog, logger)
        pro.generate_response("Open argument.")

        log_files = list(Path(tmp_path / "logs").glob("debate_*.log"))
        assert len(log_files) >= 1
        with open(log_files[0]) as f:
            for line in f:
                entry = json.loads(line)
                assert "ts" in entry
                assert "level" in entry
                assert "source" in entry
                assert "msg" in entry

    @patch("anthropic.Anthropic")
    def test_debate_transcript_mutual_reference(self, mock_anthropic_cls, tmp_env):
        """Each Con prompt must contain the Pro argument (mutual reference enforced in routing)."""
        logger, gatekeeper, watchdog, _ = tmp_env
        captured_prompts = []

        def capture(**kwargs):
            msgs = kwargs.get("messages", [])
            for m in msgs:
                if m["role"] == "user":
                    captured_prompts.append(m["content"])
            return _fake_message(CON_RESPONSES[0])

        client = MagicMock()
        client.messages.create.side_effect = capture
        mock_anthropic_cls.return_value = client

        con = ConAgent(gatekeeper, watchdog, logger)
        pro_arg = json.loads(PRO_RESPONSES[0])["argument"]
        con.generate_response(
            f'Ping 1: The Pro side just argued:\n"{pro_arg}"\n\n'
            "Tear it apart."
        )
        assert any(pro_arg[:50] in str(p) for p in captured_prompts), (
            "Con prompt must contain Pro's argument for mutual reference"
        )
