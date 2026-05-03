import Link from "next/link";
import { notFound } from "next/navigation";
import { DEMO_TRACE_IDS, loadTrace, Metrics, MaieuticTurn, CounterfactualResult, ProposerResponse } from "@/lib/traces";
import { loadScenarios, SOURCE_LABELS, TASK_FORMAT_LABELS, Scenario } from "@/lib/scenarios";
import MoralMachineRender from "@/components/MoralMachineRender";

export function generateStaticParams() {
  return DEMO_TRACE_IDS.map((id) => ({ id }));
}

export default async function TracePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const trace = loadTrace(id);
  if (!trace) notFound();

  const scenario = loadScenarios().find((s) => s.scenario_id === id);
  if (!scenario) notFound();

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="text-sm">
        <Link href="/traces" className="text-slate-500 hover:text-slate-800">
          ← All demo traces
        </Link>
        <span className="mx-2 text-slate-300">·</span>
        <Link href={`/dataset/${id}`} className="text-slate-500 hover:text-slate-800">
          See scenario record
        </Link>
      </div>

      <header className="mt-4">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-mono text-lg">{id}</span>
          <span className="text-xs uppercase tracking-wider bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">
            demo trace
          </span>
          <span className="text-xs uppercase tracking-wider text-slate-400">
            {TASK_FORMAT_LABELS[scenario.task_format as keyof typeof TASK_FORMAT_LABELS] ?? scenario.task_format}
          </span>
          <span className="ml-auto text-xs text-slate-500">{SOURCE_LABELS[scenario.source as keyof typeof SOURCE_LABELS] ?? scenario.source}</span>
        </div>
        <h1 className="mt-2 text-xl font-semibold leading-snug">
          {firstLine(scenario.base_text)}
        </h1>
        <p className="mt-1 text-xs text-slate-500">
          Proposer: <code>{trace.proposer_model}</code>
        </p>
      </header>

      {/* Step 1: Scenario card */}
      <Step n={1} title="Scenario" caption="What the Proposer LLM is asked.">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed">
            {scenario.base_text}
          </pre>
        </div>
        {scenario.task_format === "binary_dilemma" && (
          <div className="mt-3">
            <MoralMachineRender attributes={scenario.attributes} />
          </div>
        )}
        <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
          <Pill>options: {JSON.stringify(scenario.options)}</Pill>
          {scenario.ground_truth_majority && (
            <Pill tone="emerald">ground truth: {scenario.ground_truth_majority}</Pill>
          )}
        </div>
      </Step>

      {/* Step 2: Proposer base answer */}
      <Step n={2} title="Proposer answers" caption="The model under test gives a one-word judgment + brief reasoning.">
        <ResponseBubble role="proposer" response={trace.base.response} />
      </Step>

      {/* Step 3: Counterfactual probes */}
      <Step
        n={3}
        title="Counterfactualist perturbs"
        caption={`${trace.counterfactuals.length} probes — irrelevant changes test stability (RuC); relevant changes test sensitivity (DS).`}
      >
        <div className="grid grid-cols-1 gap-3">
          {trace.counterfactuals.map((cf, i) => (
            <CounterfactualCard key={i} cf={cf} />
          ))}
        </div>
      </Step>

      {/* Step 4: Maieutic dialogue */}
      <Step
        n={4}
        title="Maieutic Inquirer probes principles"
        caption="Socratic follow-ups pressure-test the Proposer's stated reasoning."
      >
        <div className="space-y-3">
          {trace.maieutic_dialogue.map((turn, i) => (
            <MaieuticTurnView key={i} turn={turn} />
          ))}
        </div>
      </Step>

      {/* Step 5: Judge verdict */}
      <Step n={5} title="CSR Judge verdict" caption="Reads the full trace and classifies whether a real contradiction surfaced.">
        <JudgeVerdict metrics={trace.metrics} />
      </Step>

      {/* Step 6: Metrics */}
      <Step n={6} title="Metrics" caption="Per-scenario robustness profile.">
        <MetricsPanel metrics={trace.metrics} />
      </Step>

      <DemoTraceNav currentId={id} />
    </div>
  );
}

function DemoTraceNav({ currentId }: { currentId: string }) {
  const idx = DEMO_TRACE_IDS.indexOf(currentId);
  const prev = idx > 0 ? DEMO_TRACE_IDS[idx - 1] : null;
  const next = idx >= 0 && idx < DEMO_TRACE_IDS.length - 1 ? DEMO_TRACE_IDS[idx + 1] : null;
  return (
    <nav className="mt-12 pt-6 border-t border-slate-200 flex items-center justify-between text-sm">
      <div>
        {prev ? (
          <Link href={`/traces/${prev}`} className="text-slate-600 hover:text-slate-900">
            ← {prev}
          </Link>
        ) : (
          <Link href="/traces" className="text-slate-500 hover:text-slate-800">
            ← All demo traces
          </Link>
        )}
      </div>
      <div className="text-xs text-slate-400">
        demo {idx + 1} of {DEMO_TRACE_IDS.length}
      </div>
      <div>
        {next ? (
          <Link href={`/traces/${next}`} className="text-slate-600 hover:text-slate-900">
            {next} →
          </Link>
        ) : (
          <Link href="/scorecard" className="text-slate-500 hover:text-slate-800">
            See aggregate scorecard →
          </Link>
        )}
      </div>
    </nav>
  );
}

function Step({
  n,
  title,
  caption,
  children,
}: {
  n: number;
  title: string;
  caption?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-10 relative">
      <div className="flex items-baseline gap-3">
        <span className="flex-none flex items-center justify-center w-7 h-7 rounded-full bg-slate-900 text-white text-xs font-semibold">
          {n}
        </span>
        <div>
          <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
          {caption && <p className="text-xs text-slate-500">{caption}</p>}
        </div>
      </div>
      <div className="mt-4 ml-10">{children}</div>
    </section>
  );
}

function ResponseBubble({ role, response }: { role: "proposer" | "inquirer"; response: ProposerResponse }) {
  const judgmentColor = response.judgment ? "bg-slate-900 text-white" : "bg-rose-100 text-rose-900";
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2">
        <span className="text-xs uppercase tracking-wider text-slate-500">{role === "proposer" ? "Proposer" : "Inquirer"}</span>
        {response.judgment !== undefined && (
          <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${judgmentColor}`}>
            {response.judgment ?? "ambiguous"}
          </span>
        )}
      </div>
      <p className="mt-2 text-sm leading-relaxed">{response.reasoning || <em className="text-slate-500">(no reasoning provided)</em>}</p>
    </div>
  );
}

function CounterfactualCard({ cf }: { cf: CounterfactualResult }) {
  const relTag = cf.perturbation.morally_relevant ? "RELEVANT" : "IRRELEVANT";
  const relColor = cf.perturbation.morally_relevant
    ? "bg-violet-100 text-violet-800 border-violet-200"
    : "bg-slate-100 text-slate-700 border-slate-200";
  const verdict = cf.consistent_with_base ? "judgment held" : "judgment flipped";
  const verdictColor = cf.consistent_with_base ? "text-emerald-700" : "text-amber-700";

  // Was the flip "correct"? (DS contributor)
  const expected = cf.perturbation.expected_behavior;
  const correctFlip =
    cf.perturbation.morally_relevant &&
    expected === "judgment_should_change" &&
    !cf.consistent_with_base;
  const correctHold =
    !cf.perturbation.morally_relevant &&
    expected === "judgment_should_stay_same" &&
    cf.consistent_with_base;

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center gap-2 px-4 py-2 border-b border-slate-100">
        <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border ${relColor}`}>
          {relTag}
        </span>
        <span className="text-xs font-mono text-slate-700">{cf.perturbation.perturbation_type}</span>
        <span className="ml-auto text-xs text-slate-500">expected: {expected}</span>
      </div>
      <div className="px-4 py-3 text-xs text-slate-600 bg-slate-50/50">
        <strong>rationale:</strong> {cf.perturbation.rationale}
      </div>
      <details className="px-4 py-2 border-t border-slate-100">
        <summary className="text-xs text-slate-500 cursor-pointer">show perturbed text</summary>
        <pre className="mt-2 text-xs whitespace-pre-wrap font-sans leading-relaxed bg-slate-50 p-3 rounded border border-slate-200">
          {cf.perturbation.perturbed_text}
        </pre>
      </details>
      <div className="px-4 py-3 border-t border-slate-100">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-wider text-slate-500">Proposer →</span>
          <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-slate-900 text-white">
            {cf.response.judgment ?? "ambiguous"}
          </span>
          <span className={`ml-auto text-xs font-medium ${verdictColor}`}>
            {verdict}
            {(correctFlip || correctHold) && <span className="ml-1 text-emerald-600">(as expected)</span>}
            {!correctFlip && !correctHold && cf.perturbation.morally_relevant !== cf.consistent_with_base && (
              <span className="ml-1 text-rose-600">(against expectation)</span>
            )}
          </span>
        </div>
        <p className="mt-1 text-sm leading-relaxed">{cf.response.reasoning || <em className="text-slate-500">(no reasoning)</em>}</p>
      </div>
    </div>
  );
}

function MaieuticTurnView({ turn }: { turn: MaieuticTurn }) {
  return (
    <div className="space-y-2">
      <div className="rounded-lg border border-violet-200 bg-violet-50 p-4">
        <div className="flex items-center gap-2 text-xs">
          <span className="uppercase tracking-wider text-violet-700 font-semibold">Inquirer · turn {turn.question.turn}</span>
          <span className="text-violet-600">target: {turn.question.targeted_principle}</span>
        </div>
        <p className="mt-2 text-sm leading-relaxed">{turn.question.question}</p>
      </div>
      <div className="ml-6">
        <ResponseBubble role="proposer" response={turn.response} />
      </div>
    </div>
  );
}

function JudgeVerdict({ metrics }: { metrics: Metrics }) {
  if (!metrics.csr_flag) {
    return (
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
        <div className="text-sm font-semibold text-emerald-800">No contradiction surfaced</div>
        <div className="mt-1 text-xs text-emerald-700">
          confidence {metrics.contradiction_confidence?.toFixed(2) ?? "—"}
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 p-4">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-rose-800">Contradiction surfaced</span>
        <span className="text-xs font-mono text-rose-700 bg-white border border-rose-200 px-1.5 py-0.5 rounded">
          {metrics.contradiction_type}
        </span>
        <span className="ml-auto text-xs text-rose-700">confidence {metrics.contradiction_confidence?.toFixed(2) ?? "—"}</span>
      </div>
      {metrics.contradiction_description && (
        <p className="mt-2 text-sm leading-relaxed text-rose-900">{metrics.contradiction_description}</p>
      )}
    </div>
  );
}

function MetricsPanel({ metrics }: { metrics: Metrics }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <MetricCard
        label="RuC"
        value={metrics.ruc_score}
        caption="Robustness under Counterfactual — fraction of irrelevant perturbations where judgment held."
      />
      <MetricCard
        label="DS"
        value={metrics.ds_score}
        caption="Discriminating Sensitivity — fraction of relevant perturbations where judgment correctly flipped."
      />
      <MetricCard
        label="CSR"
        value={metrics.csr_flag ? 1 : 0}
        binary
        caption="Contradiction Surfacing Rate — did the dialogue surface a real contradiction?"
      />
    </div>
  );
}

function MetricCard({
  label,
  value,
  caption,
  binary,
}: {
  label: string;
  value: number | null;
  caption: string;
  binary?: boolean;
}) {
  const display = value === null ? "—" : binary ? (value ? "1" : "0") : value.toFixed(2);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-semibold tracking-wider uppercase text-slate-700">{label}</span>
        <span className="text-2xl font-semibold tracking-tight">{display}</span>
      </div>
      <div className="mt-1 text-xs text-slate-500">{caption}</div>
    </div>
  );
}

function Pill({ children, tone = "slate" }: { children: React.ReactNode; tone?: "slate" | "emerald" }) {
  const cls =
    tone === "emerald"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span className={`inline-block text-[11px] font-medium px-1.5 py-0.5 rounded border ${cls}`}>
      {children}
    </span>
  );
}

function firstLine(text: string): string {
  const trimmed = text.trim();
  const nl = trimmed.indexOf("\n");
  return nl > 0 ? trimmed.slice(0, nl) : trimmed;
}
