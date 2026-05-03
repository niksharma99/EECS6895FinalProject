import Link from "next/link";
import { loadModelScoreboard, ModelScore } from "@/lib/modelScoreboard";
import { SOURCE_LABELS } from "@/lib/scenarios";

const SOURCE_ORDER = ["moral_machine", "scruples", "ethics_deontology", "ethics_justice"];

export default function ModelsPage() {
  const board = loadModelScoreboard();
  const sorted = [...board.models].sort((a, b) => a.aggregate.csr_rate - b.aggregate.csr_rate);
  const bestRuC = maxBy(board.models, (m) => m.aggregate.mean_ruc);
  const bestDS = maxBy(board.models, (m) => m.aggregate.mean_ds);
  const bestCSR = minBy(board.models, (m) => m.aggregate.csr_rate);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Model scoreboard</h1>
          <p className="mt-2 max-w-3xl text-slate-600">
            30-scenario pilot comparison across Proposer models. The Counterfactualist,
            Maieutic Inquirer, and CSR Judge are held fixed so differences reflect the
            model under test.
          </p>
        </div>
        <div className="text-xs text-slate-500">
          {board.scenario_count} scenarios · {board.models.length} Proposers
        </div>
      </div>

      <section className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-3">
        <Highlight label="Best RuC" model={bestRuC} value={bestRuC.aggregate.mean_ruc} caption="Most stable under irrelevant perturbations" />
        <Highlight label="Best DS" model={bestDS} value={bestDS.aggregate.mean_ds} caption="Most responsive to morally relevant perturbations" />
        <Highlight label="Lowest CSR" model={bestCSR} value={bestCSR.aggregate.csr_rate} caption="Fewest judge-flagged contradictions" invert />
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
          30-scenario comparison
        </h2>
        <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Model</th>
                <th className="px-4 py-3 font-medium text-right">RuC</th>
                <th className="px-4 py-3 font-medium text-right">DS</th>
                <th className="px-4 py-3 font-medium text-right">CSR</th>
                <th className="px-4 py-3 font-medium text-right">Ambiguous</th>
                <th className="px-4 py-3 font-medium text-right">Runtime</th>
                <th className="px-4 py-3 font-medium text-right">Tokens</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sorted.map((model) => (
                <tr key={model.model_id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{model.display_name}</div>
                    <div className="text-xs text-slate-500">{model.provider} · {model.model_id}</div>
                  </td>
                  <MetricCell value={model.aggregate.mean_ruc} />
                  <MetricCell value={model.aggregate.mean_ds} />
                  <MetricCell value={model.aggregate.csr_rate} percent />
                  <td className="px-4 py-3 text-right font-mono">
                    {model.parse.ambiguous}/{model.parse.total_responses}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {model.timing.run_total_minutes.toFixed(1)} min
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {model.api_usage.overall.total_tokens.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10 grid grid-cols-1 lg:grid-cols-3 gap-4">
        {sorted.map((model) => (
          <ModelCard key={model.model_id} model={model} />
        ))}
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
          By source
        </h2>
        <div className="mt-3 grid grid-cols-1 lg:grid-cols-3 gap-4">
          {sorted.map((model) => (
            <div key={model.model_id} className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="font-medium">{model.display_name}</h3>
              <div className="mt-3 space-y-2">
                {SOURCE_ORDER.map((source) => {
                  const row = model.by_source[source];
                  if (!row) return null;
                  return (
                    <div key={source} className="rounded-md bg-slate-50 px-3 py-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium">{SOURCE_LABELS[source as keyof typeof SOURCE_LABELS] ?? source}</span>
                        <span className="font-mono text-slate-500">n={row.n}</span>
                      </div>
                      <div className="mt-1 grid grid-cols-3 gap-2 text-xs">
                        <MiniMetric label="RuC" value={row.mean_ruc} />
                        <MiniMetric label="DS" value={row.mean_ds} />
                        <MiniMetric label="CSR" value={row.csr_rate} percent />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
          Top flagged examples
        </h2>
        <div className="mt-3 grid grid-cols-1 lg:grid-cols-3 gap-4">
          {sorted.map((model) => (
            <div key={model.model_id} className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="font-medium">{model.display_name}</h3>
              {model.flagged_scenarios.length === 0 ? (
                <p className="mt-3 text-sm text-slate-500">No CSR flags in this pilot.</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {model.flagged_scenarios.slice(0, 5).map((scenario) => (
                    <li key={scenario.scenario_id}>
                      <Link
                        href={`/dataset/${scenario.scenario_id}`}
                        className="block rounded-md border border-slate-200 bg-slate-50 px-3 py-2 hover:border-slate-400"
                      >
                        <div className="flex items-center gap-2 text-xs">
                          <span className="font-mono">{scenario.scenario_id}</span>
                          <span className="rounded bg-rose-100 px-1.5 py-0.5 font-mono text-rose-800">
                            {scenario.contradiction_type}
                          </span>
                          <span className="ml-auto text-slate-500">
                            {scenario.confidence?.toFixed(2)}
                          </span>
                        </div>
                        <p className="mt-1 line-clamp-2 text-xs text-slate-600">
                          {scenario.description ?? scenario.first_line}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Highlight({
  label,
  model,
  value,
  caption,
  invert = false,
}: {
  label: string;
  model: ModelScore;
  value: number;
  caption: string;
  invert?: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold">{model.display_name}</div>
      <div className="mt-1 font-mono text-2xl tracking-tight">
        {invert ? `${(value * 100).toFixed(0)}%` : value.toFixed(2)}
      </div>
      <div className="mt-1 text-xs text-slate-500">{caption}</div>
    </div>
  );
}

function MetricCell({ value, percent = false }: { value: number | null; percent?: boolean }) {
  return (
    <td className="px-4 py-3 text-right font-mono">
      {value == null ? "—" : percent ? `${(value * 100).toFixed(0)}%` : value.toFixed(2)}
    </td>
  );
}

function MiniMetric({ label, value, percent = false }: { label: string; value: number | null; percent?: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="font-mono text-slate-800">
        {value == null ? "—" : percent ? `${(value * 100).toFixed(0)}%` : value.toFixed(2)}
      </div>
    </div>
  );
}

function ModelCard({ model }: { model: ModelScore }) {
  const proposerUsage = model.api_usage.by_agent.proposer;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">{model.display_name}</h2>
          <p className="text-xs text-slate-500">{model.provider}</p>
        </div>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs font-mono text-slate-700">
          {model.aggregate.n_scenarios} runs
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-600">{model.notes}</p>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <MiniMetric label="CSR flags" value={model.aggregate.csr_rate} percent />
        <MiniMetric label="Mean seconds" value={model.timing.mean_scenario_seconds} />
        <MiniMetric label="API requests" value={model.api_usage.overall.requests} />
        <MiniMetric label="Proposer tokens" value={proposerUsage?.total_tokens ?? 0} />
      </div>
    </div>
  );
}

function maxBy<T>(items: T[], score: (item: T) => number): T {
  return items.reduce((best, item) => score(item) > score(best) ? item : best);
}

function minBy<T>(items: T[], score: (item: T) => number): T {
  return items.reduce((best, item) => score(item) < score(best) ? item : best);
}
