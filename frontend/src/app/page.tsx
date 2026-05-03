import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Multi-Agent Stress Testing of LLM Ethical Reasoning</h1>
      <p className="mt-2 text-slate-600">
        EECS 6895 final project · Columbia, Spring 2026
      </p>

      <section className="mt-10 space-y-4 text-slate-700 leading-relaxed">
        <p>
          We test whether an LLM&apos;s ethical judgments are robust by surrounding the model under test (the{" "}
          <strong>Proposer</strong>) with two interrogator agents:
        </p>
        <ul className="list-disc pl-6 space-y-1">
          <li>
            A <strong>Counterfactualist</strong> that perturbs morally-irrelevant or morally-relevant features
            of each scenario and re-queries the Proposer.
          </li>
          <li>
            A <strong>Maieutic Inquirer</strong> that asks Socratic follow-ups about the Proposer&apos;s stated
            principle.
          </li>
        </ul>
        <p>
          A separate <strong>CSR Judge</strong> reads the full trace and classifies whether the dialogue
          surfaced a real contradiction. The output is a robustness profile per scenario:{" "}
          <strong>RuC</strong> (Robustness under Counterfactual), <strong>DS</strong> (Discriminating
          Sensitivity), and <strong>CSR</strong> (Contradiction Surfacing Rate).
        </p>
      </section>

      <section className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="180 scenarios" caption="80 Moral Machine · 60 Scruples · 40 Hendrycks ETHICS" />
        <Card title="3 task formats" caption="binary_dilemma · narrative_judgment · unary_judgment" />
        <Card title="4 agents" caption="Proposer · Counterfactualist · Maieutic Inquirer · CSR Judge" />
      </section>

      <section className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/dataset"
          className="rounded-lg border border-slate-200 bg-white p-6 hover:border-slate-400 transition"
        >
          <h2 className="text-lg font-semibold">Browse the dataset →</h2>
          <p className="mt-1 text-sm text-slate-600">
            Filter by source, task format, or primary dimension. Click any scenario to see the full unified
            record + metadata.
          </p>
        </Link>
        <Link
          href="/traces"
          className="rounded-lg border border-slate-200 bg-white p-6 hover:border-slate-400 transition"
        >
          <h2 className="text-lg font-semibold">Walk through a demo trace →</h2>
          <p className="mt-1 text-sm text-slate-600">
            Step through a real evaluation: scenario → Proposer answer → counterfactual probes → Socratic
            follow-ups → judge verdict → metrics.
          </p>
        </Link>
        <Link
          href="/scorecard"
          className="rounded-lg border border-slate-200 bg-white p-6 hover:border-slate-400 transition"
        >
          <h2 className="text-lg font-semibold">Aggregate scorecard →</h2>
          <p className="mt-1 text-sm text-slate-600">
            30-scenario judged pilot results — RuC / DS / CSR per source, contradiction-type breakdown, and
            top flagged scenarios.
          </p>
        </Link>
        <Link
          href="/models"
          className="rounded-lg border border-slate-200 bg-white p-6 hover:border-slate-400 transition"
        >
          <h2 className="text-lg font-semibold">Compare Proposer models →</h2>
          <p className="mt-1 text-sm text-slate-600">
            30-scenario model scoreboard for Llama 3.2 3B, Claude Haiku, and GPT-5 mini across RuC, DS,
            CSR, runtime, and parse health.
          </p>
        </Link>
      </section>
    </div>
  );
}

function Card({ title, caption }: { title: string; caption: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-2xl font-semibold tracking-tight">{title}</div>
      <div className="mt-1 text-xs text-slate-500">{caption}</div>
    </div>
  );
}
