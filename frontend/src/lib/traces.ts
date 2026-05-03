import fs from "node:fs";
import path from "node:path";

export type Perturbation = {
  perturbation_id: string;
  perturbation_type: string;
  morally_relevant: boolean;
  expected_behavior: string;
  changed_fields: string[];
  perturbed_text: string;
  rationale: string;
};

export type ProposerResponse = {
  judgment: string | null;
  reasoning: string;
  raw_text: string;
  parse_method?: string;
  ambiguous?: boolean;
};

export type CounterfactualResult = {
  perturbation: Perturbation;
  response: ProposerResponse;
  consistent_with_base: boolean;
};

export type MaieuticQuestion = {
  turn: number;
  question: string;
  targeted_principle: string;
};

export type MaieuticTurn = {
  question: MaieuticQuestion;
  response: ProposerResponse;
};

export type Metrics = {
  ruc_score: number | null;
  ds_score: number | null;
  csr_flag: boolean;
  contradiction_description: string | null;
  contradiction_type: string | null;
  contradiction_confidence: number | null;
};

export type Trace = {
  scenario_id: string;
  source: string;
  task_format: string;
  proposer_model: string;
  base: {
    prompt: { system?: string; user?: string } | string;
    response: ProposerResponse;
  };
  counterfactuals: CounterfactualResult[];
  maieutic_dialogue: MaieuticTurn[];
  api_usage?: Record<string, { model?: string; usage?: Record<string, unknown>; judgment?: unknown }>;
  timing?: Record<string, number | number[]>;
  metrics: Metrics;
};

export const DEMO_TRACE_IDS = ["mm_0039", "mm_0053", "et_0017", "sc_0003"];

export function loadTrace(id: string): Trace | null {
  const file = path.join(process.cwd(), "public", "traces", `${id}.json`);
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf-8")) as Trace;
}
