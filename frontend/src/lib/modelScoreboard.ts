import fs from "node:fs";
import path from "node:path";

export type ModelSourceSummary = {
  n: number;
  mean_ruc: number | null;
  mean_ds: number | null;
  csr_rate: number | null;
  n_flagged: number;
};

export type ModelFlaggedScenario = {
  scenario_id: string;
  source: string;
  contradiction_type: string | null;
  confidence: number | null;
  description: string | null;
  first_line: string;
};

export type ModelScore = {
  model_id: string;
  display_name: string;
  provider: string;
  run_dirs: string[];
  notes: string;
  scenario_ids: string[];
  aggregate: {
    n_scenarios: number;
    mean_ruc: number;
    mean_ds: number;
    csr_rate: number;
  };
  by_source: Record<string, ModelSourceSummary>;
  contradiction_type_histogram: Record<string, number>;
  flagged_scenarios: ModelFlaggedScenario[];
  parse: {
    ambiguous: number;
    total_responses: number;
    ambiguity_rate: number;
  };
  api_usage: {
    overall: {
      input_tokens: number;
      output_tokens: number;
      total_tokens: number;
      requests: number;
    };
    by_agent: Record<string, {
      input_tokens: number;
      output_tokens: number;
      total_tokens: number;
      requests: number;
    }>;
  };
  timing: {
    run_total_minutes: number;
    mean_scenario_seconds: number;
    mean_proposer_seconds_per_scenario: number;
  };
};

export type ModelScoreboard = {
  generated_from: string[][];
  scenario_count: number;
  scenario_ids: string[];
  models: ModelScore[];
};

export function loadModelScoreboard(): ModelScoreboard {
  const file = path.join(process.cwd(), "public", "model_scoreboard.json");
  return JSON.parse(fs.readFileSync(file, "utf-8")) as ModelScoreboard;
}
