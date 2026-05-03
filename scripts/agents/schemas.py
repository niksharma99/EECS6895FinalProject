"""Shared dataclasses for the Tier 0 agent runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


TaskFormat = Literal["binary_dilemma", "unary_judgment", "narrative_judgment"]
ExpectedBehavior = Literal["judgment_should_stay_same", "judgment_should_change"]


@dataclass
class ProposerResponse:
    judgment: str | None
    reasoning: str
    raw_text: str
    parse_method: str = "unparsed"
    ambiguous: bool = False


@dataclass
class Perturbation:
    perturbation_id: str
    perturbation_type: str
    morally_relevant: bool
    expected_behavior: ExpectedBehavior
    changed_fields: list[str]
    perturbed_text: str
    rationale: str


@dataclass
class CounterfactualResult:
    perturbation: Perturbation
    response: ProposerResponse
    consistent_with_base: bool | None


@dataclass
class MaieuticQuestion:
    turn: int
    question: str
    targeted_principle: str


@dataclass
class MaieuticTurn:
    question: MaieuticQuestion
    response: ProposerResponse


@dataclass
class ScenarioMetrics:
    ruc_score: float | None
    ds_score: float | None
    csr_flag: bool
    contradiction_description: str | None = None
    contradiction_type: str | None = None
    contradiction_confidence: float | None = None


@dataclass
class ScenarioTrace:
    scenario_id: str
    source: str
    task_format: TaskFormat
    proposer_model: str
    base: dict[str, Any]
    counterfactuals: list[CounterfactualResult] = field(default_factory=list)
    maieutic_dialogue: list[MaieuticTurn] = field(default_factory=list)
    api_usage: dict[str, Any] = field(default_factory=dict)
    timing: dict[str, Any] = field(default_factory=dict)
    metrics: ScenarioMetrics | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunConfig:
    run_id: str
    scenario_ids: list[str]
    proposer_model: str
    cost_tier: str
    counterfactual_model: str
    maieutic_model: str
    judge_model: str
    num_perturbations: int
    max_maieutic_turns: int
    seed: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
