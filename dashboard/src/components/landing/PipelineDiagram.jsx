const STAGES = [
  { id: "services", title: "Microservices", sub: "4x Spring Boot", glyph: "grid" },
  { id: "kafka", title: "Kafka", sub: "logs topic", glyph: "stream" },
  { id: "detector", title: "Anomaly Detector", sub: "Drain3 + LSTM", glyph: "wave" },
  { id: "agent", title: "Local LLM Agent", sub: "qwen2.5:3b", glyph: "brain" },
  { id: "remediation", title: "Remediation", sub: "verify + rollback", glyph: "shield" },
];

const BOX_W = 150;
const BOX_H = 92;
const STEP = 206;
const X0 = 13;
const Y = 44;

function Glyph({ kind, x, y }) {
  const t = `translate(${x} ${y})`;
  if (kind === "grid") {
    return (
      <g transform={t} className="pd-glyph">
        <rect x="0" y="0" width="7" height="7" rx="1.5" />
        <rect x="10" y="0" width="7" height="7" rx="1.5" />
        <rect x="0" y="10" width="7" height="7" rx="1.5" />
        <rect x="10" y="10" width="7" height="7" rx="1.5" />
      </g>
    );
  }
  if (kind === "stream") {
    return (
      <g transform={t} className="pd-glyph pd-glyph--stroke">
        <path d="M0 2 H17" />
        <path d="M0 8.5 H17" />
        <path d="M0 15 H17" />
      </g>
    );
  }
  if (kind === "wave") {
    return (
      <g transform={t} className="pd-glyph pd-glyph--stroke">
        <path d="M0 12 L4 12 L6 4 L9 17 L12 9 L14 12 L17 12" />
      </g>
    );
  }
  if (kind === "brain") {
    return (
      <g transform={t} className="pd-glyph pd-glyph--stroke">
        <circle cx="5" cy="6" r="3.2" />
        <circle cx="13" cy="5" r="2.6" />
        <circle cx="9" cy="14" r="3" />
        <path d="M7 8 L8 11" />
        <path d="M12 7 L10.5 11.5" />
      </g>
    );
  }
  return (
    <g transform={t} className="pd-glyph pd-glyph--stroke">
      <path d="M8.5 1 L16 4.5 V10 C16 14 12.5 16.5 8.5 18 C4.5 16.5 1 14 1 10 V4.5 Z" />
      <path d="M5.5 9.5 L7.8 12 L11.8 6.5" />
    </g>
  );
}

export function PipelineDiagram() {
  return (
    <div className="pipeline-scroll">
      <svg
        className="pipeline-svg"
        viewBox="0 0 1000 180"
        role="img"
        aria-labelledby="pd-title pd-desc"
        preserveAspectRatio="xMidYMid meet"
      >
        <title id="pd-title">The AI-Ops pipeline</title>
        <desc id="pd-desc">
          Logs flow from four Spring Boot microservices into a Kafka topic, then into an anomaly
          detector built from Drain3 template mining and an LSTM autoencoder, then into a local LLM
          agent that writes a root-cause report, and finally into a confidence-gated remediation step
          that verifies its own fix and can roll it back.
        </desc>

        {STAGES.slice(0, -1).map((stage, i) => {
          const x1 = X0 + BOX_W + i * STEP;
          return (
            <g key={`link-${stage.id}`}>
              <line className="pd-link" x1={x1} y1={Y + BOX_H / 2} x2={x1 + STEP - BOX_W} y2={Y + BOX_H / 2} />
              <polygon
                className="pd-arrow"
                points={`${x1 + STEP - BOX_W},${Y + BOX_H / 2} ${x1 + STEP - BOX_W - 7},${Y + BOX_H / 2 - 4.5} ${x1 + STEP - BOX_W - 7},${Y + BOX_H / 2 + 4.5}`}
              />
              <circle
                className="pd-packet"
                r="4"
                cx={x1}
                cy={Y + BOX_H / 2}
                style={{ animationDelay: `${i * 0.45}s` }}
              />
            </g>
          );
        })}

        {STAGES.map((stage, i) => {
          const x = X0 + i * STEP;
          return (
            <g key={stage.id} className="pd-stage">
              <rect className="pd-box" x={x} y={Y} width={BOX_W} height={BOX_H} rx="10" />
              <Glyph kind={stage.glyph} x={x + 16} y={Y + 15} />
              <text className="pd-step" x={x + BOX_W - 14} y={Y + 26} textAnchor="end">
                {String(i + 1).padStart(2, "0")}
              </text>
              <text className="pd-title-text" x={x + 16} y={Y + 58}>
                {stage.title}
              </text>
              <text className="pd-sub-text" x={x + 16} y={Y + 76}>
                {stage.sub}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
