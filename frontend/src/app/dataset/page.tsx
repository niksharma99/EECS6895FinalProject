import Link from "next/link";
import { loadScenarios, SOURCE_LABELS, TASK_FORMAT_LABELS } from "@/lib/scenarios";

const DEMO_IDS = new Set(["mm_0039", "mm_0053", "et_0017", "sc_0003"]);

export default function DatasetPage({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  return <DatasetView searchParamsPromise={searchParams} />;
}

async function DatasetView({ searchParamsPromise }: { searchParamsPromise: Promise<Record<string, string>> }) {
  const params = await searchParamsPromise;
  const scenarios = loadScenarios();
  const sourceFilter = params.source;
  const formatFilter = params.format;
  const dimFilter = params.dim;

  const sources = Array.from(new Set(scenarios.map((s) => s.source))).sort();
  const formats = Array.from(new Set(scenarios.map((s) => s.task_format))).sort();
  const dims = Array.from(new Set(scenarios.map((s) => s.primary_dimension))).sort();

  const filtered = scenarios.filter(
    (s) =>
      (!sourceFilter || s.source === sourceFilter) &&
      (!formatFilter || s.task_format === formatFilter) &&
      (!dimFilter || s.primary_dimension === dimFilter)
  );

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Dataset</h1>
        <span className="text-sm text-slate-500">
          {filtered.length} of {scenarios.length} scenarios
        </span>
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <FilterSelect label="Source" name="source" value={sourceFilter} options={sources} optionLabel={(v) => SOURCE_LABELS[v as keyof typeof SOURCE_LABELS] ?? v} params={params} />
        <FilterSelect label="Task format" name="format" value={formatFilter} options={formats} optionLabel={(v) => TASK_FORMAT_LABELS[v as keyof typeof TASK_FORMAT_LABELS] ?? v} params={params} />
        <FilterSelect label="Primary dimension" name="dim" value={dimFilter} options={dims} optionLabel={(v) => v} params={params} />
      </div>

      {(sourceFilter || formatFilter || dimFilter) && (
        <div className="mt-3">
          <Link href="/dataset" className="text-xs text-slate-500 hover:text-slate-800 underline">
            Clear filters
          </Link>
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map((s) => {
          const title = firstLine(s.base_text);
          return (
            <Link
              key={s.scenario_id}
              href={`/dataset/${s.scenario_id}`}
              className="rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400 transition group"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-slate-500">{s.scenario_id}</span>
                {DEMO_IDS.has(s.scenario_id) && (
                  <span className="text-[10px] uppercase tracking-wider bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">
                    demo
                  </span>
                )}
                <span className="ml-auto text-[10px] uppercase tracking-wider text-slate-400">
                  {TASK_FORMAT_LABELS[s.task_format]}
                </span>
              </div>
              <div className="mt-2 text-sm text-slate-800 line-clamp-3 group-hover:text-slate-900">
                {title}
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                <Pill>{SOURCE_LABELS[s.source]}</Pill>
                <Pill>{s.primary_dimension}</Pill>
                {s.ground_truth_majority && <Pill tone="green">GT: {s.ground_truth_majority}</Pill>}
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  name,
  value,
  options,
  optionLabel,
  params,
}: {
  label: string;
  name: string;
  value: string | undefined;
  options: string[];
  optionLabel: (v: string) => string;
  params: Record<string, string>;
}) {
  return (
    <form action="/dataset" method="get" className="flex flex-col">
      <label htmlFor={name} className="text-xs font-medium text-slate-600 mb-1">
        {label}
      </label>
      {/* preserve other filters */}
      {Object.entries(params)
        .filter(([k]) => k !== name)
        .map(([k, v]) => (
          <input key={k} type="hidden" name={k} value={v} />
        ))}
      <select
        id={name}
        name={name}
        defaultValue={value || ""}
        className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
        onChange={undefined}
      >
        <option value="">All</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {optionLabel(opt)}
          </option>
        ))}
      </select>
      <button type="submit" className="sr-only">
        Apply
      </button>
    </form>
  );
}

function Pill({ children, tone = "slate" }: { children: React.ReactNode; tone?: "slate" | "green" }) {
  const cls =
    tone === "green"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span className={`inline-block text-[10px] font-medium px-1.5 py-0.5 rounded border ${cls}`}>
      {children}
    </span>
  );
}

function firstLine(text: string): string {
  const trimmed = text.trim();
  const nl = trimmed.indexOf("\n");
  return (nl > 0 ? trimmed.slice(0, nl) : trimmed).slice(0, 200);
}
