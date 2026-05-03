import Link from "next/link";
import { notFound } from "next/navigation";
import fs from "node:fs";
import path from "node:path";
import { loadScenarios, SOURCE_LABELS, TASK_FORMAT_LABELS } from "@/lib/scenarios";
import MoralMachineRender from "@/components/MoralMachineRender";

const DEMO_IDS = new Set(["mm_0039", "mm_0053", "et_0017", "sc_0003"]);

export function generateStaticParams() {
  return loadScenarios().map((s) => ({ id: s.scenario_id }));
}

export default async function ScenarioDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const scenario = loadScenarios().find((s) => s.scenario_id === id);
  if (!scenario) notFound();

  const traceAvailable = fs.existsSync(path.join(process.cwd(), "public", "traces", `${id}.json`));

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="text-sm">
        <Link href="/dataset" className="text-slate-500 hover:text-slate-800">
          ← Back to dataset
        </Link>
      </div>

      <div className="mt-4 flex items-center gap-3 flex-wrap">
        <span className="font-mono text-lg">{scenario.scenario_id}</span>
        {DEMO_IDS.has(scenario.scenario_id) && (
          <span className="text-[10px] uppercase tracking-wider bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">
            demo
          </span>
        )}
        <span className="text-xs uppercase tracking-wider text-slate-400">
          {TASK_FORMAT_LABELS[scenario.task_format]}
        </span>
        <span className="ml-auto text-xs text-slate-500">{SOURCE_LABELS[scenario.source]}</span>
      </div>

      <h1 className="mt-2 text-xl font-semibold leading-snug">
        {firstLine(scenario.base_text)}
      </h1>

      {traceAvailable && (
        <div className="mt-4">
          <Link
            href={`/traces/${id}`}
            className="inline-block rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-900 hover:bg-amber-100"
          >
            See this scenario in a demo trace →
          </Link>
        </div>
      )}

      {scenario.task_format === "binary_dilemma" && (
        <section className="mt-6">
          <MoralMachineRender attributes={scenario.attributes} />
        </section>
      )}

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Base text</h2>
        <pre className="mt-2 rounded-lg border border-slate-200 bg-white p-4 text-sm whitespace-pre-wrap font-sans leading-relaxed">
          {scenario.base_text}
        </pre>
      </section>

      <section className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        <Field label="Options">
          <code className="text-sm">{JSON.stringify(scenario.options)}</code>
        </Field>
        <Field label="Ground truth (majority)">
          <code className="text-sm">{scenario.ground_truth_majority ?? "null"}</code>
        </Field>
        <Field label="Primary dimension">
          <code className="text-sm">{scenario.primary_dimension}</code>
        </Field>
        <Field label="Cultural cluster">
          <code className="text-sm">{scenario.cultural_cluster ?? "null"}</code>
        </Field>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Attributes</h2>
        <pre className="mt-2 rounded-lg border border-slate-200 bg-white p-4 text-xs overflow-x-auto">
{JSON.stringify(scenario.attributes, null, 2)}
        </pre>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Metadata</h2>
        <pre className="mt-2 rounded-lg border border-slate-200 bg-white p-4 text-xs overflow-x-auto">
{JSON.stringify(scenario.metadata, null, 2)}
        </pre>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</div>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function firstLine(text: string): string {
  const trimmed = text.trim();
  const nl = trimmed.indexOf("\n");
  return nl > 0 ? trimmed.slice(0, nl) : trimmed;
}
