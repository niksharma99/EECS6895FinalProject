import Link from "next/link";
import { loadModelScoreboard, ModelFlaggedScenario, ModelScore } from "@/lib/modelScoreboard";
import { SOURCE_LABELS } from "@/lib/scenarios";

const SOURCE_ORDER = ["moral_machine", "scruples", "ethics_deontology", "ethics_justice"];
const DEMO_IDS = ["mm_0039", "mm_0053", "et_0017", "sc_0003"];

export default async function Scorecard({
  searchParams,
}: {
  searchParams: Promise<{ model?: string }>;
}) {
  const board = loadModelScoreboard();
  const params = await searchParams;
  const selectedModelId = params.model ?? board.models[0]?.model_id;
  const model = board.models.find((m) => m.model_id === selectedModelId) ?? board.models[0];

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">Aggregate scorecard</h1>
      <p className="mt-2 text-slate-600">
        Results from the shared 30-scenario judged pilot subset. Select a Proposer model below; the
        Counterfactualist, Maieutic Inquirer, and CSR Judge are held fixed for comparison.
      </p>

      <ModelSelector models={board.models} selected={model.model_id} />

      <Funnel scenarioCount={board.scenario_count} demoIds={DEMO_IDS} model={model} />

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
          Top-line metrics
        </h2>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
          <BigStat label="mean RuC" value={model.aggregate.mean_ruc} caption="Robustness under irrelevant perturbations" />
          <BigStat label="mean DS" value={model.aggregate.mean_ds} caption="Discriminating Sensitivity on relevant perturbations" />
          <BigStat label="CSR rate" value={model.aggregate.csr_rate} caption="Fraction of scenarios where the judge flagged a real contradiction" />
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
          By source
        </h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-3 py-2 font-medium">Source</th>
                <th className="px-3 py-2 font-medium text-right">n</th>
                <th className="px-3 py-2 font-medium text-right">mean RuC</th>
                <th className="px-3 py-2 font-medium text-right">mean DS</th>
                <th className="px-3 py-2 font-medium text-right">CSR rate</th>
                <th className="px-3 py-2 font-medium text-right">flagged</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {SOURCE_ORDER.map((src) => {
                const s = model.by_source[src];
                if (!s) return null;
                return (
                  <tr key={src} className="bg-white">
                    <td className="px-3 py-2 font-medium">{SOURCE_LABELS[src as keyof typeof SOURCE_LABELS] ?? src}</td>
                    <td className="px-3 py-2 text-right font-mono">{s.n}</td>
                    <td className="px-3 py-2 text-right font-mono">{s.mean_ruc?.toFixed(2) ?? "—"}</td>
                    <td className="px-3 py-2 text-right font-mono">{s.mean_ds?.toFixed(2) ?? "—"}</td>
                    <td className="px-3 py-2 text-right font-mono">{s.csr_rate == null ? "—" : `${(s.csr_rate * 100).toFixed(0)}%`}</td>
                    <td className="px-3 py-2 text-right font-mono">{s.n_flagged}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
          Contradiction type histogram
        </h2>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(model.contradiction_type_histogram)
            .sort((a, b) => b[1] - a[1])
            .map(([t, n]) => (
              <TypeBar key={t} type={t} n={n} max={Math.max(...Object.values(model.contradiction_type_histogram))} />
            ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
          Flagged scenarios ({model.flagged_scenarios.length} of {model.aggregate.n_scenarios})
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Sorted by judge confidence. Demo-trace candidates are highlighted when present in the current frontend trace set.
        </p>
        <ul className="mt-3 space-y-2">
          {model.flagged_scenarios.map((f) => (
            <FlaggedRow key={f.scenario_id} f={f} demoIds={DEMO_IDS} />
          ))}
        </ul>
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Run cost & timing</h2>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
          <Card label="Wall time" value={`${model.timing.run_total_minutes.toFixed(1)} min`} caption={`${model.timing.mean_scenario_seconds.toFixed(1)} s/scenario average`} />
          <Card label="Total tokens" value={model.api_usage.overall.total_tokens.toLocaleString()} caption={`${model.api_usage.overall.requests} API requests across available agents`} />
          <Card label="Parse ambiguity" value={`${model.parse.ambiguous}/${model.parse.total_responses}`} caption="Ambiguous Proposer responses across base, counterfactual, and maieutic calls" />
        </div>
      </section>
    </div>
  );
}

function ModelSelector({ models, selected }: { models: ModelScore[]; selected: string }) {
  return (
    <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wider text-slate-500">Proposer model</div>
      <div className="mt-3 flex flex-wrap gap-2">
        {models.map((model) => {
          const active = model.model_id === selected;
          return (
            <Link
              key={model.model_id}
              href={`/scorecard?model=${encodeURIComponent(model.model_id)}`}
              className={`rounded-md border px-3 py-2 text-sm transition ${
                active
                  ? "border-slate-900 bg-slate-900 text-white"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-400"
              }`}
            >
              <span className="font-medium">{model.display_name}</span>
              <span className={`ml-2 text-xs ${active ? "text-slate-300" : "text-slate-500"}`}>{model.provider}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function Funnel({ scenarioCount, demoIds, model }: { scenarioCount: number; demoIds: string[]; model: ModelScore }) {
  return (
    <div className="mt-6 rounded-lg border border-slate-200 bg-white p-5">
      <div className="text-xs uppercase tracking-wider text-slate-500 mb-3">From dataset to selected run</div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-stretch">
        <FunnelStep title="180 scenarios" caption="Full unified dataset" linkText="Browse →" linkHref="/dataset" />
        <FunnelStep title={`${scenarioCount} pilot`} caption="Shared judged subset for model comparison" />
        <FunnelStep title={model.display_name} caption={demoIds.join(" · ")} linkText="Compare models →" linkHref="/models" />
      </div>
    </div>
  );
}

function FunnelStep({
  title,
  caption,
  linkText,
  linkHref,
}: {
  title: string;
  caption: string;
  linkText?: string;
  linkHref?: string;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-4 flex flex-col">
      <div className="text-xl font-semibold tracking-tight">{title}</div>
      <div className="mt-1 text-xs text-slate-500 flex-1">{caption}</div>
      {linkText && linkHref && (
        <Link href={linkHref} className="mt-3 text-xs text-slate-700 hover:text-slate-900 underline">
          {linkText}
        </Link>
      )}
    </div>
  );
}

function BigStat({ label, value, caption }: { label: string; value: number; caption: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold tracking-tight">
        {label.includes("CSR") ? `${(value * 100).toFixed(0)}%` : value.toFixed(2)}
      </div>
      <div className="mt-1 text-xs text-slate-500">{caption}</div>
    </div>
  );
}

function Card({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold tracking-tight font-mono">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{caption}</div>
    </div>
  );
}

function TypeBar({ type, n, max }: { type: string; n: number; max: number }) {
  const isFlag = type !== "none";
  const tone = isFlag ? "bg-rose-300" : "bg-slate-200";
  const pct = max ? (n / max) * 100 : 0;
  return (
    <div className="rounded border border-slate-200 bg-white px-3 py-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono">{type}</span>
        <span className="text-slate-500">{n}</span>
      </div>
      <div className="mt-1 h-1.5 rounded bg-slate-100 overflow-hidden">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function FlaggedRow({ f, demoIds }: { f: ModelFlaggedScenario; demoIds: string[] }) {
  const isDemo = demoIds.includes(f.scenario_id);
  const href = isDemo ? `/traces/${f.scenario_id}` : `/dataset/${f.scenario_id}`;
  return (
    <li>
      <Link
        href={href}
        className={`block rounded-lg border p-3 transition ${isDemo ? "border-amber-300 bg-amber-50/40 hover:bg-amber-50" : "border-slate-200 bg-white hover:border-slate-400"}`}
      >
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-mono">{f.scenario_id}</span>
          <span className="text-slate-500">{SOURCE_LABELS[f.source as keyof typeof SOURCE_LABELS] ?? f.source}</span>
          <span className="font-mono bg-rose-100 text-rose-800 border border-rose-200 px-1.5 py-0.5 rounded">
            {f.contradiction_type}
          </span>
          <span className="text-slate-500 ml-auto">conf {f.confidence?.toFixed(2)}</span>
          {isDemo && (
            <span className="text-[10px] uppercase tracking-wider bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">
              demo
            </span>
          )}
        </div>
        <div className="mt-1 text-sm text-slate-800 line-clamp-1">{f.first_line}</div>
        {f.description && (
          <div className="mt-1 text-xs text-slate-600 line-clamp-2">{f.description}</div>
        )}
      </Link>
    </li>
  );
}
