"""
Autonomous multi-step task orchestrator for DS Code Agent.
Provides a higher-level planning and execution loop for complex goals.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .llm_client import LLMClient
from .orchestrator_schemas import CoderOutput, PlannerOutput, ReviewerOutput
from .tools_adapter import ToolsAdapter

# Load env variables if .env exists
load_dotenv()

# -----------------------------
# Configuration / Guardrails
# -----------------------------

MAX_PATCH_ATTEMPTS = 3
MAX_VERIFY_FAILURES = 2
MAX_OPEN_FILES = 6
MAX_DIFF_LINES = 200
MAX_NO_PROGRESS_STEPS = 2

AGENT_DIR = ".agent"
SESSION_FILE = f"{AGENT_DIR}/session.json"
PATCH_FILE = f"{AGENT_DIR}/patch.diff"
REPO_PROFILE_FILE = f"{AGENT_DIR}/repo_profile.json"

# -----------------------------
# State / session persistence
# -----------------------------

class State(str, Enum):
    INTAKE = "INTAKE"
    DISCOVER = "DISCOVER"
    RETRIEVE = "RETRIEVE"
    PLAN = "PLAN"
    PATCH = "PATCH"
    APPLY = "APPLY"
    VERIFY = "VERIFY"
    DIAGNOSE = "DIAGNOSE"
    DONE = "DONE"
    STOPPED = "STOPPED"


@dataclass
class Evidence:
    last_command: str = ""
    stderr_summary: str = ""
    stdout_summary: str = ""


@dataclass
class RepoProfile:
    language: str = "unknown"
    test_commands: List[str] = field(default_factory=list)
    lint_commands: List[str] = field(default_factory=list)
    build_commands: List[str] = field(default_factory=list)
    entrypoints: List[str] = field(default_factory=list)


@dataclass
class SessionState:
    repo_root: str = "."
    state: State = State.INTAKE
    goal: str = ""
    definition_of_done: List[str] = field(default_factory=list)

    # guardrail counters
    patch_attempts: int = 0
    verify_failures: int = 0
    no_progress_steps: int = 0

    # working set
    open_files: List[str] = field(default_factory=list)
    pinned_notes: List[str] = field(default_factory=list)
    evidence: Evidence = field(default_factory=Evidence)

    # change tracking
    last_diff: str = ""
    files_changed: List[str] = field(default_factory=list)

    repo_profile: RepoProfile = field(default_factory=RepoProfile)

    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        d = asdict(self)
        d["state"] = self.state.value
        return json.dumps(d, indent=2)

    @staticmethod
    def from_json(s: str) -> SessionState:
        d = json.loads(s)
        d["state"] = State(d["state"])
        if "evidence" in d:
            d["evidence"] = Evidence(**d["evidence"])
        else:
            d["evidence"] = Evidence()
        if "repo_profile" in d:
            d["repo_profile"] = RepoProfile(**d["repo_profile"])
        else:
            d["repo_profile"] = RepoProfile()
        return SessionState(**d)


def load_session() -> SessionState:
    Path(AGENT_DIR).mkdir(exist_ok=True)
    p = Path(SESSION_FILE)
    if p.exists():
        try:
            return SessionState.from_json(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return SessionState()


def save_session(st: SessionState) -> None:
    Path(AGENT_DIR).mkdir(exist_ok=True)
    Path(SESSION_FILE).write_text(st.to_json(), encoding="utf-8")


# -----------------------------
# Utility
# -----------------------------

def summarize(text: str, max_lines: int = 50) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    head = lines[: max_lines // 2]
    tail = lines[-max_lines // 2:]
    return "\n".join(head + ["... (truncated) ..."] + tail)


def diff_line_count(diff: str) -> int:
    return len((diff or "").splitlines())


def extract_paths_from_diff(diff: str) -> List[str]:
    paths = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            paths.append(line.replace("+++ b/", "").strip())
    return sorted(set(paths))


# -----------------------------
# Core orchestrator
# -----------------------------

class Orchestrator:
    def __init__(self, tools: ToolsAdapter, llm: LLMClient):
        self.tools = tools
        self.llm = llm

    def run(self, user_goal: str) -> SessionState:
        st = load_session()
        if st.state == State.INTAKE:
            st.goal = user_goal.strip()

        while st.state not in (State.DONE, State.STOPPED):
            self._enforce_guardrails(st)
            save_session(st)

            print(f"[*] State: {st.state.value}")

            if st.state == State.INTAKE:
                self._handle_intake(st)
            elif st.state == State.DISCOVER:
                self._handle_discover(st)
            elif st.state == State.RETRIEVE:
                self._handle_retrieve(st)
            elif st.state == State.PLAN:
                self._handle_plan(st)
            elif st.state == State.PATCH:
                self._handle_patch(st)
            elif st.state == State.APPLY:
                self._handle_apply(st)
            elif st.state == State.VERIFY:
                self._handle_verify(st)
            elif st.state == State.DIAGNOSE:
                self._handle_diagnose(st)
            else:
                st.state = State.STOPPED

        save_session(st)
        return st

    def _enforce_guardrails(self, st: SessionState) -> None:
        if st.patch_attempts >= MAX_PATCH_ATTEMPTS:
            st.audit_log.append({"event": "stop", "reason": "max_patch_attempts"})
            st.state = State.STOPPED
        if st.verify_failures >= MAX_VERIFY_FAILURES and st.state in (State.DIAGNOSE, State.PATCH, State.APPLY, State.VERIFY):
            st.audit_log.append({"event": "stop", "reason": "max_verify_failures"})
            st.state = State.STOPPED
        if len(st.open_files) > MAX_OPEN_FILES:
            st.open_files = st.open_files[:MAX_OPEN_FILES]

    def _handle_intake(self, st: SessionState) -> None:
        st.audit_log.append({"state": "INTAKE", "goal": st.goal})
        st.state = State.DISCOVER

    def _handle_discover(self, st: SessionState) -> None:
        st.audit_log.append({"state": "DISCOVER"})
        pyproject = self.tools.glob("**/pyproject.toml").get("paths", [])
        pkgjson = self.tools.glob("**/package.json").get("paths", [])
        rp = RepoProfile()

        if pyproject:
            rp.language = "python"
            rp.test_commands = ["pytest -q"]
            rp.lint_commands = ["ruff check ."]
        elif pkgjson:
            rp.language = "node"
            rp.test_commands = ["npm test"]
            rp.lint_commands = ["npm run lint"]
        else:
            rp.language = "unknown"

        st.repo_profile = rp
        self.tools.write_file(REPO_PROFILE_FILE, json.dumps(asdict(rp), indent=2))
        st.state = State.RETRIEVE

    def _handle_retrieve(self, st: SessionState) -> None:
        st.audit_log.append({"state": "RETRIEVE"})
        import re
        key_terms = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", st.goal)
        key_terms = list(dict.fromkeys(key_terms))[:10]

        matches = []
        for term in key_terms[:3]:
            res = self.tools.search_file_content(term, dir_path=".", include="**/*.py" if st.repo_profile.language == "python" else None, context=2)
            matches.extend(res.get("matches", []))

        files = []
        for m in matches:
            f = m["file"]
            if f not in files:
                files.append(f)
            if len(files) >= MAX_OPEN_FILES:
                break

        st.open_files = files
        st.state = State.PLAN

    def _handle_plan(self, st: SessionState) -> None:
        st.audit_log.append({"state": "PLAN"})
        file_snippets = []
        for fp in st.open_files:
            content = self.tools.read_file(fp, limit=200).get("content", "")
            file_snippets.append(f"FILE: {fp}\n{content}")

        prompt = (
            "You are the PLANNER for a terminal coding agent.\n"
            "Return STRICT JSON.\n"
            f"GOAL:\n{st.goal}\n\n"
            f"REPO_PROFILE:\n{json.dumps(asdict(st.repo_profile), indent=2)}\n\n"
            "OPEN_FILES_SNIPPETS:\n" + "\n\n".join(file_snippets[:MAX_OPEN_FILES]) + "\n"
        )

        raw = self.llm.call_planner(prompt)
        out = PlannerOutput.model_validate(raw)

        st.definition_of_done = out.definition_of_done
        st.open_files = out.files_to_open[:MAX_OPEN_FILES] if out.files_to_open else st.open_files
        st.state = State.PATCH

    def _handle_patch(self, st: SessionState) -> None:
        st.audit_log.append({"state": "PATCH"})
        st.patch_attempts += 1

        file_blobs = []
        for fp in st.open_files:
            content = self.tools.read_file(fp).get("content", "")
            file_blobs.append(f"FILE: {fp}\n{content}")

        prompt = (
            "You are the CODER for a terminal coding agent.\n"
            "You MUST output STRICT JSON.\n"
            "Rules:\n"
            "- Produce ONE atomic unified diff.\n"
            f"- Keep diff under {MAX_DIFF_LINES} lines.\n"
            "- Do not include commentary outside JSON.\n\n"
            f"GOAL:\n{st.goal}\n\n"
            f"DEFINITION_OF_DONE:\n{json.dumps(st.definition_of_done, indent=2)}\n\n"
            "CURRENT_FILES:\n" + "\n\n".join(file_blobs) + "\n"
        )

        raw = self.llm.call_coder(prompt)
        out = CoderOutput.model_validate(raw)

        if diff_line_count(out.diff) > MAX_DIFF_LINES:
            st.audit_log.append({"event": "diff_too_large", "lines": diff_line_count(out.diff)})
            st.state = State.DIAGNOSE
            return

        st.last_diff = out.diff
        st.files_changed = extract_paths_from_diff(out.diff)
        st.audit_log.append({"event": "diff_generated", "files_changed": st.files_changed, "summary": out.summary})
        st.state = State.APPLY

    def _handle_apply(self, st: SessionState) -> None:
        st.audit_log.append({"state": "APPLY"})
        self.tools.write_file(PATCH_FILE, st.last_diff)

        check = self.tools.run_shell_command(f"git apply --check {PATCH_FILE}")
        if check["exit_code"] != 0:
            st.evidence.last_command = check["command"]
            st.evidence.stderr_summary = summarize(check["stderr"])
            st.audit_log.append({"event": "apply_failed", "stderr": st.evidence.stderr_summary})
            st.state = State.DIAGNOSE
            return

        apply = self.tools.run_shell_command(f"git apply {PATCH_FILE}")
        if apply["exit_code"] != 0:
            st.evidence.last_command = apply["command"]
            st.evidence.stderr_summary = summarize(apply["stderr"])
            st.state = State.DIAGNOSE
            return

        st.state = State.VERIFY

    def _handle_verify(self, st: SessionState) -> None:
        st.audit_log.append({"state": "VERIFY"})
        cmds = st.repo_profile.test_commands or ["pytest -q"]
        cmd = cmds[0]
        res = self.tools.run_shell_command(cmd, description="Verify after patch")
        st.audit_log.append({"event": "verify_run", "command": cmd, "exit_code": res["exit_code"]})

        if res["exit_code"] == 0:
            st.state = State.DONE
            return

        st.verify_failures += 1
        st.evidence.last_command = cmd
        st.evidence.stderr_summary = summarize(res["stderr"])
        st.evidence.stdout_summary = summarize(res["stdout"])
        st.audit_log.append({"event": "verify_failed", "stderr": st.evidence.stderr_summary})
        st.state = State.DIAGNOSE

    def _handle_diagnose(self, st: SessionState) -> None:
        st.audit_log.append({"state": "DIAGNOSE"})

        prompt = (
            "You are the REVIEWER/DIAGNOSER.\n"
            "Return STRICT JSON.\n"
            "Goal:\n" + st.goal + "\n\n"
            "Last evidence:\n"
            f"COMMAND: {st.evidence.last_command}\n"
            f"STDERR:\n{st.evidence.stderr_summary}\n\n"
            f"Changed files: {st.files_changed}\n\n"
            "Rules:\n"
            "- If patch didn't apply, suggest smaller diff or rebase approach.\n"
            "- If tests failed, suggest the minimal next file(s) to open and the minimal patch approach.\n"
        )

        raw = self.llm.call_reviewer(prompt)
        out = ReviewerOutput.model_validate(raw)

        import re
        files = []
        for m in re.finditer(r"([A-Za-z0-9_\-./]+\.py):\d+", st.evidence.stderr_summary or ""):
            files.append(m.group(1))
        suggested = list(dict.fromkeys(files))[:MAX_OPEN_FILES]

        if suggested:
            st.open_files = (suggested + st.open_files)[:MAX_OPEN_FILES]

        st.no_progress_steps += 1
        if st.no_progress_steps > MAX_NO_PROGRESS_STEPS:
            st.audit_log.append({"event": "stop", "reason": "no_progress"})
            st.state = State.STOPPED
            return

        st.state = State.PATCH


# -----------------------------
# CLI
# -----------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: orchestrator.py \"<goal>\"", file=sys.stderr)
        sys.exit(1)

    goal = sys.argv[1]

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    # Use actual root of the project
    root_path = os.getcwd()

    tools = ToolsAdapter(root_path)
    llm = LLMClient(api_key=api_key)
    orch = Orchestrator(tools, llm)

    try:
        st = orch.run(goal)
        print("\n=== FINAL STATE ===")
        print(st.state.value)
        print("\n=== SUMMARY ===")
        print("Goal:", st.goal)
        print("Definition of Done:", st.definition_of_done)
    except Exception as e:
        print(f"Error during execution: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
