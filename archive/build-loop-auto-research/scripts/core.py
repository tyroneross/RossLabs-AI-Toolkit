from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


EXCLUDED_DIRS = {
    ".git",
    ".next",
    ".turbo",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
}

ENTRYPOINT_CANDIDATES = [
    "src/index.ts",
    "src/index.tsx",
    "src/main.ts",
    "src/main.tsx",
    "src/app.ts",
    "src/app.tsx",
    "src/index.js",
    "src/main.js",
    "app.py",
    "main.py",
    "manage.py",
    "src/lib.rs",
    "src/main.rs",
    "Package.swift",
]

PHASE_MARKERS = {
    "diagnose": [
        "check",
        "review",
        "audit",
        "assess",
        "investigate",
        "scan",
        "look through",
        "understand",
    ],
    "authorize": [
        "go for it",
        "do this",
        "continue",
        "implement",
        "build this",
        "proceed",
        "ship it",
    ],
    "verify": [
        "re-check",
        "recheck",
        "compare",
        "verify",
        "validate",
        "check latest",
        "audit again",
        "test this",
    ],
    "ship": [
        "commit",
        "push",
        "branch",
        "deploy",
        "release",
        "merge",
        "pr ",
        "pull request",
    ],
    "handoff": [
        "draft the plan",
        "step by step",
        "markdown",
        "copy paste",
        "handoff",
        "summarize",
        "what can you do vs what do i need to do",
    ],
}

TASK_MARKERS = {
    "product": ["product", "app", "platform", "workflow", "service"],
    "feature": ["feature", "add ", "support ", "enable ", "improve ", "versioning"],
    "algorithm": ["algorithm", "scoring", "ranking", "retrieval", "evaluation"],
    "prompt": ["prompt", "system prompt", "agent prompt", "instruction", "judge"],
    "bugfix": ["bug", "fix", "issue", "broken", "regression", "error"],
    "refactor": ["refactor", "cleanup", "restructure", "split", "migrate"],
}

STOPWORDS = {
    "about",
    "after",
    "against",
    "algorithm",
    "build",
    "building",
    "could",
    "feature",
    "into",
    "just",
    "make",
    "need",
    "please",
    "prompt",
    "repo",
    "should",
    "that",
    "this",
    "want",
    "with",
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def detect_phase(text: str) -> str | None:
    lowered = text.lower()
    scores: dict[str, int] = {}
    for phase, markers in PHASE_MARKERS.items():
        matched = [marker for marker in markers if marker in lowered]
        if matched:
            scores[phase] = len(matched)
    if not scores:
        return None
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0][0]


def collapse_phase_sequence(phases: list[str]) -> list[str]:
    collapsed: list[str] = []
    for phase in phases:
        merged = "ship_or_handoff" if phase in {"ship", "handoff"} else phase
        if not collapsed or collapsed[-1] != merged:
            collapsed.append(merged)
    return collapsed


def history_confidence(session_count: int, structured_inputs: int) -> str:
    if session_count >= 25 and structured_inputs >= 5:
        return "high"
    if session_count >= 10:
        return "medium"
    return "low"


def analyze_history_dir(history_dir: Path) -> dict[str, Any]:
    files = sorted(history_dir.glob("*.jsonl"))
    sessions = 0
    sessions_with_request_input = 0
    total_user_messages = 0
    total_request_input_answers = 0
    answer_lengths: list[int] = []
    phase_message_counts: Counter[str] = Counter()
    phase_marker_counts: dict[str, Counter[str]] = {
        phase: Counter() for phase in PHASE_MARKERS
    }
    loop_sequences: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []

    for file_path in files:
        rows = iter_jsonl(file_path)
        sessions += 1
        thread_name = file_path.stem
        user_messages: list[str] = []
        saw_request_input = False

        for row in rows:
            if row.get("type") == "session_meta":
                payload = row.get("payload", {})
                thread_name = payload.get("thread_name") or payload.get("id") or thread_name

            if row.get("type") == "event_msg" and row.get("payload", {}).get("type") == "user_message":
                message = normalize_whitespace(row.get("payload", {}).get("message", ""))
                if message:
                    user_messages.append(message)
                    phase = detect_phase(message)
                    if phase:
                        phase_message_counts[phase] += 1
                        lowered = message.lower()
                        for marker in PHASE_MARKERS[phase]:
                            if marker in lowered:
                                phase_marker_counts[phase][marker] += 1

            payload = row.get("payload", {})
            if row.get("type") == "response_item" and payload.get("type") == "function_call":
                if payload.get("name") == "request_user_input":
                    saw_request_input = True

            if row.get("type") == "response_item" and payload.get("type") == "function_call_output":
                output = payload.get("output")
                if isinstance(output, str) and output.startswith('{"answers"'):
                    parsed = json.loads(output)
                    for answer_block in parsed.get("answers", {}).values():
                        for answer in answer_block.get("answers", []):
                            total_request_input_answers += 1
                            answer_lengths.append(len(answer))

        total_user_messages += len(user_messages)
        if saw_request_input:
            sessions_with_request_input += 1

        phases = [detect_phase(message) for message in user_messages]
        filtered = [phase for phase in phases if phase]
        sequence = collapse_phase_sequence(filtered)
        if sequence:
            loop_sequences[" -> ".join(sequence)] += 1
            if len(samples) < 5 and len(sequence) >= 2:
                samples.append(
                    {
                        "thread": thread_name,
                        "sequence": sequence,
                        "first_message": user_messages[0][:160] if user_messages else "",
                        "last_message": user_messages[-1][:160] if user_messages else "",
                    }
                )

    avg_answer_length = round(sum(answer_lengths) / len(answer_lengths), 1) if answer_lengths else 0.0
    dominant_loop = loop_sequences.most_common(1)[0][0] if loop_sequences else "insufficient data"
    marker_summary = {
        phase: counter.most_common(5) for phase, counter in phase_marker_counts.items() if counter
    }
    sample_size_confidence = history_confidence(sessions, sessions_with_request_input)
    input_style_confidence = history_confidence(sessions_with_request_input, total_request_input_answers)

    return {
        "history_dir": str(history_dir),
        "sessions": sessions,
        "sessions_with_request_input": sessions_with_request_input,
        "total_user_messages": total_user_messages,
        "total_request_input_answers": total_request_input_answers,
        "avg_request_input_answer_length": avg_answer_length,
        "dominant_loop": dominant_loop,
        "phase_message_counts": dict(phase_message_counts.most_common()),
        "phase_marker_counts": marker_summary,
        "loop_sequences": loop_sequences.most_common(5),
        "samples": samples,
        "sample_size_confidence": sample_size_confidence,
        "input_style_confidence": input_style_confidence,
    }


def render_history_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# History Analysis",
        "",
        "## Bottom line",
        f"- Dominant loop: `{summary['dominant_loop']}`",
        f"- Sessions scanned: `{summary['sessions']}`",
        f"- Structured input evidence: `{summary['sessions_with_request_input']}` sessions with `request_user_input`",
        "",
        "## Strongest cues",
    ]
    for phase, markers in summary["phase_marker_counts"].items():
        marker_text = ", ".join(f"`{marker}` ({count})" for marker, count in markers)
        lines.append(f"- {phase}: {marker_text}")

    lines.extend(
        [
            "",
            "## Confidence",
            f"- Sample-size confidence: `{summary['sample_size_confidence']}`",
            f"- Structured-input confidence: `{summary['input_style_confidence']}`",
            f"- Average request-input answer length: `{summary['avg_request_input_answer_length']}`",
            "",
            "## Sample threads",
        ]
    )

    for sample in summary["samples"]:
        lines.append(
            f"- `{sample['thread']}`: {' -> '.join(sample['sequence'])} | first: {sample['first_message']}"
        )

    lines.extend(
        [
            "",
            "## Workflow implications",
            "- Lead with diagnosis and repo understanding.",
            "- Keep authorization friction low once the path is clear.",
            "- Add an explicit verification pass before ship or handoff.",
            "- Treat structured-input preferences as low confidence unless a larger corpus is provided.",
        ]
    )
    return "\n".join(lines)


def classify_task(text: str) -> str:
    lowered = text.lower()
    scores: Counter[str] = Counter()
    for task_type, markers in TASK_MARKERS.items():
        for marker in markers:
            if marker in lowered:
                scores[task_type] += 1
    if not scores:
        return "feature"
    return scores.most_common(1)[0][0]


def infer_mode(text: str, default: str = "balanced") -> str:
    lowered = text.lower()
    if "--mode" in lowered:
        for mode in ("quick", "balanced", "max_accuracy"):
            if mode in lowered:
                return mode
    return default


def infer_artifact_mode(text: str, default: str = "research_plus_plan") -> str:
    lowered = text.lower()
    for value in ("research_only", "plan_only", "research_plus_plan"):
        if value in lowered:
            return value
    return default


def tokenize_focus(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())
    unique: list[str] = []
    for token in tokens:
        if token in STOPWORDS or token in unique:
            continue
        unique.append(token)
    return unique[:8]


def detect_repo_manifests(repo_path: Path) -> list[str]:
    manifests = []
    for filename in (
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
        "Package.swift",
        "tsconfig.json",
        "vercel.json",
    ):
        if (repo_path / filename).exists():
            manifests.append(filename)
    return manifests


def detect_project_kind(repo_path: Path, manifests: list[str]) -> str:
    kinds = []
    if "package.json" in manifests:
        kinds.append("node")
    if {"pyproject.toml", "requirements.txt", "setup.py"} & set(manifests):
        kinds.append("python")
    if "Cargo.toml" in manifests:
        kinds.append("rust")
    if "go.mod" in manifests:
        kinds.append("go")
    if "Package.swift" in manifests:
        kinds.append("apple")
    if len(kinds) > 1:
        return "mixed"
    if kinds:
        return kinds[0]
    return "generic"


def parse_validation_commands(repo_path: Path, manifests: list[str]) -> dict[str, str]:
    commands: dict[str, str] = {}
    package_json = repo_path / "package.json"
    if "package.json" in manifests and package_json.exists():
        package_data = json.loads(package_json.read_text())
        scripts = package_data.get("scripts", {})
        for key in ("test", "lint", "build", "typecheck", "check"):
            if key in scripts:
                commands[key] = f"npm run {key}"

    pyproject = repo_path / "pyproject.toml"
    if "pyproject.toml" in manifests and pyproject.exists() and tomllib is not None:
        data = tomllib.loads(pyproject.read_text())
        project = data.get("project", {})
        optional = project.get("optional-dependencies", {})
        if "test" not in commands:
            if (repo_path / "pytest.ini").exists() or "pytest" in json.dumps(optional).lower():
                commands["test"] = "pytest"
        if "lint" not in commands:
            if "ruff" in pyproject.read_text():
                commands["lint"] = "ruff check ."
        if "typecheck" not in commands and "mypy" in pyproject.read_text():
            commands["typecheck"] = "mypy ."

    if "requirements.txt" in manifests and "test" not in commands and (repo_path / "tests").exists():
        commands["test"] = "python3 -m unittest discover -s tests"

    if "Cargo.toml" in manifests:
        commands.setdefault("build", "cargo build")
        commands.setdefault("test", "cargo test")

    if "go.mod" in manifests:
        commands.setdefault("build", "go build ./...")
        commands.setdefault("test", "go test ./...")

    if "Package.swift" in manifests:
        commands.setdefault("build", "swift build")
        commands.setdefault("test", "swift test")

    return commands


def count_files(repo_path: Path, limit: int = 5000) -> Counter[str]:
    counter: Counter[str] = Counter()
    seen = 0
    for path in repo_path.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.is_file():
            counter[path.suffix or "[no_ext]"] += 1
            seen += 1
            if seen >= limit:
                break
    return counter


def probable_entrypoints(repo_path: Path) -> list[str]:
    hits = []
    for candidate in ENTRYPOINT_CANDIDATES:
        if (repo_path / candidate).exists():
            hits.append(candidate)
    return hits[:8]


def focus_hits(repo_path: Path, focus_text: str, max_hits: int = 12) -> list[str]:
    tokens = tokenize_focus(focus_text)
    if not tokens:
        return []

    rg_path = shutil.which("rg")
    if rg_path:
        pattern = "|".join(re.escape(token) for token in tokens)
        result = subprocess.run(
            [rg_path, "-n", "-S", pattern, str(repo_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        hits = [line for line in result.stdout.splitlines() if line]
        return hits[:max_hits]

    hits: list[str] = []
    for path in repo_path.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.parts) or not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".toml"}:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        lowered = text.lower()
        if any(token in lowered for token in tokens):
            hits.append(str(path.relative_to(repo_path)))
            if len(hits) >= max_hits:
                break
    return hits


def scan_repo(repo_path: Path, focus_text: str = "") -> dict[str, Any]:
    manifests = detect_repo_manifests(repo_path)
    commands = parse_validation_commands(repo_path, manifests)
    top_dirs = [
        path.name
        for path in sorted(repo_path.iterdir())
        if path.is_dir() and path.name not in EXCLUDED_DIRS and not path.name.startswith(".")
    ][:12]
    counts = count_files(repo_path)
    return {
        "repo_path": str(repo_path),
        "project_kind": detect_project_kind(repo_path, manifests),
        "manifests": manifests,
        "top_level_dirs": top_dirs,
        "top_file_types": counts.most_common(8),
        "entrypoints": probable_entrypoints(repo_path),
        "validation_commands": commands,
        "focus_hits": focus_hits(repo_path, focus_text),
    }


def infer_integration_topics(repo_path: Path, repo_summary: dict[str, Any], task_text: str) -> list[str]:
    lowered = task_text.lower()
    topics: list[str] = []

    if any(word in lowered for word in ("api", "apis", "sdk", "integration", "webhook", "endpoint")):
        topics.append("api")
    if any(word in lowered for word in ("auth", "login", "oauth", "session", "token", "clerk", "auth0")):
        topics.append("auth")
    if any(word in lowered for word in ("payment", "payments", "stripe", "billing", "subscription", "checkout")):
        topics.append("payments")
    if (repo_path / "vercel.json").exists() or any(
        name in repo_summary.get("manifests", []) for name in ("package.json",)
    ):
        package_json = repo_path / "package.json"
        if package_json.exists() and '"next"' in package_json.read_text():
            topics.append("vercel")
    if repo_summary.get("project_kind") == "apple" or list(repo_path.glob("*.xcodeproj")):
        topics.append("apple")

    unique: list[str] = []
    for topic in topics:
        if topic not in unique:
            unique.append(topic)
    return unique


def build_integration_checks(topics: list[str]) -> list[str]:
    checks = [
        "- Verify cross-file and cross-service handoffs before accepting the plan.",
        "- Confirm data contracts, state transfer, and ownership boundaries at each integration point.",
    ]
    if "api" in topics:
        checks.extend(
            [
                "- Check request/response contracts, retries, idempotency, and timeout behavior.",
                "- Verify error handling and fallback behavior at client/server boundaries.",
            ]
        )
    if "auth" in topics:
        checks.extend(
            [
                "- Verify token, cookie, or session handoff across login, refresh, logout, and protected routes.",
                "- Check secrets, redirect URIs, callback handling, and deployment-specific auth behavior.",
            ]
        )
    if "payments" in topics:
        checks.extend(
            [
                "- Verify checkout, webhook, entitlement, and refund / retry handoffs end to end.",
                "- Confirm that payment failures degrade cleanly without breaking core user flows.",
            ]
        )
    return checks


def build_documentation_checks(topics: list[str]) -> list[str]:
    checks = [
        "- For every integration, verify both the tool/provider documentation and the deployment/runtime documentation.",
    ]
    if "api" in topics:
        checks.append(
            "- For APIs and SDKs, verify the provider docs plus the runtime/platform docs that affect limits, auth, env vars, and networking."
        )
    if "auth" in topics:
        checks.append(
            "- For auth, verify the auth provider docs plus deployment/runtime docs for cookies, callbacks, secrets, and session persistence."
        )
    if "payments" in topics:
        checks.append(
            "- For payments, verify the payment provider docs plus deployment/runtime docs for webhooks, retries, background jobs, and secret storage."
        )
    if "vercel" in topics:
        checks.append(
            "- Check Vercel docs for env vars, function/runtime limits, webhooks, cron behavior, and edge vs node constraints."
        )
    if "apple" in topics:
        checks.append(
            "- Check Apple platform docs for capabilities, entitlements, sign-in flows, permissions, and deployment constraints."
        )
    return checks


def confidence_bucket(score: int) -> str:
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def build_confidence_report(
    repo_summary: dict[str, Any],
    mode: str,
    task_type: str,
    include_external: bool,
) -> dict[str, str]:
    context_score = 0
    verification_score = 0
    evidence_score = 0

    if repo_summary.get("manifests"):
        context_score += 1
        evidence_score += 1
    if repo_summary.get("entrypoints"):
        context_score += 1
    if repo_summary.get("focus_hits"):
        context_score += 2
        evidence_score += 1
    if repo_summary.get("validation_commands"):
        verification_score += 3
        evidence_score += 1
    else:
        verification_score += 1

    if include_external:
        evidence_score += 1
    if mode == "max_accuracy":
        verification_score += 1

    novelty_risk = "high" if task_type in {"product", "algorithm"} else "medium"
    if task_type in {"bugfix", "refactor"}:
        novelty_risk = "low"

    report = {
        "Context coverage": confidence_bucket(context_score),
        "Verification coverage": confidence_bucket(verification_score),
        "Novelty risk": novelty_risk,
        "Evidence quality": confidence_bucket(evidence_score),
    }

    low_count = sum(
        1
        for key, value in report.items()
        if key != "Novelty risk" and value == "low"
    )
    component_values = [
        report["Context coverage"],
        report["Verification coverage"],
        report["Evidence quality"],
    ]
    overall = "high"
    if low_count >= 2 or report["Context coverage"] == "low":
        overall = "low"
    elif low_count >= 1 or novelty_risk == "high" or any(value != "high" for value in component_values):
        overall = "medium"
    report["Overall confidence"] = overall
    return report


def build_confidence_actions(confidence: dict[str, str]) -> list[str]:
    overall = confidence["Overall confidence"]
    if overall == "high":
        return [
            "- Spot-check at least one critical assumption before treating the packet as final.",
            "- Re-calibrate confidence downward if the spot check fails or uncovers hidden complexity.",
        ]
    if overall == "medium":
        return [
            "- Iterate on the weakest low/medium areas before accepting the packet.",
            "- Re-run the confidence check after refining the plan, docs, or verification path.",
        ]
    return [
        "- Do another repo/documentation pass before accepting the packet.",
        "- Reduce scope, simplify the approach, or gather missing evidence, then re-calibrate confidence.",
    ]


def build_research_packet(
    task_text: str,
    repo_path: Path,
    mode: str = "balanced",
    artifact_mode: str = "research_plus_plan",
    history_summary: dict[str, Any] | None = None,
) -> str:
    task = normalize_whitespace(task_text)
    task_type = classify_task(task)
    repo_summary = scan_repo(repo_path, focus_text=task)
    include_external = mode in {"balanced", "max_accuracy"} and task_type in {
        "product",
        "algorithm",
        "prompt",
        "feature",
    }
    confidence = build_confidence_report(repo_summary, mode, task_type, include_external)
    confidence_actions = build_confidence_actions(confidence)
    integration_topics = infer_integration_topics(repo_path, repo_summary, task)
    integration_checks = build_integration_checks(integration_topics)
    documentation_checks = build_documentation_checks(integration_topics)

    findings = [
        f"project kind: `{repo_summary['project_kind']}`",
        f"manifests: `{', '.join(repo_summary['manifests']) or 'none detected'}`",
        f"entrypoints: `{', '.join(repo_summary['entrypoints']) or 'not obvious yet'}`",
        f"validation commands: `{', '.join(f'{k}={v}' for k, v in repo_summary['validation_commands'].items()) or 'none detected'}`",
    ]
    if repo_summary["focus_hits"]:
        findings.append("focus hits:\n  - " + "\n  - ".join(repo_summary["focus_hits"][:6]))

    best_path = [
        f"Use `{mode}` mode with repo-first grounding before making build recommendations.",
        "Read at least two relevant files from the focus-hit set before finalizing the plan.",
        "Design the verification path before any implementation work begins.",
        "Prefer the simplest implementation that meaningfully improves user experience without degrading another UX factor.",
        "Prefer building with existing app code and tools before adding a new library.",
    ]
    if include_external:
        best_path.append(
            "Add selective external research from primary sources only if the recommendation depends on current framework, model, or benchmark behavior."
        )
    else:
        best_path.append("Skip external research unless the user explicitly asks for it or a current fact becomes blocking.")

    why_path = [
        "Repo-aware retrieval improves multi-file planning quality over single-file reasoning.",
        "Tool-using and verification-first flows reduce overconfident first-pass recommendations.",
        "A short self-debug pass catches weak assumptions before handoff.",
        "A simplicity gate keeps recommendations focused on user value rather than architectural novelty.",
    ]

    verification = []
    if repo_summary["validation_commands"]:
        verification.extend(
            f"- Run `{command}`" for command in repo_summary["validation_commands"].values()
        )
    else:
        verification.extend(
            [
                "- Create smoke tests or assertions for the critical path.",
                "- Define a manual verification checklist with exact expected outcomes.",
            ]
        )
    if mode == "max_accuracy":
        verification.append("- Add a final draft -> explain -> critique -> revise pass before shipping the plan.")
    verification.append("- Check each recommendation for unnecessary complexity and for any user-experience regression.")

    risks = [
        "- Repo scan is heuristic and may miss non-standard entrypoints.",
        "- External findings are not collected by the local script; they must be added by the command flow when needed.",
        "- Confidence should drop if the task depends on hidden operational context not present in the repo.",
        "- Any recommendation that needs a new library should remain provisional until a simpler in-app option is ruled out.",
    ]
    if history_summary:
        risks.append(
            f"- History profile confidence is `{history_summary['sample_size_confidence']}`, so behavior tuning should stay lightweight."
        )

    next_action = "Run focused reads on the highest-signal files and finalize the implementation plan."
    if artifact_mode == "research_only":
        next_action = "Use this packet to decide whether deeper planning or implementation is warranted."
    elif artifact_mode == "plan_only":
        next_action = "Convert the packet into the smallest decision-complete implementation plan needed for execution."

    history_line = ""
    if history_summary:
        history_line = (
            f"\n- History-informed default loop: `{history_summary['dominant_loop']}`"
        )

    confidence_lines = "\n".join(
        f"- {label}: `{value}`" for label, value in confidence.items()
    )

    plan_steps = [
        "Clarify the goal and success condition in one sentence.",
        "Confirm the target repo area using the focus-hit shortlist.",
        "Read the core implementation files and adjacent tests or validators.",
        "Draft the recommended approach with dependencies, risks, and validation steps.",
        "Run the simplicity + UX gate before accepting the approach.",
        "Check the integration points and handoffs before implementation starts.",
        "If the task is high novelty or externally dependent, add targeted primary-source research before finalizing.",
    ]

    handoff_prompt = (
        "Use the attached research packet as the source of truth. "
        "Start with repo grounding, keep the output answer-first, preserve the verification plan, prefer the simplest viable path, and avoid adding new libraries unless clearly justified."
    )

    sections = [
        "# Research Packet",
        "",
        "## Bottom line",
        f"- Task type: `{task_type}`",
        f"- Recommended optimization mode: `{mode}`",
        f"- Artifact mode: `{artifact_mode}`",
        f"- Recommended path: repo-first planning with explicit verification{history_line}",
        "",
        "## What I found",
        *[f"- {item}" for item in findings],
        "",
        "## External findings",
        "- Not collected by the local script.",
        "- In `balanced` and `max_accuracy` mode, add only primary-source research when current external facts materially affect the plan.",
        "",
        "## Best path",
        *[f"- {item}" for item in best_path],
        "",
        "## Why this path",
        *[f"- {item}" for item in why_path],
        "",
        "## Verification plan",
        *verification,
        "",
        "## Integration points / handoffs",
        *integration_checks,
        "",
        "## Documentation checks",
        *documentation_checks,
        "",
        "## Simplicity + UX gate",
        "- Does this recommendation make the product faster, more accurate, smoother, or simpler?",
        "- Does it avoid degrading another experience factor?",
        "- Is this the simplest path that works?",
        "- Can this be built before adding a new library?",
        "",
        "## Risks / unknowns",
        *risks,
        "",
        "## Confidence report",
        confidence_lines,
        "",
        "## Confidence action",
        *confidence_actions,
        "",
        "## Plan.md",
        *[f"{index}. {step}" for index, step in enumerate(plan_steps, start=1)],
        "",
        "## Handoff prompt.md",
        "```text",
        handoff_prompt,
        "```",
        "",
        "## Next action",
        f"- {next_action}",
    ]
    return "\n".join(sections)


def detect_autoresearch_targets(repo_path: Path, repo_summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Auto-detect potential autoresearch optimization targets in a repo.

    Detection rules:
    - If package.json has a 'build' script → optimize-build target
    - If package.json has a 'test' script → optimize-tests target
    - If pytest/unittest detected → optimize-tests target
    - If skills/*.md or prompts/ exist → optimize-prompt target
    - If docs/ exists → optimize-docs target

    Returns:
        List of dicts with keys: target, scope, metric_cmd, guard_cmd, budget.
    """
    targets: list[dict[str, Any]] = []
    manifests = repo_summary.get("manifests", [])
    validation_commands = repo_summary.get("validation_commands", {})

    # --- optimize-build (Node) ---
    if "package.json" in manifests:
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                pkg = json.loads(package_json.read_text())
                scripts = pkg.get("scripts", {})
                if "build" in scripts:
                    targets.append(
                        suggest_metric_for_target("optimize-build", repo_summary)
                        | {"target": "optimize-build", "scope": "src/**/*"}
                    )
                if "test" in scripts:
                    targets.append(
                        suggest_metric_for_target("optimize-tests", repo_summary)
                        | {"target": "optimize-tests", "scope": "src/**/*"}
                    )
            except (json.JSONDecodeError, OSError):
                pass

    # --- optimize-tests (Python) ---
    has_pytest = (
        (repo_path / "pytest.ini").exists()
        or (repo_path / "pyproject.toml").exists()
        and "pytest" in (repo_path / "pyproject.toml").read_text(errors="ignore").lower()
    )
    has_unittest = (repo_path / "tests").exists() or (repo_path / "test").exists()
    if (has_pytest or has_unittest) and not any(t["target"] == "optimize-tests" for t in targets):
        targets.append(
            suggest_metric_for_target("optimize-tests", repo_summary)
            | {"target": "optimize-tests", "scope": "**/*.py"}
        )

    # --- optimize-prompt ---
    has_skills = any((repo_path / "skills").rglob("*.md")) if (repo_path / "skills").exists() else False
    has_prompts = (repo_path / "prompts").exists()
    if has_skills or has_prompts:
        scope = "skills/**/*.md" if has_skills else "prompts/**/*"
        targets.append(
            suggest_metric_for_target("optimize-prompt", repo_summary)
            | {"target": "optimize-prompt", "scope": scope}
        )

    # --- optimize-docs ---
    if (repo_path / "docs").exists():
        targets.append(
            suggest_metric_for_target("optimize-docs", repo_summary)
            | {"target": "optimize-docs", "scope": "docs/**/*"}
        )

    return targets


def suggest_metric_for_target(target_type: str, repo_summary: dict[str, Any]) -> dict[str, Any]:
    """Suggest metric_cmd, guard_cmd, and budget for a given target type.

    Uses validation_commands from repo_summary when available.

    Args:
        target_type: One of "optimize-build", "optimize-tests", "optimize-prompt", "optimize-docs".
        repo_summary: Output of scan_repo().

    Returns:
        Dict with keys: metric_cmd, guard_cmd, budget.
        (Does NOT include 'target' or 'scope' — those are added by the caller.)
    """
    validation = repo_summary.get("validation_commands", {})
    project_kind = repo_summary.get("project_kind", "generic")

    if target_type == "optimize-build":
        build_cmd = validation.get("build", "npm run build")
        # Metric: capture build time (seconds). Guard: build must succeed.
        return {
            "metric_cmd": f"time {build_cmd} 2>&1 | tail -1",
            "guard_cmd": build_cmd,
            "budget": 15,
        }

    if target_type == "optimize-tests":
        if project_kind == "python":
            test_cmd = validation.get("test", "pytest")
            return {
                "metric_cmd": f"{test_cmd} --tb=no -q 2>&1 | tail -1",
                "guard_cmd": test_cmd,
                "budget": 20,
            }
        # Node / generic
        test_cmd = validation.get("test", "npm test")
        return {
            "metric_cmd": f"time {test_cmd} 2>&1 | tail -1",
            "guard_cmd": test_cmd,
            "budget": 20,
        }

    if target_type == "optimize-prompt":
        # Prompt targets are evaluated by a custom scorer — provide a placeholder.
        return {
            "metric_cmd": "python3 scripts/score_prompt.py",
            "guard_cmd": None,
            "budget": 30,
        }

    if target_type == "optimize-docs":
        # Docs targets: word count or a custom scorer.
        return {
            "metric_cmd": "wc -w docs/**/*.md | tail -1 | awk '{print $1}'",
            "guard_cmd": None,
            "budget": 10,
        }

    # Fallback for unknown target types.
    test_cmd = validation.get("test", "")
    build_cmd = validation.get("build", "")
    guard = test_cmd or build_cmd or None
    return {
        "metric_cmd": f"time {guard} 2>&1 | tail -1" if guard else "echo 0",
        "guard_cmd": guard if guard else None,
        "budget": 15,
    }


def optimize_brief_text(raw_text: str) -> str:
    text = normalize_whitespace(raw_text)
    task_type = classify_task(text)
    suggested_mode = infer_mode(text)
    missing: list[str] = []

    lowered = text.lower()
    if "/" not in text and "repo" not in lowered and "path" not in lowered:
        missing.append("repo path or target codebase context")
    if not any(word in lowered for word in ("constraint", "deadline", "performance", "security", "cost", "latency")):
        missing.append("constraints or tradeoff priorities")
    if not any(word in lowered for word in ("test", "verify", "validation", "acceptance")):
        missing.append("verification or acceptance criteria")
    if not any(word in lowered for word in ("markdown", "plan", "brief", "report", "prompt", "artifact")):
        missing.append("desired output artifact")
    if "quick" not in lowered and "balanced" not in lowered and "max_accuracy" not in lowered:
        missing.append("desired effort / accuracy mode")
    if not any(word in lowered for word in ("faster", "accur", "smooth", "simple", "ux", "user experience")):
        missing.append("the exact user-experience improvement being targeted")

    bottom_line = f"Turn this into a `{task_type}` brief with a clear goal, repo context, verification path, and the simplest viable approach."
    sharpened = (
        f"Create a research-backed `{task_type}` packet for: {text} "
        "Ground it in the target repo first, then add only the minimum external research needed."
    )
    verification = [
        "- Define the success condition in one sentence.",
        "- List the commands, assertions, or manual checks that prove the result.",
        "- Call out unknowns that would reduce confidence before execution.",
        "- Add a simplicity check to confirm the approach does not introduce avoidable complexity.",
    ]
    handoff = (
        f"Build a `{task_type}` recommendation from this request. "
        "Start with repo grounding, keep the output answer-first, prefer existing app primitives before new libraries, and end with a concrete next action."
    )

    sections = [
        "# Optimized Brief",
        "",
        "## Bottom line",
        f"- {bottom_line}",
        "",
        "## Sharpened request",
        f"- {sharpened}",
        "",
        "## Missing assumptions",
    ]
    if missing:
        sections.extend(f"- {item}" for item in missing)
    else:
        sections.append("- No obvious gaps detected by the heuristic pass.")

    sections.extend(
        [
            "",
            "## Suggested mode",
            f"- `{suggested_mode}`",
            "",
            "## Simplicity + UX gate",
            "- State the exact UX improvement expected from the recommendation.",
            "- Reject paths that add complexity without clear user value.",
            "- Prefer building with existing app code before adding a dependency.",
            "",
            "## Verification plan",
            *verification,
            "",
            "## Handoff prompt",
            "```text",
            handoff,
            "```",
        ]
    )
    return "\n".join(sections)
