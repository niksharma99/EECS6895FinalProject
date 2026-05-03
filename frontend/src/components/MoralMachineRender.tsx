// Visualizes a Moral Machine binary_dilemma scenario from its structured attributes.
// No GPT image generation — pure deterministic emoji + Tailwind grid.

const GLYPHS: Record<string, string> = {
  man: "👨", woman: "👩", boy: "👦", girl: "👧",
  "elderly man": "👨‍🦳", "elderly woman": "👩‍🦳",
  baby: "👶", "pregnant woman": "🤰",
  "homeless person": "🧎",
  "large man": "🧑‍🦱", "large woman": "👩‍🦱",
  criminal: "🦹",
  "male executive": "👨‍💼", "female executive": "👩‍💼",
  "male athlete": "🏃‍♂️", "female athlete": "🏃‍♀️",
  "male doctor": "👨‍⚕️", "female doctor": "👩‍⚕️",
  dog: "🐕", cat: "🐈",
};

type Group = {
  label?: string;
  characters?: Record<string, number>;
};

type Attrs = {
  group_left?: Group;
  group_right?: Group;
  is_in_car?: boolean;
  is_interventionism?: boolean;
  is_law?: boolean;
  traffic_light_pattern?: [string, string];
  primary_dimension?: string;
};

export default function MoralMachineRender({ attributes }: { attributes: Attrs }) {
  const left = attributes.group_left ?? {};
  const right = attributes.group_right ?? {};
  const inCar = attributes.is_in_car ?? false;
  const swerve = attributes.is_interventionism ?? false;
  const law = attributes.is_law ?? false;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">
        Scenario at a glance
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <CasePanel
          tag="Case 1"
          group={left}
          killed={left}
          spared={right}
          carAction={swerve ? "swerves" : "continues straight"}
          inCar={inCar}
          law={law}
          trafficLight={attributes.traffic_light_pattern?.[0]}
          highlight="rose"
        />
        <CasePanel
          tag="Case 2"
          group={right}
          killed={right}
          spared={left}
          carAction={swerve ? "continues straight" : "swerves"}
          inCar={inCar}
          law={law}
          trafficLight={attributes.traffic_light_pattern?.[1]}
          highlight="sky"
        />
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5 text-[10px]">
        <Pill>primary: {attributes.primary_dimension}</Pill>
        <Pill>{inCar ? "passengers ↔ pedestrians" : "two pedestrian groups"}</Pill>
        <Pill>{swerve ? "swerve = intervention" : "straight = no intervention"}</Pill>
        {law && <Pill>traffic light affects judgment</Pill>}
      </div>
    </div>
  );
}

function CasePanel({
  tag,
  killed,
  spared,
  carAction,
  inCar,
  law,
  trafficLight,
  highlight,
}: {
  tag: string;
  group: Group;
  killed: Group;
  spared: Group;
  carAction: string;
  inCar: boolean;
  law: boolean;
  trafficLight?: string;
  highlight: "rose" | "sky";
}) {
  const ringColor = highlight === "rose" ? "ring-rose-200 bg-rose-50/40" : "ring-sky-200 bg-sky-50/40";
  return (
    <div className={`rounded-lg ring-1 ${ringColor} p-3`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold tracking-wider uppercase">{tag}</span>
        <span className="text-[10px] text-slate-500">car {carAction}</span>
      </div>

      <Row label="dies" tone="rose" group={killed} caption={inCar ? (killed === spared ? "" : "passengers" ) : ""} />
      <Row label="spared" tone="emerald" group={spared} />

      {law && trafficLight && trafficLight !== "NA" && (
        <div className="mt-2 text-[10px] text-slate-500">
          traffic light: <span className={trafficLight === "red" ? "text-rose-600 font-medium" : "text-emerald-600 font-medium"}>{trafficLight}</span>
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  tone,
  group,
  caption,
}: {
  label: string;
  tone: "rose" | "emerald";
  group: Group;
  caption?: string;
}) {
  const items = Object.entries(group.characters ?? {});
  const total = items.reduce((acc, [, n]) => acc + n, 0);
  const labelColor = tone === "rose" ? "text-rose-700" : "text-emerald-700";
  return (
    <div className="mt-2">
      <div className={`text-[10px] font-medium uppercase tracking-wider ${labelColor}`}>
        {label} <span className="text-slate-400 font-normal">· {total} {total === 1 ? "individual" : "individuals"}</span>
        {caption && <span className="text-slate-400 font-normal"> · {caption}</span>}
      </div>
      <div className="mt-1 flex flex-wrap gap-1.5 items-center">
        {items.map(([name, count]) => (
          <span key={name} className="inline-flex items-center gap-1 rounded bg-white border border-slate-200 px-1.5 py-0.5 text-xs">
            <span className="text-base leading-none">{GLYPHS[name] ?? "•"}</span>
            <span className="text-slate-700">{count}</span>
            <span className="text-slate-500 text-[10px]">{name}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block bg-slate-100 text-slate-700 border border-slate-200 px-1.5 py-0.5 rounded">
      {children}
    </span>
  );
}
