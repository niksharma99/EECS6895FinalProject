"""Generate frontend model-comparison data from completed run traces.

This intentionally recomputes summary numbers from trace JSON so it can handle
split runs such as GPT-5 mini's 26-trace partial + 4-trace continuation.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "runs"
OUT_PATH = REPO_ROOT / "frontend" / "public" / "model_scoreboard.json"
SCENARIOS_PATH = REPO_ROOT / "data" / "base_scenarios.jsonl"


MODEL_RUNS = [
    {
        "model_id": "llama3.2:3b",
        "display_name": "Llama 3.2 3B",
        "provider": "Ollama",
        "run_dirs": ["pilot30_csr_judge"],
        "notes": "Local baseline on the 30-scenario pilot.",
    },
    {
        "model_id": "claude-haiku-4-5",
        "display_name": "Claude Haiku 4.5",
        "provider": "Anthropic",
        "run_dirs": ["pilot30_proposer_claude_haiku45"],
        "notes": "Low-cost hosted Claude Proposer.",
    },
    {
        "model_id": "claude-sonnet-4-6",
        "display_name": "Claude Sonnet 4.6",
        "provider": "Anthropic",
        "run_dirs": ["pilot30_proposer_claude_sonnet46"],
        "notes": "SOTA-style Claude comparison run. Strongest contradiction-resistance in the 30-scenario pilot.",
    },
    {
        "model_id": "gpt-5-mini",
        "display_name": "GPT-5 mini",
        "provider": "OpenAI",
        "run_dirs": [
            "pilot30_proposer_openai_gpt5mini",
            "pilot30_proposer_openai_gpt5mini_remaining",
        ],
        "notes": "Low-cost hosted OpenAI Proposer. The 30-scenario run is merged from a 26-trace partial plus a 4-trace continuation.",
    },
]


def main() -> None:
    records = load_records()
    runs = [summarize_model_run(spec, records) for spec in MODEL_RUNS]
    payload = {
        "generated_from": [spec["run_dirs"] for spec in MODEL_RUNS],
        "scenario_count": 30,
        "scenario_ids": sorted({sid for run in runs for sid in run["scenario_ids"]}),
        "models": runs,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")


def load_records() -> dict[str, dict[str, Any]]:
    with SCENARIOS_PATH.open() as f:
        return {
            row["scenario_id"]: row
            for row in (json.loads(line) for line in f)
        }


def summarize_model_run(spec: dict[str, Any], records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    traces = load_traces(spec["run_dirs"])
    if len(traces) != 30:
        raise SystemExit(f"{spec['model_id']} has {len(traces)} traces, expected 30")

    scenario_metrics = {sid: trace["metrics"] for sid, trace in traces.items()}
    ruc_values = [m["ruc_score"] for m in scenario_metrics.values() if m.get("ruc_score") is not None]
    ds_values = [m["ds_score"] for m in scenario_metrics.values() if m.get("ds_score") is not None]
    csr_values = [1.0 if m.get("csr_flag") else 0.0 for m in scenario_metrics.values()]

    by_source: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "n": 0,
        "ruc": [],
        "ds": [],
        "csr": [],
        "flagged": 0,
    })
    contradiction_types: Counter[str] = Counter()
    flagged = []
    ambiguous = 0
    response_count = 0
    api_usage = empty_usage()
    timing = {
        "run_total_seconds": 0.0,
        "scenario_seconds": [],
        "proposer_seconds": [],
    }

    for sid, trace in sorted(traces.items()):
        record = records[sid]
        metrics = trace["metrics"]
        bucket = by_source[record["source"]]
        bucket["n"] += 1
        if metrics.get("ruc_score") is not None:
            bucket["ruc"].append(metrics["ruc_score"])
        if metrics.get("ds_score") is not None:
            bucket["ds"].append(metrics["ds_score"])
        bucket["csr"].append(1.0 if metrics.get("csr_flag") else 0.0)
        if metrics.get("csr_flag"):
            bucket["flagged"] += 1

        ctype = metrics.get("contradiction_type") or "none"
        contradiction_types[ctype] += 1
        if metrics.get("csr_flag"):
            flagged.append({
                "scenario_id": sid,
                "source": record["source"],
                "contradiction_type": ctype,
                "confidence": metrics.get("contradiction_confidence"),
                "description": metrics.get("contradiction_description"),
                "first_line": record["base_text"].split("\n", 1)[0][:200],
            })

        for response in collect_responses(trace):
            response_count += 1
            if response.get("ambiguous"):
                ambiguous += 1

        add_api_usage(api_usage, trace.get("api_usage") or {})
        t = trace.get("timing") or {}
        timing["scenario_seconds"].append(float(t.get("scenario_total_seconds", 0) or 0))
        timing["proposer_seconds"].append(
            float(t.get("base_proposer_seconds", 0) or 0)
            + float(t.get("perturbation_proposer_total_seconds", 0) or 0)
            + float(t.get("maieutic_proposer_total_seconds", 0) or 0)
        )

    flagged.sort(key=lambda item: -(item.get("confidence") or 0))
    return {
        "model_id": spec["model_id"],
        "display_name": spec["display_name"],
        "provider": spec["provider"],
        "run_dirs": spec["run_dirs"],
        "notes": spec["notes"],
        "scenario_ids": sorted(traces),
        "aggregate": {
            "n_scenarios": len(traces),
            "mean_ruc": mean(ruc_values),
            "mean_ds": mean(ds_values),
            "csr_rate": mean(csr_values),
        },
        "by_source": {
            source: {
                "n": data["n"],
                "mean_ruc": mean(data["ruc"]),
                "mean_ds": mean(data["ds"]),
                "csr_rate": mean(data["csr"]),
                "n_flagged": data["flagged"],
            }
            for source, data in sorted(by_source.items())
        },
        "contradiction_type_histogram": dict(contradiction_types),
        "flagged_scenarios": flagged,
        "parse": {
            "ambiguous": ambiguous,
            "total_responses": response_count,
            "ambiguity_rate": ambiguous / response_count if response_count else None,
        },
        "api_usage": api_usage,
        "timing": {
            "run_total_minutes": round(sum(timing["scenario_seconds"]) / 60, 3),
            "mean_scenario_seconds": mean(timing["scenario_seconds"]),
            "mean_proposer_seconds_per_scenario": mean(timing["proposer_seconds"]),
        },
    }


def load_traces(run_dirs: list[str]) -> dict[str, dict[str, Any]]:
    traces: dict[str, dict[str, Any]] = {}
    for run_dir in run_dirs:
        trace_dir = RUNS_DIR / run_dir / "traces"
        if not trace_dir.exists():
            raise SystemExit(f"missing trace directory: {trace_dir}")
        for path in trace_dir.glob("*.json"):
            traces[path.stem] = json.loads(path.read_text())
    return traces


def collect_responses(trace: dict[str, Any]) -> list[dict[str, Any]]:
    responses = [trace["base"]["response"]]
    responses.extend(item["response"] for item in trace.get("counterfactuals", []))
    responses.extend(item["response"] for item in trace.get("maieutic_dialogue", []))
    return responses


def empty_usage() -> dict[str, Any]:
    return {
        "by_agent": {},
        "overall": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
        },
    }


def add_api_usage(total: dict[str, Any], trace_usage: dict[str, Any]) -> None:
    for agent, payload in trace_usage.items():
        usage = (payload or {}).get("usage") or {}
        if not usage:
            continue
        bucket = total["by_agent"].setdefault(agent, {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
        })
        source = usage.get("cumulative") or usage
        requests = int(usage.get("requests", 1) or 1)
        bucket["requests"] += requests
        total["overall"]["requests"] += requests
        for key in ["input_tokens", "output_tokens", "total_tokens"]:
            value = int(source.get(key, 0) or 0)
            bucket[key] += value
            total["overall"][key] += value


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


if __name__ == "__main__":
    main()
