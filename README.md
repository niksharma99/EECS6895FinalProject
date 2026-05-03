# EECS6895FinalProject

Multi-agent stress testing of LLM ethical reasoning for EECS 6895.

## Current State

- Unified dataset complete: `data/base_scenarios.jsonl` with 180 records.
- Agent runtime complete: `scripts/agents/`.
- 30-scenario model comparison complete for:
  - `llama3.2:3b`
  - `claude-haiku-4-5`
  - `gpt-5-mini`
- Demo frontend complete under `frontend/`.

## Frontend

```bash
cd frontend
npm run dev
```

Open:

- `/dataset` — browse unified scenarios
- `/traces` — walk through demo traces
- `/scorecard` — aggregate scorecard with model selector
- `/models` — cross-model scoreboard

## Key Commands

```bash
python scripts/10_assemble_base_scenarios.py
python scripts/11_select_pilot_scenarios.py
python scripts/12_generate_model_scoreboard.py
```

See `PLAN.md` for the durable project plan, status, results, and changelog.

See `METRICS.md` for plain-language explanations of RuC, DS, and CSR with examples.
