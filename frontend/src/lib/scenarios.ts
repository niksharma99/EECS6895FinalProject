import fs from "node:fs";
import path from "node:path";

export type Scenario = {
  scenario_id: string;
  source: "moral_machine" | "scruples" | "ethics_deontology" | "ethics_justice";
  task_format: "binary_dilemma" | "unary_judgment" | "narrative_judgment";
  base_text: string;
  options: string[];
  attributes: Record<string, unknown>;
  primary_dimension: string;
  ground_truth_majority: string | null;
  cultural_cluster: string | null;
  metadata: Record<string, unknown>;
};

export const TASK_FORMAT_LABELS: Record<Scenario["task_format"], string> = {
  binary_dilemma: "Binary dilemma",
  unary_judgment: "Unary judgment",
  narrative_judgment: "Narrative judgment",
};

export const SOURCE_LABELS: Record<Scenario["source"], string> = {
  moral_machine: "Moral Machine",
  scruples: "Scruples",
  ethics_deontology: "ETHICS · Deontology",
  ethics_justice: "ETHICS · Justice",
};

export function loadScenarios(): Scenario[] {
  const file = path.join(process.cwd(), "public", "scenarios.json");
  return JSON.parse(fs.readFileSync(file, "utf-8")) as Scenario[];
}
