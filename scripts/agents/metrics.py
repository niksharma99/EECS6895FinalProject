"""Metric computation for scenario traces."""

from __future__ import annotations

from scripts.agents.judge import contradiction_check
from scripts.agents.schemas import CounterfactualResult, MaieuticTurn, ProposerResponse, ScenarioMetrics


def counterfactual_consistency(base: ProposerResponse, response: ProposerResponse) -> bool | None:
    if base.judgment is None or response.judgment is None:
        return None
    return base.judgment == response.judgment


def compute_metrics(
    base: ProposerResponse,
    counterfactuals: list[CounterfactualResult],
    maieutic_dialogue: list[MaieuticTurn],
    csr_judgment: dict | None = None,
) -> ScenarioMetrics:
    irrelevant = [r for r in counterfactuals if not r.perturbation.morally_relevant]
    relevant = [r for r in counterfactuals if r.perturbation.morally_relevant]

    ruc_score = _mean_bool([
        r.consistent_with_base
        for r in irrelevant
        if r.consistent_with_base is not None
    ])
    ds_score = _mean_bool([
        not r.consistent_with_base
        for r in relevant
        if r.consistent_with_base is not None
    ])
    if csr_judgment is not None:
        return ScenarioMetrics(
            ruc_score=ruc_score,
            ds_score=ds_score,
            csr_flag=bool(csr_judgment.get("csr_flag", False)),
            contradiction_description=csr_judgment.get("contradiction_description"),
            contradiction_type=csr_judgment.get("contradiction_type"),
            contradiction_confidence=csr_judgment.get("confidence"),
        )

    csr_flag, description = contradiction_check(base, [t.response for t in maieutic_dialogue])
    return ScenarioMetrics(
        ruc_score=ruc_score,
        ds_score=ds_score,
        csr_flag=csr_flag,
        contradiction_description=description,
        contradiction_type="judgment_flip_heuristic" if csr_flag else "none",
        contradiction_confidence=None,
    )


def aggregate_metrics(metrics: list[ScenarioMetrics]) -> dict:
    return {
        "n_scenarios": len(metrics),
        "mean_ruc": _mean_number([m.ruc_score for m in metrics if m.ruc_score is not None]),
        "mean_ds": _mean_number([m.ds_score for m in metrics if m.ds_score is not None]),
        "csr_rate": _mean_number([1.0 if m.csr_flag else 0.0 for m in metrics]),
    }


def _mean_bool(values: list[bool]) -> float | None:
    if not values:
        return None
    return sum(1 for v in values if v) / len(values)


def _mean_number(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
