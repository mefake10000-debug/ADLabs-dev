const INK = "#16161f"
const SUB = "rgba(29,29,31,0.55)"
const LINE = "rgba(29,29,31,0.14)"
const GOLD = "#A9792B"
const GOLD_DEEP = "#8f6422"
const GOLD_SOFT = "rgba(169,121,43,0.14)"
const GOLD_SOFT2 = "rgba(169,121,43,0.08)"
const LIME = "#D4F53C"
const LIME_DEEP = "#A9BF2E"
const CREAM = "#F5F0E4"
const CARD = "#FFFFFF"
const WALL = "#2a2a2e"
const MONO = "'ui-monospace', 'SF Mono', SFMono-Regular, Menlo, Consolas, monospace"
const SANS = "'Inter', system-ui, sans-serif"

/* ---------------------------- 1 · street moments ----------------------------- */

export function StreetMomentDiagram() {
  return (
    <svg viewBox="0 0 880 272" className="h-auto w-full" role="img" aria-label="Three storefront moments: pass, stop, enter">
      {/* facade */}
      <rect x={0} y={0} width={880} height={56} rx={0} fill="#F1ECE0" />
      <rect x={0} y={54} width={880} height={2} fill={LINE} />

      {/* glass panels */}
      {[52, 280, 700].map((x) => (
        <g key={x}>
          <rect x={x} y={14} width={150} height={30} rx={3} fill={GOLD_SOFT} stroke={GOLD_SOFT2} strokeWidth={2} />
          <line x1={x + 8} y1={29} x2={x + 142} y2={29} stroke="rgba(169,121,43,0.18)" strokeWidth={1.5} />
        </g>
      ))}

      {/* door */}
      <rect x={516} y={8} width={52} height={46} rx={4} fill="rgba(29,29,31,0.05)" stroke={GOLD} strokeWidth={2.5} />
      <line x1={550} y1={20} x2={550} y2={34} stroke={INK} strokeWidth={2} strokeLinecap="round" />
      <text x={542} y={72} textAnchor="middle" fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.14em" fill={GOLD}>
        THE DOOR
      </text>

      {/* sidewalk + curb */}
      <rect x={0} y={56} width={880} height={166} fill={CREAM} />
      <rect x={0} y={222} width={880} height={8} fill="rgba(29,29,31,0.12)" />
      <text x={880} y={232} textAnchor="end" fontFamily={MONO} fontSize={8} letterSpacing="0.14em" fill={SUB}>
        PAVEMENT · BANDRA WEST
      </text>

      {/* PASS lane */}
      <line x1={20} y1={206} x2={860} y2={206} stroke="#B6AFA0" strokeWidth={2} strokeDasharray="7 6" />
      <circle cx={20} cy={206} r={3} fill="#B6AFA0" />
      {[190, 300, 430, 570, 700, 820].map((x) => (
        <circle key={x} cx={x} cy={202} r={1.6} fill="rgba(29,29,31,0.35)" />
      ))}

      {/* STOP lane */}
      <line x1={20} y1={150} x2={424} y2={150} stroke={GOLD} strokeWidth={2.5} />
      <circle cx={20} cy={150} r={3} fill={GOLD} />
      {/* gaze ellipse around the window */}
      <ellipse cx={472} cy={150} rx={58} ry={26} fill="none" stroke={LIME_DEEP} strokeWidth={2} strokeDasharray="4 4" />
      <circle cx={472} cy={150} r={4} fill={LIME_DEEP} />
      <line x1={530} y1={150} x2={800} y2={150} stroke={GOLD} strokeWidth={2.5} strokeDasharray="6 6" />
      <text x={640} y={142} textAnchor="middle" fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.12em" fill={GOLD_DEEP}>
        + 4.8s GAZE · 94%
      </text>

      {/* ENTER lane */}
      <path d="M20 84 H 540 C 566 84 566 70 566 60" fill="none" stroke={LIME_DEEP} strokeWidth={2.5} strokeLinecap="round" />
      <circle cx={20} cy={84} r={3} fill={LIME_DEEP} />

      {/* numbered callouts */}
      {[
        { n: "1", x: 36, y: 224, label: "JUMP — no glance" },
        { n: "2", x: 44, y: 122, label: "" },
        { n: "3", x: 44, y: 58, label: "" },
      ].map((c) => (
        <g key={c.n}>
          <circle cx={c.x} cy={c.y} r={10} fill={INK} />
          <text x={c.x} y={c.y + 3.5} textAnchor="middle" fontFamily={MONO} fontSize={10} fontWeight={700} fill="#FAF8F5">
            {c.n}
          </text>
          {c.label && (
            <text x={c.x + 16} y={c.y + 4} fontFamily={MONO} fontSize={9} letterSpacing="0.08em" fill={SUB}>
              {c.label}
            </text>
          )}
        </g>
      ))}

      {/* legend */}
      <g fontFamily={MONO} fontSize={9.5} letterSpacing="0.1em">
        <circle cx={36} cy={250} r={3} fill="#B6AFA0" />
        <text x={46} y={253.5} fill={SUB}>WALK PAST · 2,481 · 0.8 m/s</text>
        <circle cx={296} cy={250} r={3} fill={GOLD} />
        <text x={306} y={253.5} fill={SUB}>STOP · 186 · 7.5% STOP RATE</text>
        <circle cx={586} cy={250} r={3} fill={LIME_DEEP} />
        <text x={596} y={253.5} fill={SUB}>ENTER · 39 · 21.0% CONVERT</text>
      </g>
    </svg>
  )
}

/* ------------------------- 2 · deployment timeline --------------------------- */

const TIMELINE_NODES = [
  { label: "DAY 0", a: "Map windows & zones", b: "PoE box ships overnight" },
  { label: "H +48H", a: "Live on your cameras", b: "Stop rate starts building" },
  { label: "DAY 7", a: "First verified report", b: "Three actions, with evidence" },
  { label: "EVERY MONDAY", a: "A/B verdicts", b: "Keep what wins" },
]

export function DeploymentTimeline() {
  const xs = [104, 356, 602, 806]
  return (
    <svg viewBox="0 0 880 178" className="h-auto w-full" role="img" aria-label="Deployment timeline from day zero to every Monday">
      {/* baseline */}
      <line x1={72} y1={64} x2={836} y2={64} stroke={LINE} strokeWidth={2} />
      <line x1={72} y1={64} x2={512} y2={64} stroke={GOLD} strokeWidth={2} />

      {xs.map((cx, i) => (
        <g key={TIMELINE_NODES[i].label}>
          <circle cx={cx} cy={64} r={8} fill={i === 0 ? GOLD : CARD} stroke={GOLD} strokeWidth={2} />
          <circle cx={cx} cy={64} r={2.5} fill={LIME_DEEP} />
          <text x={cx} y={40} textAnchor="middle" fontFamily={MONO} fontSize={11} fontWeight={700} letterSpacing="0.14em" fill={i === 0 ? GOLD_DEEP : INK}>
            {TIMELINE_NODES[i].label}
          </text>
          <text x={cx} y={86} textAnchor="middle" fontFamily={SANS} fontSize={11} fontWeight={600} fill={INK}>
            {TIMELINE_NODES[i].a}
          </text>
          <text x={cx} y={102} textAnchor="middle" fontFamily={SANS} fontSize={10} fill={SUB}>
            {TIMELINE_NODES[i].b}
          </text>
        </g>
      ))}

      <rect x={530} y={120} width={290} height={30} rx={15} fill="rgba(169,121,43,0.1)" stroke="rgba(169,121,43,0.3)" strokeWidth={1.5} />
      <text x={675} y={139} textAnchor="middle" fontFamily={MONO} fontSize={9.5} fontWeight={700} letterSpacing="0.12em" fill={GOLD_DEEP}>
        NO ELECTRICIAN · NO NEW CAMERAS
      </text>
    </svg>
  )
}

/* --------------------------- 3 · sensor install ------------------------------ */

export function SensorInstallDiagram() {
  return (
    <svg viewBox="0 0 560 300" className="h-auto w-full" role="img" aria-label="Where the sensor lives: existing camera, edge box, PoE cable">
      {/* ceiling */}
      <line x1={0} y1={22} x2={560} y2={22} stroke={INK} strokeWidth={3} strokeLinecap="round" />
      {/* wall */}
      <rect x={0} y={262} width={560} height={26} fill="rgba(29,29,31,0.08)" />

      {/* existing camera */}
      <g>
        <line x1={120} y1={24} x2={120} y2={52} stroke={SUB} strokeWidth={2} />
        <rect x={102} y={52} width={36} height={22} rx={4} fill={WALL} />
        <circle cx={120} cy={74} r={6} fill={GOLD} />
        <text x={120} y={96} textAnchor="middle" fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.1em" fill={INK}>
          EXISTING CAMERA
        </text>
        <text x={120} y={110} textAnchor="middle" fontFamily={MONO} fontSize={8} letterSpacing="0.08em" fill={SUB}>
          YOU ALREADY PAID FOR IT
        </text>
        <rect x={88} y={126} width={64} height={30} rx={8} fill={GOLD_SOFT} stroke="rgba(169,121,43,0.35)" strokeWidth={1.5} />
        <text x={120} y={144} textAnchor="middle" fontFamily={MONO} fontSize={8.5} fontWeight={700} letterSpacing="0.1em" fill={GOLD_DEEP}>
          RTSP / NVR FEED
        </text>
      </g>

      {/* PoE cable */}
      <path d="M140 74 C 200 74 220 120 260 128" fill="none" stroke={GOLD} strokeWidth={2.5} strokeDasharray="6 5" strokeLinecap="round" />
      <text x={228} y={152} fontFamily={MONO} fontSize={8.5} fontWeight={700} letterSpacing="0.1em" fill={GOLD_DEEP}>
        POE · POWER + DATA
      </text>

      {/* edge box */}
      <g>
        <rect x={258} y={96} width={74} height={104} rx={10} fill={CARD} stroke={LINE} strokeWidth={1.5} />
        <rect x={258} y={96} width={74} height={26} rx={10} fill={INK} />
        <circle cx={278} cy={109} r={4} fill={LIME} />
        <text x={286} y={113} fontFamily={MONO} fontSize={8} fontWeight={700} letterSpacing="0.08em" fill="#FAF8F5">
          EDGE
        </text>
        {[136, 152, 168].map((y) => (
          <line key={y} x1={268} y1={y} x2={322} y2={y} stroke="rgba(29,29,31,0.14)" strokeWidth={2} />
        ))}
        <text x={295} y={216} textAnchor="middle" fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.1em" fill={INK}>
          AD LABS EDGE BOX
        </text>
        <text x={295} y={230} textAnchor="middle" fontFamily={MONO} fontSize={8} letterSpacing="0.08em" fill={SUB}>
          12W · WALL-MOUNTED
        </text>
      </g>

      {/* only numbers to cloud */}
      <path d="M350 148 H 430" stroke={LINE} strokeWidth={2} strokeDasharray="4 4" />
      <path d="M428 148 L 420 143 M 428 148 L 420 153" stroke={SUB} strokeWidth={1.6} fill="none" />
      <text x={390} y={140} textAnchor="middle" fontFamily={MONO} fontSize={8} letterSpacing="0.08em" fill={SUB}>
        NUMBERS ONLY
      </text>

      {/* verdict monitor */}
      <g>
        <rect x={434} y={116} width={96} height={64} rx={6} fill={CARD} stroke={LINE} strokeWidth={1.5} />
        <rect x={442} y={124} width={80} height={44} rx={3} fill="#F8F4EA" />
        {[
          { h: 20, c: GOLD },
          { h: 34, c: GOLD },
          { h: 44, c: LINE },
        ].map((b, i) => (
          <rect key={i} x={454} y={162 - b.h} width={46} height={b.h} rx={2} fill={b.c} opacity={b.c === LINE ? 0.5 : 0.9} />
        ))}
        <line x1={446} y1={188} x2={452} y2={188} stroke={INK} strokeWidth={2} />
        <text x={482} y={200} textAnchor="middle" fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.1em" fill={INK}>
          MONDAY BRIEF
        </text>
      </g>

      {/* zero faces stamp */}
      <g transform="rotate(-4 500 250)">
        <rect x={430} y={236} width={110} height={26} rx={13} fill={LIME} stroke={INK} strokeWidth={1.5} />
        <text x={485} y={253} textAnchor="middle" fontFamily={MONO} fontSize={9.5} fontWeight={800} letterSpacing="0.1em" fill={INK}>
          ZERO FACES
        </text>
      </g>
    </svg>
  )
}

/* ----------------------------- 4 · privacy flow ------------------------------ */

export function PrivacyFlowDiagram() {
  return (
    <svg viewBox="0 0 880 240" className="h-auto w-full" role="img" aria-label="Data flow: camera to edge box to numbers only, pixels discarded">
      {/* store zone */}
      <rect x={16} y={40} width={470} height={186} rx={16} fill={GOLD_SOFT2} stroke={LINE} strokeWidth={1.5} />
      <text x={40} y={62} fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.14em" fill={GOLD_DEEP}>
        IN YOUR STORE · ON-PREMISE
      </text>

      {/* camera */}
      <g>
        <rect x={40} y={120} width={76} height={46} rx={8} fill={CARD} stroke={LINE} strokeWidth={1.5} />
        <circle cx={78} cy={143} r={9} fill={INK} />
        <circle cx={78} cy={143} r={3} fill={GOLD} />
        <text x={78} y={188} textAnchor="middle" fontFamily={MONO} fontSize={8} letterSpacing="0.1em" fill={SUB}>
          ORIGIN
        </text>
        <text x={78} y={102} textAnchor="middle" fontFamily={MONO} fontSize={8.5} fontWeight={700} letterSpacing="0.1em" fill={INK}>
          YOUR CAMERA
        </text>
      </g>

      <path d="M124 143 H 160" stroke={SUB} strokeWidth={1.8} />
      <path d="M158 143 L 150 138 M 158 143 L 150 148" stroke={SUB} strokeWidth={1.6} fill="none" />

      {/* edge box */}
      <g>
        <rect x={168} y={104} width={92} height={78} rx={10} fill={CARD} stroke={GOLD} strokeWidth={2} />
        <rect x={168} y={104} width={92} height={22} rx={10} fill={INK} />
        <text x={214} y={119} textAnchor="middle" fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.12em" fill="#FAF8F5">
          EDGE BOX
        </text>
        <text x={214} y={150} textAnchor="middle" fontFamily={MONO} fontSize={8} letterSpacing="0.08em" fill={SUB}>
          PROCESSING
        </text>
        <text x={214} y={166} textAnchor="middle" fontFamily={MONO} fontSize={8} fontWeight={700} letterSpacing="0.1em" fill={GOLD_DEEP}>
          12W · SUB-SECOND
        </text>

        {/* discard */}
        <path d="M214 182 C 214 206 214 206 214 214" stroke={SUB} strokeWidth={1.8} strokeDasharray="4 4" />
        <path d="M204 222 H 224 M 209 216 V 228 M 219 216 V 228" stroke="#c9372c" strokeWidth={1.6} />
        <text x={214} y={236} textAnchor="middle" fontFamily={MONO} fontSize={8} letterSpacing="0.08em" fill="#c9372c">
          PIXELS DISCARDED · FRAMES EXPIRE
        </text>
      </g>

      {/* divider */}
      <line x1={520} y1={46} x2={520} y2={222} stroke={LINE} strokeWidth={1.5} strokeDasharray="5 5" />
      <rect x={504} y={122} width={32} height={18} rx={9} fill={INK} />
      <text x={520} y={134} textAnchor="middle" fontFamily={MONO} fontSize={8} fontWeight={700} fill={LIME}>
        DOCK
      </text>
      <text x={520} y={28} textAnchor="middle" fontFamily={MONO} fontSize={8.5} fontWeight={700} letterSpacing="0.1em" fill={SUB}>
        ONLY NUMBERS CROSS
      </text>

      {/* cloud */}
      <g>
        <rect x={566} y={58} width={260} height={160} rx={16} fill={CARD} stroke={LINE} strokeWidth={1.5} />
        <text x={582} y={80} fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.14em" fill={INK}>
          THE CLOUD · NUMBERS ONLY
        </text>
        <rect x={582} y={94} width={228} height={40} rx={8} fill={GOLD_SOFT2} stroke={LINE} strokeWidth={1} />
        <text x={696} y={119} textAnchor="middle" fontFamily={MONO} fontSize={11} fontWeight={700} letterSpacing="0.12em" fill={INK}>
          TS · DWELL · ENTRY · ZONE
        </text>
        <text x={620} y={164} fontFamily={SANS} fontSize={11} fill={SUB}>
          No frame. No face. No silhouette.
        </text>
        <text x={620} y={182} fontFamily={SANS} fontSize={11} fill={SUB}>
          <tspan fontWeight={700} fill={GOLD_DEEP}>Nothing to re-identify</tspan> — it never exists.
        </text>
        <line x1={582} y1={200} x2={650} y2={200} stroke={LINE} strokeWidth={1} />
        <text x={620} y={210} fontFamily={MONO} fontSize={9} letterSpacing="0.1em" fill={SUB}>
          OUTPUT → MONDAY BRIEF
        </text>
      </g>

      {/* stamp */}
      <g transform="rotate(-5 385 70)">
        <rect x={300} y={58} width={170} height={26} rx={13} fill={LIME} stroke={INK} strokeWidth={1.5} />
        <text x={385} y={75} textAnchor="middle" fontFamily={MONO} fontSize={9.5} fontWeight={800} letterSpacing="0.08em" fill={INK}>
          ZERO VIDEO LEAVES THE STORE
        </text>
      </g>
    </svg>
  )
}

/* ------------------------------ 5 · floor plan -------------------------------- */

export function FloorPlanDiagram() {
  const wall = { stroke: INK, strokeWidth: 3 }
  return (
    <svg viewBox="0 0 720 386" className="h-auto w-full" role="img" aria-label="Store floor plan with hot and cold zones">
      {/* compass */}
      <g fontFamily={MONO} fontSize={9} letterSpacing="0.1em" fill={SUB}>
        <text x={686} y={30} textAnchor="end">N</text>
        <path d="M686 36 L686 24" stroke={SUB} strokeWidth={2} />
      </g>

      {/* store walls */}
      <rect x={24} y={64} width={672} height={226} rx={14} {...wall} fill="#fffdfa" />

      {/* door opening */}
      <line x1={352} y1={64} x2={424} y2={64} stroke={LINE} strokeWidth={3} />
      <path d="M352 64 Q 388 22 424 64" fill="none" stroke={GOLD} strokeWidth={2.5} strokeDasharray="5 4" />
      <text x={388} y={92} textAnchor="middle" fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.1em" fill={GOLD_DEEP}>
        FRONT · THE GLASS
      </text>

      {/* floor zones */}
      <rect x={44} y={96} width={220} height={168} rx={10} fill={GOLD_SOFT2} stroke={GOLD} strokeWidth={1.5} strokeDasharray="6 4" />
      <text x={154} y={146} textAnchor="middle" fontFamily={MONO} fontSize={10} fontWeight={700} letterSpacing="0.1em" fill={GOLD_DEEP}>
        HERO VITRINE
      </text>
      <text x={154} y={164} textAnchor="middle" fontFamily={SANS} fontSize={11} fill={SUB}>
        8.4s dwell · 42% touch
      </text>
      <circle cx={154} cy={186} r={3} fill={GOLD} />

      <rect x={282} y={96} width={156} height={168} rx={10} fill="rgba(212,245,60,0.4)" stroke={LIME_DEEP} strokeWidth={1.5} />
      <text x={360} y={170} textAnchor="middle" fontFamily={MONO} fontSize={10} fontWeight={700} letterSpacing="0.1em" fill="#3d4d1f">
        LEATHER
        <tspan x={360} dy={14}>ISLAND</tspan>
      </text>
      <text x={360} y={196} textAnchor="middle" fontFamily={SANS} fontSize={11} fill="#3d4d1f">
        68% of all traffic
      </text>

      <rect x={456} y={96} width={220} height={86} rx={10} fill="rgba(29,29,31,0.045)" stroke={LINE} strokeWidth={1.5} />
      <text x={566} y={136} textAnchor="middle" fontFamily={MONO} fontSize={10} fontWeight={700} letterSpacing="0.1em" fill={INK}>
        APPAREL
      </text>
      <text x={566} y={152} textAnchor="middle" fontFamily={SANS} fontSize={11} fill={SUB}>
        41% zone dwell
      </text>

      {/* rear dead zone */}
      <rect x={456} y={196} width={220} height={68} rx={10} fill="none" stroke={LINE} strokeWidth={1.5} strokeDasharray="4 4" />
      <text x={566} y={228} textAnchor="middle" fontFamily={MONO} fontSize={9} fontWeight={700} letterSpacing="0.1em" fill={SUB}>
        REAR · 9% · UNDER-LIT
      </text>

      {/* cold corridor */}
      <path d="M428 268 V 84" stroke="rgba(29,29,31,0.2)" strokeWidth={1.5} strokeDasharray="3 3" />
      <text x={432} y={60} fontFamily={MONO} fontSize={8} letterSpacing="0.1em" fill={SUB}>
        1.3 m/s · NO PAUSE
      </text>

      {/* scale bar */}
      <line x1={44} y1={318} x2={124} y2={318} stroke={INK} strokeWidth={2} />
      {[44, 124].map((x) => (
        <line key={x} x1={x} y1={313} x2={x} y2={323} stroke={INK} strokeWidth={2} />
      ))}
      <text x={84} y={336} textAnchor="middle" fontFamily={MONO} fontSize={8.5} letterSpacing="0.08em" fill={SUB}>
        10 M
      </text>

      {/* legend */}
      <g fontFamily={MONO} fontSize={9} letterSpacing="0.1em" fill={SUB}>
        <rect x={320} y={308} width={12} height={12} rx={3} fill={GOLD_SOFT2} stroke={GOLD} strokeWidth={1.5} />
        <text x={340} y={318}>GAZE HOT</text>
        <rect x={430} y={308} width={12} height={12} rx={3} fill="rgba(212,245,60,0.4)" stroke={LIME_DEEP} strokeWidth={1.5} />
        <text x={450} y={318}>TRAFFIC CORE</text>
        <rect x={574} y={308} width={12} height={12} rx={3} fill="none" stroke={LINE} strokeWidth={1.5} strokeDasharray="3 2" />
        <text x={594} y={318}>DEAD ZONE</text>
      </g>
    </svg>
  )
}

/* ------------------------------ 6 · storefront -------------------------------- */

export function StorefrontGlyphs({ count, label }: { count: number; label?: string }) {
  const shown = Math.min(count, 6)
  const more = count > 6
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-end gap-1.5" aria-hidden>
        {Array.from({ length: shown }).map((_, i) => (
          <span
            key={i}
            className="block"
            style={{
              width: 10,
              height: i === 0 ? 17 : 16,
              borderRadius: "4px 4px 2px 2px",
              border: "1.6px solid #A9792B",
              background: i === 0 ? "rgba(212,245,60,0.55)" : "rgba(169,121,43,0.1)",
              boxShadow: i === 0 ? "0 0 0 1px rgba(169,121,43,0.35)" : undefined,
            }}
          />
        ))}
        {more && (
          <span className="flex h-6 items-center rounded-full border border-[rgba(139,124,246,0.35)] px-2 font-mono cosmic-text-2xs font-bold tracking-[0.1em] text-[#8B7CF6]">
            +{count - 6}
          </span>
        )}
      </div>
      <span className="font-mono cosmic-text-2xs font-bold tracking-[0.14em] text-[#16161f]/55">{label}</span>
    </div>
  )
}

/* --------------------------- 7 · sector silhouettes --------------------------- */

export type SectorTag = { title: string; tag: string }

function Silhouette({ title, tag }: SectorTag) {
  return (
    <g>
      {/* awning */}
      <path d="M0 26 h96 q-6 -12 -18 -14 h-60 q-12 2 -18 14 Z" fill={INK} />
      {/* glass */}
      <rect x={8} y={32} width={80} height={52} rx={2} fill={GOLD_SOFT} stroke={LINE} strokeWidth={1.5} />
      <line x1={24} y1={32} x2={24} y2={84} stroke="rgba(169,121,43,0.3)" strokeWidth={1.5} />
      <line x1={40} y1={32} x2={40} y2={84} stroke="rgba(169,121,43,0.3)" strokeWidth={1.5} />
      {/* door */}
      <rect x={64} y={40} width={18} height={44} fill="#fffdfa" stroke={GOLD} strokeWidth={1.6} />
      <circle cx={78} cy={62} r={1.4} fill={INK} />
      {/* plinth */}
      <rect x={-4} y={86} width={104} height={8} fill="rgba(29,29,31,0.12)" />
      {/* labels */}
      <text x={48} y={116} textAnchor="middle" fontFamily={MONO} fontSize={10} fontWeight={700} letterSpacing="0.12em" fill={INK}>
        {title.toUpperCase()}
      </text>
      <text x={48} y={132} textAnchor="middle" fontFamily={MONO} fontSize={8} letterSpacing="0.06em" fill={GOLD_DEEP}>
        {tag}
      </text>
      {/* signal dot */}
      <circle cx={48} cy={142} r={2.4} fill={LIME_DEEP} />
    </g>
  )
}

export function SectorSilhouettes({ sectors }: { sectors: SectorTag[] }) {
  const step = 200
  return (
    <svg viewBox="0 0 800 168" className="h-auto w-full" role="img" aria-label="Storefront silhouettes by sector">
      {sectors.map((s, i) => (
        <g key={s.title} transform={`translate(${40 + i * step} 8)`}>
          <Silhouette {...s} />
        </g>
      ))}
      <text x={760} y={164} textAnchor="end" fontFamily={MONO} fontSize={8} letterSpacing="0.1em" fill={SUB}>
        THE SAME INSTRUMENT, SHAPED BY THE SAME PHYSICS
      </text>
    </svg>
  )
}
