from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

class PlannerOutput(BaseModel):
    intent: str = Field(..., pattern=r"^(bugfix|feature|refactor|explain)$")
    definition_of_done: List[str]
    search_queries: List[str] = []
    files_to_open: List[str] = []
    commands_to_run: List[str] = []
    plan_steps: List[str]


class CoderOutput(BaseModel):
    summary: str
    diff: str
    verification: List[str] = []
    risk_notes: List[str] = []


class ReviewerOutput(BaseModel):
    looks_correct: bool
    issues: List[str] = []
    suggested_changes: List[str] = []
    verify_commands: List[str] = []
