"""Shared mock API responses for integration tests. Not a test file."""
import json

PRO_RESPONSES = [
    json.dumps({
        "argument": (
            "Linux's package management is unmatched. With apt, pacman, or dnf, "
            "developers install entire toolchains in seconds. On Windows you're still "
            "clicking through wizard installers. WSL proves Microsoft admits Linux is "
            "the superior dev environment."
        ),
        "references_used": ["https://linuxfoundation.org"],
    }),
    json.dumps({
        "argument": (
            "NEMESIS claims Windows has better tooling — flatly false. VS Code runs "
            "identically on Linux, and 96% of cloud infrastructure runs on Linux. "
            "Deploying from Linux means zero environment parity issues."
        ),
        "references_used": ["https://stackexchange.com/dev-survey-2024"],
    }),
    json.dumps({
        "argument": (
            "96.4% of the world's top 1 million servers run Linux. Every major cloud "
            "provider defaults to Linux VMs. A developer on Linux works in "
            "production-equivalent conditions from day one."
        ),
        "references_used": ["https://w3techs.com"],
    }),
    json.dumps({
        "argument": (
            "Docker runs natively on Linux without Hyper-V overhead. Git was written "
            "by Linus Torvalds FOR Linux. The entire open-source ecosystem is Linux-first."
        ),
        "references_used": ["https://kernel.org"],
    }),
    json.dumps({
        "argument": (
            "On Linux you own your OS — no forced updates breaking your build pipeline "
            "at 3am. No telemetry. No licensing fees for CI/CD servers. "
            "Linux gives developers the sharp tool they deserve."
        ),
        "references_used": ["https://linuxfoundation.org/annual-report"],
    }),
]

CON_RESPONSES = [
    json.dumps({
        "argument": (
            "AXIOM's 'package manager' argument is 2010 nostalgia. Windows has winget, "
            "Chocolatey, and Scoop — plus the .NET and Visual Studio ecosystem that "
            "powers enterprise development worldwide."
        ),
        "references_used": ["https://docs.microsoft.com/winget"],
    }),
    json.dumps({
        "argument": (
            "AXIOM cherry-picks server stats while ignoring desktop reality. Adobe Suite, "
            "Office native integration, Teams — all Windows-first. Linux desktop "
            "fragmentation means your devtools work differently on Ubuntu vs Arch."
        ),
        "references_used": ["https://jetbrains.com/developer-survey"],
    }),
    json.dumps({
        "argument": (
            "Docker Desktop solved the parity problem on Windows entirely. Meanwhile "
            "Linux desktop gaming and Bluetooth reliability remain embarrassingly behind."
        ),
        "references_used": ["https://store.steampowered.com/linux"],
    }),
    json.dumps({
        "argument": (
            "Windows Update for Business gives enterprises full scheduling control. "
            "Linux documentation is fragmented — every distro gives different answers. "
            "Windows docs are centralized and backed by a $3 trillion company."
        ),
        "references_used": ["https://docs.microsoft.com"],
    }),
    json.dumps({
        "argument": (
            "Windows telemetry can be disabled in Enterprise editions. The average Linux "
            "developer spends hours per month on system maintenance that Windows handles "
            "automatically. Time is money."
        ),
        "references_used": ["https://docs.microsoft.com/privacy"],
    }),
]

JUDGE_ROUTE_RESPONSE = json.dumps({"route_to": "Con"})

JUDGE_VERDICT = json.dumps({
    "winner": "Pro",
    "reason": (
        "AXIOM consistently backed claims with verifiable server statistics and ecosystem "
        "data. AXIOM's production environment parity point was never convincingly refuted."
    ),
    "score_pro": 78,
    "score_con": 65,
    "summary": "Pro edged it on infrastructure dominance and dev toolchain arguments.",
})
