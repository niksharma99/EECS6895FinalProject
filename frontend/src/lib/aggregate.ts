import fs from "node:fs";
import path from "node:path";

export type SourceSummary = {
  n: number;
  mean_ruc: number;
  mean_ds: number | null;
  csr_rate: number;
  n_flagged: number;
};

export type FlaggedScenario = {
  scenario_id: string;
  source: string;
  contradiction_type: string | null;
  confidence: number | null;
  description: string | null;
  first_line: string;
};

export type Aggregate = {
  run_id: string;
  config: Record<string, unknown>;
  aggregate: { n_scenarios: number; mean_ruc: number; mean_ds: number; csr_rate: number };
  by_source: Record<string, SourceSummary>;
  contradiction_type_histogram: Record<string, number>;
  flagged_scenarios: FlaggedScenario[];
  api_usage?: { overall?: { input_tokens: number; output_tokens: number; total_tokens: number; requests: number }; by_agent?: Record<string, Record<string, number>> };
  timing?: { run_total_minutes?: number; mean_scenario_seconds?: number };
  demo_scenario_ids: string[];
  totals: { dataset_size: number; pilot_size: number; demo_size: number };
};

export function loadAggregate(): Aggregate {
  const file = path.join(process.cwd(), "public", "aggregate.json");
  return JSON.parse(fs.readFileSync(file, "utf-8")) as Aggregate;
}
