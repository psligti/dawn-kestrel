"""Pydantic contracts for review agent output."""
from __future__ import annotations
from typing import List, Literal
import pydantic as pd


class Scope(pd.BaseModel):
    relevant_files: List[str]
    ignored_files: List[str] = pd.Field(default_factory=list)
    reasoning: str

    model_config = pd.ConfigDict(extra="forbid")


class Check(pd.BaseModel):
    name: str
    required: bool
    commands: List[str]
    why: str
    expected_signal: str | None = None

    model_config = pd.ConfigDict(extra="forbid")


class Skip(pd.BaseModel):
    name: str
    why_safe: str
    when_to_run: str

    model_config = pd.ConfigDict(extra="forbid")


class Finding(pd.BaseModel):
    id: str
    title: str
    severity: Literal["warning", "critical", "blocking"]
    confidence: Literal["high", "medium", "low"]
    owner: Literal["dev", "docs", "devops", "security"]
    estimate: Literal["S", "M", "L"]
    evidence: str
    risk: str
    recommendation: str
    suggested_patch: str | None = None

    model_config = pd.ConfigDict(extra="forbid")


class MergeGate(pd.BaseModel):
    decision: Literal["approve", "needs_changes", "block"]
    must_fix: List[str] = pd.Field(default_factory=list)
    should_fix: List[str] = pd.Field(default_factory=list)
    notes_for_coding_agent: List[str] = pd.Field(default_factory=list)

    model_config = pd.ConfigDict(extra="forbid")


class ReviewOutput(pd.BaseModel):
    agent: str
    summary: str
    severity: Literal["merge", "warning", "critical", "blocking"]
    scope: Scope
    checks: List[Check] = pd.Field(default_factory=list)
    skips: List[Skip] = pd.Field(default_factory=list)
    findings: List[Finding] = pd.Field(default_factory=list)
    merge_gate: MergeGate

    model_config = pd.ConfigDict(extra="forbid")
