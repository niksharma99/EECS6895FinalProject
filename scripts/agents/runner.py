"""Tier 0 runner for the multi-agent ethical stress-test pipeline.

Run from repo root:
    python -m scripts.agents.runner --limit 3
    python -m scripts.agents.runner --sample-per-format 2 --run-id smoke
"""

from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.agents.counterfactualist import OpenAICounterfactualist, TemplateCounterfactualist
from scripts.agents.judge import OpenAICSRJudge
from scripts.agents.maieutic_inquirer import OpenAIMaieuticInquirer, TemplateMaieuticInquirer
from scripts.agents.metrics import aggregate_metrics, compute_metrics, counterfactual_consistency
from scripts.agents.model_clients import (
    AnthropicProposerClient,
    HeuristicProposerClient,
    OllamaProposerClient,
    OpenAIProposerClient,
)
from scripts.agents.prompts import build_prompt
from scripts.agents.proposer import Proposer
from scripts.agents.schemas import CounterfactualResult, MaieuticTurn, RunConfig, ScenarioTrace


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "base_scenarios.jsonl"
RUNS_DIR = REPO_ROOT / "runs"


def load_records() -> list[dict]:
    with DATA_PATH.open() as f:
        return [json.loads(line) for line in f]


def select_records(
    rows: list[dict],
    scenario_ids: list[str] | None,
    scenario_ids_file: str | None,
    sample_per_format: int | None,
    limit: int | None,
    seed: int,
) -> list[dict]:
    if scenario_ids_file:
        with Path(scenario_ids_file).open() as f:
            payload = json.load(f)
        scenario_ids = payload["scenario_ids"]

    if scenario_ids:
        by_id = {r["scenario_id"]: r for r in rows}
        missing = [sid for sid in scenario_ids if sid not in by_id]
        if missing:
            raise SystemExit(f"Unknown scenario_id values: {missing}")
        return [by_id[sid] for sid in scenario_ids]

    rng = random.Random(seed)
    if sample_per_format:
        selected: list[dict] = []
        for task_format in ["binary_dilemma", "unary_judgment", "narrative_judgment"]:
            pool = [r for r in rows if r["task_format"] == task_format]
            selected.extend(rng.sample(pool, min(sample_per_format, len(pool))))
        return selected

    return rows[: limit or 3]


def run_scenario(record: dict, proposer: Proposer, cf_agent, maieutic_agent, csr_judge, num_perturbations: int, max_turns: int) -> ScenarioTrace:
    scenario_start = time.perf_counter()
    timing = {}
    if hasattr(proposer.client, "reset_usage"):
        proposer.client.reset_usage()

    base_prompt = build_prompt(record)
    t0 = time.perf_counter()
    base_response = proposer.answer(record)
    timing["base_proposer_seconds"] = round(time.perf_counter() - t0, 3)

    cf_results: list[CounterfactualResult] = []
    t0 = time.perf_counter()
    perturbations = cf_agent.generate(record, base_response, num_perturbations)
    timing["counterfactual_generation_seconds"] = round(time.perf_counter() - t0, 3)
    perturbation_proposer_seconds = []
    for perturbation in perturbations:
        t0 = time.perf_counter()
        response = proposer.answer(record, perturbation.perturbed_text)
        perturbation_proposer_seconds.append(round(time.perf_counter() - t0, 3))
        cf_results.append(
            CounterfactualResult(
                perturbation=perturbation,
                response=response,
                consistent_with_base=counterfactual_consistency(base_response, response),
            )
        )
    timing["perturbation_proposer_seconds"] = perturbation_proposer_seconds
    timing["perturbation_proposer_total_seconds"] = round(sum(perturbation_proposer_seconds), 3)

    maieutic_turns: list[MaieuticTurn] = []
    t0 = time.perf_counter()
    questions = maieutic_agent.generate(record, base_response, cf_results, max_turns)
    timing["maieutic_generation_seconds"] = round(time.perf_counter() - t0, 3)
    maieutic_proposer_seconds = []
    for question in questions:
        followup_text = (
            f"{record['base_text']}\n\n"
            f"Initial answer: {base_response.judgment}. {base_response.reasoning}\n\n"
            f"Follow-up question: {question.question}"
        )
        t0 = time.perf_counter()
        response = proposer.answer(record, followup_text)
        maieutic_proposer_seconds.append(round(time.perf_counter() - t0, 3))
        maieutic_turns.append(MaieuticTurn(question, response))
    timing["maieutic_proposer_seconds"] = maieutic_proposer_seconds
    timing["maieutic_proposer_total_seconds"] = round(sum(maieutic_proposer_seconds), 3)

    api_usage = {}
    if hasattr(proposer.client, "usage_summary"):
        proposer_usage = proposer.client.usage_summary()
        if proposer_usage:
            api_usage["proposer"] = {
                "model": proposer.model_id,
                "usage": proposer_usage,
            }
    if hasattr(cf_agent, "last_usage"):
        api_usage["counterfactualist"] = {
            "model": cf_agent.model_id,
            "usage": cf_agent.last_usage,
        }
    if hasattr(maieutic_agent, "last_usage"):
        api_usage["maieutic"] = {
            "model": maieutic_agent.model_id,
            "usage": maieutic_agent.last_usage,
        }
    csr_judgment = None
    if csr_judge is not None:
        t0 = time.perf_counter()
        csr_judgment = csr_judge.judge(record, base_response, cf_results, maieutic_turns)
        timing["csr_judge_seconds"] = round(time.perf_counter() - t0, 3)
        api_usage["csr_judge"] = {
            "model": csr_judge.model_id,
            "usage": csr_judge.last_usage,
            "judgment": csr_judgment,
        }
    else:
        timing["csr_judge_seconds"] = 0.0

    metrics = compute_metrics(base_response, cf_results, maieutic_turns, csr_judgment)
    timing["scenario_total_seconds"] = round(time.perf_counter() - scenario_start, 3)
    return ScenarioTrace(
        scenario_id=record["scenario_id"],
        source=record["source"],
        task_format=record["task_format"],
        proposer_model=proposer.model_id,
        base={
            "prompt": base_prompt,
            "response": base_response,
        },
        counterfactuals=cf_results,
        maieutic_dialogue=maieutic_turns,
        api_usage=api_usage,
        timing=timing,
        metrics=metrics,
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def main() -> None:
    run_start = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--sample-per-format", type=int, default=None)
    parser.add_argument("--scenario-ids", nargs="*", default=None)
    parser.add_argument("--scenario-ids-file", default=None)
    parser.add_argument("--num-perturbations", type=int, default=4)
    parser.add_argument("--max-maieutic-turns", type=int, default=2)
    parser.add_argument("--seed", type=int, default=4242)
    parser.add_argument("--counterfactualist", choices=["template", "openai"], default="template")
    parser.add_argument("--openai-counterfactual-model", default=None)
    parser.add_argument("--counterfactual-max-output-tokens", type=int, default=None)
    parser.add_argument("--counterfactual-max-retries", type=int, default=1)
    parser.add_argument("--proposer", choices=["heuristic", "ollama", "openai", "anthropic"], default="heuristic")
    parser.add_argument("--ollama-model", default=None)
    parser.add_argument("--ollama-base-url", default=None)
    parser.add_argument("--openai-proposer-model", default=None)
    parser.add_argument("--anthropic-proposer-model", default=None)
    parser.add_argument("--proposer-max-output-tokens", type=int, default=None)
    parser.add_argument("--openai-proposer-reasoning-effort", default=None)
    parser.add_argument("--maieutic", choices=["template", "openai"], default="template")
    parser.add_argument("--openai-maieutic-model", default=None)
    parser.add_argument("--maieutic-max-output-tokens", type=int, default=None)
    parser.add_argument("--csr-judge", choices=["heuristic", "openai"], default="heuristic")
    parser.add_argument("--openai-judge-model", default=None)
    parser.add_argument("--judge-max-output-tokens", type=int, default=None)
    args = parser.parse_args()

    run_id = args.run_id or datetime.now(timezone.utc).strftime("tier0_%Y%m%d_%H%M%S")
    rows = load_records()
    selected = select_records(
        rows,
        args.scenario_ids,
        args.scenario_ids_file,
        args.sample_per_format,
        args.limit,
        args.seed,
    )

    if args.proposer == "ollama":
        proposer = Proposer(OllamaProposerClient(model=args.ollama_model, base_url=args.ollama_base_url))
        proposer_tier = "ollama_local"
    elif args.proposer == "openai":
        proposer = Proposer(
            OpenAIProposerClient(
                model=args.openai_proposer_model,
                max_output_tokens=args.proposer_max_output_tokens,
                reasoning_effort=args.openai_proposer_reasoning_effort,
            )
        )
        proposer_tier = "openai_api"
    elif args.proposer == "anthropic":
        proposer = Proposer(
            AnthropicProposerClient(
                model=args.anthropic_proposer_model,
                max_output_tokens=args.proposer_max_output_tokens,
            )
        )
        proposer_tier = "anthropic_api"
    else:
        proposer = Proposer(HeuristicProposerClient())
        proposer_tier = "heuristic"

    if args.counterfactualist == "openai":
        cf_agent = OpenAICounterfactualist(
            model=args.openai_counterfactual_model,
            max_output_tokens=args.counterfactual_max_output_tokens,
            max_retries=args.counterfactual_max_retries,
        )
        cost_tier = f"tier_1_counterfactualist_openai__proposer_{proposer_tier}"
    else:
        cf_agent = TemplateCounterfactualist()
        cost_tier = f"tier_0__proposer_{proposer_tier}"
    if args.maieutic == "openai":
        maieutic_agent = OpenAIMaieuticInquirer(
            model=args.openai_maieutic_model,
            max_output_tokens=args.maieutic_max_output_tokens,
        )
    else:
        maieutic_agent = TemplateMaieuticInquirer()

    csr_judge = None
    judge_model = "deterministic-parser-v0 + heuristic-csr"
    if args.csr_judge == "openai":
        csr_judge = OpenAICSRJudge(
            model=args.openai_judge_model,
            max_output_tokens=args.judge_max_output_tokens,
        )
        judge_model = f"deterministic-parser-v0 + {csr_judge.model_id}"

    config = RunConfig(
        run_id=run_id,
        scenario_ids=[r["scenario_id"] for r in selected],
        proposer_model=proposer.model_id,
        cost_tier=cost_tier,
        counterfactual_model=cf_agent.model_id,
        maieutic_model=maieutic_agent.model_id,
        judge_model=judge_model,
        num_perturbations=args.num_perturbations,
        max_maieutic_turns=args.max_maieutic_turns,
        seed=args.seed,
    )

    run_dir = RUNS_DIR / run_id
    write_json(run_dir / "config.json", config.to_dict())

    traces: list[ScenarioTrace] = []
    for record in selected:
        trace = run_scenario(
            record,
            proposer,
            cf_agent,
            maieutic_agent,
            csr_judge,
            args.num_perturbations,
            args.max_maieutic_turns,
        )
        traces.append(trace)
        write_json(run_dir / "traces" / f"{record['scenario_id']}.json", trace.to_dict())

    summary = {
        "run_id": run_id,
        "config": config.to_dict(),
        "aggregate_metrics": aggregate_metrics([t.metrics for t in traces if t.metrics is not None]),
        "api_usage": aggregate_api_usage(traces),
        "timing": aggregate_timing(traces, time.perf_counter() - run_start),
        "scenario_metrics": {
            t.scenario_id: t.metrics.__dict__ if t.metrics else None
            for t in traces
        },
    }
    write_json(run_dir / "metrics.json", summary)
    print(json.dumps(summary["aggregate_metrics"], indent=2))
    if summary["api_usage"]:
        print(json.dumps(summary["api_usage"], indent=2))
    print(json.dumps(summary["timing"], indent=2))
    print(f"Wrote run artifacts to {run_dir.relative_to(REPO_ROOT)}")


def aggregate_api_usage(traces: list[ScenarioTrace]) -> dict:
    totals_by_agent = {}
    for trace in traces:
        for agent_name, payload in trace.api_usage.items():
            usage = (payload or {}).get("usage") or {}
            if not usage:
                continue
            totals = totals_by_agent.setdefault(agent_name, {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "requests": 0,
            })
            totals["requests"] += int(usage.get("requests", 1) or 1)
            token_source = usage.get("cumulative") or usage
            totals["input_tokens"] += int(token_source.get("input_tokens", 0) or 0)
            totals["output_tokens"] += int(token_source.get("output_tokens", 0) or 0)
            totals["total_tokens"] += int(token_source.get("total_tokens", 0) or 0)
    if not totals_by_agent:
        return {}
    overall = {
        "input_tokens": sum(v["input_tokens"] for v in totals_by_agent.values()),
        "output_tokens": sum(v["output_tokens"] for v in totals_by_agent.values()),
        "total_tokens": sum(v["total_tokens"] for v in totals_by_agent.values()),
        "requests": sum(v["requests"] for v in totals_by_agent.values()),
    }
    return {"by_agent": totals_by_agent, "overall": overall}


def aggregate_timing(traces: list[ScenarioTrace], run_total_seconds: float) -> dict:
    scenario_seconds = [
        float(t.timing.get("scenario_total_seconds", 0) or 0)
        for t in traces
    ]
    proposer_seconds = [
        float(t.timing.get("base_proposer_seconds", 0) or 0)
        + float(t.timing.get("perturbation_proposer_total_seconds", 0) or 0)
        + float(t.timing.get("maieutic_proposer_total_seconds", 0) or 0)
        for t in traces
    ]
    counterfactual_seconds = [
        float(t.timing.get("counterfactual_generation_seconds", 0) or 0)
        for t in traces
    ]
    return {
        "run_total_seconds": round(run_total_seconds, 3),
        "run_total_minutes": round(run_total_seconds / 60, 3),
        "scenario_count": len(traces),
        "mean_scenario_seconds": _mean(scenario_seconds),
        "max_scenario_seconds": round(max(scenario_seconds), 3) if scenario_seconds else None,
        "mean_proposer_seconds_per_scenario": _mean(proposer_seconds),
        "mean_counterfactual_seconds_per_scenario": _mean(counterfactual_seconds),
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


if __name__ == "__main__":
    main()
