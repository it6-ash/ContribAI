"""LLM-facing helpers: contribution planning, skill-gap narration, workspace chat.

Same contract as everywhere else — each function has a deterministic fallback so
nothing here can break the demo when the model is unavailable.
"""

from __future__ import annotations

import logging

from . import llm
from .models import Issue, User, UserSkill

log = logging.getLogger("contribai.agents")

_PLANNER_SYSTEM = """You write contribution plans for developers making their first
pull request to an unfamiliar open-source repository.

Return JSON: {"prerequisites": [...], "steps": [{"title", "objective", "command",
"expected", "common_failure"}]}

Rules:
- 8-11 steps, from reading the contribution guide through opening the pull request.
- "command" must be a real shell command or "" when the step is not a command.
  Only use commands justified by the repository data you were given. If setup
  commands are unknown, say so in "objective" and leave "command" empty rather
  than inventing a build system.
- "common_failure" is the mistake a newcomer actually makes at that step.
- Do NOT write the fix for the issue. Plan the contribution, not the patch.
- "prerequisites" are things to learn or install before starting; [] if none."""


def _generic_setup(repo) -> list[str]:
    if repo and repo.setup_commands:
        return list(repo.setup_commands)
    lang = (repo.language or "").lower() if repo else ""
    if lang == "python":
        return ["python -m venv .venv", "pip install -e .", "pytest"]
    if lang in ("typescript", "javascript"):
        return ["npm install", "npm test"]
    if lang == "go":
        return ["go mod download", "go test ./..."]
    if lang == "rust":
        return ["cargo build", "cargo test"]
    return []


def fallback_plan(issue: Issue, user: User, gaps: list[dict]) -> tuple[list[dict], list[str]]:
    repo = issue.repository
    slug = repo.full_name if repo else "the repository"
    setup = _generic_setup(repo)
    install = setup[0] if setup else ""
    test_cmd = setup[-1] if len(setup) > 1 else ""
    files = (issue.analysis.affected_files if issue.analysis else []) or []
    first_file = files[0] if files else "the relevant module"

    steps = [
        {
            "title": "Read the contribution guide",
            "objective": f"Learn how {slug} expects changes to be proposed."
            + ("" if repo and repo.has_contributing else " This repo has no CONTRIBUTING.md, so follow the README and recent merged PRs instead."),
            "command": "",
            "expected": "You know the branch naming, commit and PR conventions.",
            "common_failure": "Skipping this and getting the PR closed on process grounds.",
        },
        {
            "title": "Comment on the issue",
            "objective": "Say you intend to work on it, so two people don't duplicate effort.",
            "command": "",
            "expected": "A maintainer acknowledges, or nobody objects within a day or two.",
            "common_failure": "Disappearing after claiming an issue. Only claim what you'll start now.",
        },
        {
            "title": "Fork and clone",
            "objective": "Get a local copy you can push branches to.",
            "command": f"gh repo fork {slug} --clone" if repo else "",
            "expected": "A local directory with your fork as `origin` and upstream configured.",
            "common_failure": "Cloning upstream directly, then being unable to push.",
        },
        {
            "title": "Install dependencies",
            "objective": "Get the project running before you change anything.",
            "command": install,
            "expected": "Dependencies resolve without errors.",
            "common_failure": "Wrong language runtime version. Check the CI config for the version the project targets.",
        },
        {
            "title": "Run the existing test suite",
            "objective": "Establish a green baseline so you can tell your change apart from pre-existing breakage.",
            "command": test_cmd,
            "expected": "Tests pass, or you note which ones already fail on a clean checkout.",
            "common_failure": "Assuming a pre-existing failure was caused by you.",
        },
        {
            "title": "Reproduce the reported behaviour",
            "objective": "Confirm the issue is real and that you understand its trigger.",
            "command": "",
            "expected": "You can make the problem happen on demand.",
            "common_failure": "Starting to code before reproducing, then fixing the wrong thing.",
        },
        {
            "title": f"Read {first_file}",
            "objective": "Trace the code path named in the issue and find the root cause.",
            "command": "",
            "expected": "You can point at the specific line responsible.",
            "common_failure": "Patching the symptom at the call site instead of the shared cause.",
        },
        {
            "title": "Create a branch",
            "objective": "Keep the change isolated.",
            "command": f"git checkout -b fix/issue-{issue.number}",
            "expected": "You're on a new branch off an up-to-date default branch.",
            "common_failure": "Committing straight to main on your fork.",
        },
        {
            "title": "Implement the smallest change that fixes it",
            "objective": "Address the root cause without unrelated refactoring.",
            "command": "",
            "expected": "A focused diff a reviewer can read in one sitting.",
            "common_failure": "Bundling formatting changes, which buries the actual fix.",
        },
        {
            "title": "Add a regression test",
            "objective": "Prove the bug is fixed and stays fixed.",
            "command": "",
            "expected": "A test that fails on the old code and passes on yours.",
            "common_failure": "Writing a test that passes either way.",
        },
        {
            "title": "Run the full suite and open the PR",
            "objective": "Ship it, referencing the issue so maintainers can link the two.",
            "command": test_cmd,
            "expected": f"Green suite, then a PR whose description says 'Fixes #{issue.number}'.",
            "common_failure": "Only running your own test and breaking something else.",
        },
    ]

    prerequisites = [
        f"{gap['skill']}: roughly {gap['learning_hours']:.0f}h to reach a working level"
        for gap in gaps[:3]
    ]
    return steps, prerequisites


def contribution_plan(
    issue: Issue, user: User, gaps: list[dict]
) -> tuple[list[dict], list[str], str]:
    steps, prerequisites = fallback_plan(issue, user, gaps)
    repo = issue.repository
    analysis = issue.analysis

    prompt = f"""CONTRIBUTOR
Experience level: {user.experience_level}
Known skills: {', '.join(sorted({us.skill.name for us in user.skills})) if user.skills else 'unknown'}
Missing skills for this issue: {', '.join(g['skill'] for g in gaps) or 'none identified'}

REPOSITORY (fact)
{repo.full_name if repo else 'unknown'} — language {repo.language if repo else 'unknown'}
CONTRIBUTING.md present: {bool(repo and repo.has_contributing)}
Tests detected: {bool(repo and repo.has_tests)}
Known setup commands: {', '.join(repo.setup_commands) if repo and repo.setup_commands else 'unknown — do not invent any'}

ISSUE (fact)
#{issue.number} {issue.title}
{(issue.body or '')[:2000]}

ANALYSIS (inference)
Difficulty: {analysis.difficulty if analysis else 'unknown'}
Likely files: {', '.join(analysis.affected_files) if analysis and analysis.affected_files else 'unknown'}
Concepts: {', '.join(analysis.concepts) if analysis and analysis.concepts else 'unknown'}"""

    data = llm.complete_json(_PLANNER_SYSTEM, prompt, max_tokens=2200)
    if not data or not isinstance(data.get("steps"), list) or len(data["steps"]) < 5:
        return steps, prerequisites, "heuristic"

    cleaned = []
    for raw in data["steps"][:12]:
        if not isinstance(raw, dict) or not raw.get("title"):
            continue
        cleaned.append(
            {
                "title": str(raw.get("title", ""))[:120],
                "objective": str(raw.get("objective", ""))[:400],
                "command": str(raw.get("command", ""))[:200],
                "expected": str(raw.get("expected", ""))[:300],
                "common_failure": str(raw.get("common_failure", ""))[:300],
            }
        )
    if len(cleaned) < 5:
        return steps, prerequisites, "heuristic"

    llm_prereqs = data.get("prerequisites")
    if isinstance(llm_prereqs, list) and llm_prereqs:
        prerequisites = [str(p)[:200] for p in llm_prereqs][:5]
    return cleaned, prerequisites, "llm"


_CHAT_SYSTEM = """You are a contribution assistant embedded in a workspace for ONE
open-source issue. You help the contributor understand the issue and the repository.

Rules:
- Ground every answer in the supplied context. If the context does not contain the
  answer, say what you don't know and name the file or command that would tell them.
- Never invent file paths, function names, APIs or maintainer opinions.
- Do not write the patch for them. Point at the code, explain the mechanism, suggest
  what to verify. They do the engineering.
- Be concrete and brief. A senior engineer answering a colleague, not a tutorial."""


def workspace_chat(
    question: str, issue: Issue, user: User, user_skills: list[UserSkill], match: dict | None
) -> tuple[str, str]:
    repo = issue.repository
    analysis = issue.analysis
    if not llm.get_provider().available():
        return _fallback_answer(question, issue), "heuristic"

    context = f"""REPOSITORY (fact)
{repo.full_name if repo else 'unknown'} — {repo.description if repo else ''}
Language: {repo.language if repo else 'unknown'} | Stars: {repo.stars if repo else '?'}
CONTRIBUTING.md: {bool(repo and repo.has_contributing)} | Tests: {bool(repo and repo.has_tests)}
Setup commands on record: {', '.join(repo.setup_commands) if repo and repo.setup_commands else 'none recorded'}
Repository paths (sample): {', '.join((repo.tree or [])[:60]) if repo else 'unknown'}

ISSUE (fact)
#{issue.number} {issue.title}
Labels: {', '.join(issue.labels or []) or 'none'}
Body:
{(issue.body or '(empty)')[:3000]}
Comment excerpts: {' | '.join(str(c)[:300] for c in (issue.comment_samples or [])[:3]) or 'none'}

ANALYSIS (inference, may be wrong)
{analysis.summary if analysis else ''}
Likely files: {', '.join(analysis.affected_files) if analysis and analysis.affected_files else 'unknown'}
Concepts: {', '.join(analysis.concepts) if analysis and analysis.concepts else 'unknown'}
Open questions: {'; '.join(analysis.open_questions) if analysis and analysis.open_questions else 'none'}

CONTRIBUTOR
Skills: {', '.join(f"{us.skill.name} ({us.confidence:.0%})" for us in user_skills[:12]) or 'unknown'}
Missing for this issue: {', '.join(g['skill'] for g in (match or {}).get('skill_gaps', [])) or 'none identified'}

QUESTION
{question}"""

    answer = llm.complete_text(_CHAT_SYSTEM, context, max_tokens=900)
    if not answer:
        return _fallback_answer(question, issue), "heuristic"
    return answer.strip(), "llm"


def _fallback_answer(question: str, issue: Issue) -> str:
    analysis = issue.analysis
    files = (analysis.affected_files if analysis else []) or []
    lines = [
        "The AI assistant is not configured (no GROQ_API_KEY), so here is what "
        "the deterministic analysis already knows:",
        "",
        f"Issue: {issue.title}",
    ]
    if analysis:
        lines += [
            f"Difficulty: {analysis.difficulty} ({analysis.difficulty_basis})",
            f"Estimated effort: {analysis.estimated_hours_min:g} to {analysis.estimated_hours_max:g} hours",
        ]
        if analysis.concepts:
            lines.append(f"Concepts involved: {', '.join(analysis.concepts)}")
    if files:
        lines.append(f"Start by reading: {files[0]}")
        if len(files) > 1:
            lines.append(f"Then: {', '.join(files[1:3])}")
    else:
        lines.append(
            "No candidate files were identified. Grep the repository for terms from "
            "the issue title."
        )
    return "\n".join(lines)


def skill_gap_narrative(gaps: list[dict], matched: list[dict], readiness: dict) -> str:
    if not gaps:
        return (
            f"You're at {readiness.get('overall', 0):.0%} readiness with no missing core "
            "skills. The remaining unknown is this specific codebase, which you learn by "
            "reading it."
        )
    core = [g["skill"] for g in gaps if g["severity"] == "core"]
    supporting = [g["skill"] for g in gaps if g["severity"] != "core"]
    parts = [f"You're at {readiness.get('overall', 0):.0%} readiness for this issue."]
    if core:
        hours = sum(g["learning_hours"] for g in gaps if g["severity"] == "core")
        parts.append(
            f"The real gap is {', '.join(core)}: budget roughly {hours:.0f} hours to get "
            "to a working level, not mastery."
        )
    if supporting:
        parts.append(f"{', '.join(supporting)} you can pick up while working the issue.")
    parts.append("You don't need to know everything before starting. You need enough to start.")
    return " ".join(parts)
