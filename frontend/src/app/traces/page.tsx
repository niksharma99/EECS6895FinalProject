import Link from "next/link";
import { loadScenarios, SOURCE_LABELS, TASK_FORMAT_LABELS } from "@/lib/scenarios";
import { DEMO_TRACE_IDS, loadTrace } from "@/lib/traces";

export default function TracesIndex() {
  const all = loadScenarios();
  const byId = new Map(all.map((s) => [s.scenario_id, s]));

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">Demo traces</h1>
      <p className="mt-2 text-slate-600">
        Four scenarios from the 30-scenario judged pilot, hand-picked for cross-format coverage. Each shows
        a complete evaluation: scenario → Proposer → counterfactual probes → Maieutic dialogue → judge
        verdict → metrics.
      </p>

      <ul className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-3">
        {DEMO_TRACE_IDS.map((id) => {
          const s = byId.get(id);
          const trace = loadTrace(id);
          if (!s || !trace) return null;
          const m = trace.metrics;
          return (
            <li key={id}>
              <Link
                href={`/traces/${id}`}
                className="block rounded-lg border border-slate-200 bg-white p-4 hover:border-amber-400 transition"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm">{id}</span>
                  <span className="text-[10px] uppercase tracking-wider bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">
                    demo
                  </span>
                  <span className="ml-auto text-[10px] uppercase tracking-wider text-slate-400">
                    {TASK_FORMAT_LABELS[s.task_format]}
                  </span>
                </div>
                <div className="mt-2 text-sm text-slate-800 line-clamp-2">{firstLine(s.base_text)}</div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                  <Stat label="RuC" value={m.ruc_score} />
                  <Stat label="DS" value={m.ds_score} />
                  <span className={`px-1.5 py-0.5 rounded border text-[11px] ${m.csr_flag ? "bg-rose-50 text-rose-800 border-rose-200" : "bg-emerald-50 text-emerald-700 border-emerald-200"}`}>
                    CSR: {m.csr_flag ? "flagged" : "clean"}
                  </span>
                  {m.contradiction_type && m.contradiction_type !== "none" && (
                    <span className="px-1.5 py-0.5 rounded border bg-rose-50 text-rose-800 border-rose-200 font-mono">
                      {m.contradiction_type}
                    </span>
                  )}
                  <span className="ml-auto text-slate-400">{SOURCE_LABELS[s.source]}</span>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | null }) {
  const display = value === null ? "—" : value.toFixed(2);
  return (
    <span className="px-1.5 py-0.5 rounded border bg-slate-50 text-slate-700 border-slate-200 font-mono">
      {label}: {display}
    </span>
  );
}

function firstLine(text: string): string {
  const trimmed = text.trim();
  const nl = trimmed.indexOf("\n");
  return nl > 0 ? trimmed.slice(0, nl) : trimmed;
}
