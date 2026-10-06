import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { config, TEAM } from "../config.js";
import { useForcedTheme } from "../theme/ThemeContext.jsx";
import { PipelineDiagram } from "../components/landing/PipelineDiagram.jsx";
import { hdfs, llmLatency, pipelineIntegrity } from "../data/benchmarkFigures.js";

const NAV = [
  { href: "#problem", label: "Problem" },
  { href: "#how", label: "How it works" },
  { href: "#capabilities", label: "Capabilities" },
  { href: "#results", label: "Results" },
  { href: "#stack", label: "Stack" },
  { href: "#team", label: "Team" },
];

const STEPS = [
  {
    n: "01",
    title: "Every request carries a trace id",
    body:
      "A servlet filter mints a traceId at the edge and a client interceptor forwards it on every hop, so one order's path across four services is recoverable from the logs alone.",
  },
  {
    n: "02",
    title: "Logs ship themselves",
    body:
      "Filebeat autodiscovers labeled containers, reads Docker's JSON log files and publishes to a Kafka topic partitioned by traceId. No application code participates in shipping.",
  },
  {
    n: "03",
    title: "Templates, then reconstruction error",
    body:
      "Drain3 mines each line down to a stable template id. An LSTM autoencoder trained only on healthy traffic replays the sequence; how badly it fails to reconstruct it is the anomaly score.",
  },
  {
    n: "04",
    title: "A local model explains it",
    body:
      "A flagged trace, its ordered log lines and the static dependency graph go to a quantized 3B model running on the same machine, which returns a structured root-cause report with a confidence.",
  },
  {
    n: "05",
    title: "Act only when it is safe to",
    body:
      "Above a confidence gate, and only when the diagnosis matches a known pattern, a playbook applies a fix, independently re-tests it, and rolls back if that test fails.",
  },
];

const CAPABILITIES = [
  {
    title: "Unsupervised anomaly detection",
    body:
      "Trained on normal traffic only, so no labeled failure dataset is needed. Missing steps, wrong ordering, unseen templates and timing drift all surface as reconstruction error.",
    tag: "Drain3 + LSTM",
  },
  {
    title: "Root-cause analysis, not log search",
    body:
      "The agent receives the full reconstructed trace plus the service dependency graph and returns a structured verdict: root cause, affected services, reasoning, and a confidence score.",
    tag: "Local LLM",
  },
  {
    title: "Confidence-gated auto-remediation",
    body:
      "Every action is gated on confidence and pattern match, verified by an independent re-test, and reversible. A failed verification triggers rollback and escalation instead of a silent retry.",
    tag: "Verify + rollback",
  },
  {
    title: "Zero paid APIs",
    body:
      "The model runs locally through Ollama. No API keys, no per-token cost, and no log data leaves the machine it was generated on.",
    tag: "Runs offline",
  },
];

const STACK = [
  { group: "Services", items: ["Java 17", "Spring Boot 3.3", "SLF4J MDC", "Logback JSON encoder"] },
  { group: "Pipeline", items: ["Filebeat 8.13", "Apache Kafka 7.6", "Zookeeper"] },
  { group: "Detection", items: ["Python 3.11", "FastAPI", "Drain3", "PyTorch 2.3"] },
  { group: "Agent", items: ["Ollama", "qwen2.5:3b", "SQLite", "JWT + bcrypt"] },
  { group: "Interface", items: ["React 18", "Vite 5", "React Router", "nginx"] },
  { group: "Runtime", items: ["Docker Compose", "13 services", "one bridge network"] },
];

function pct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function Landing() {
  useForcedTheme("dark");
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="landing">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <header className={`lp-nav${scrolled ? " lp-nav--scrolled" : ""}`}>
        <div className="lp-nav-inner">
          <a className="lp-brand" href="#main">
            <span className="lp-brand-mark" aria-hidden="true" />
            <span>
              AI<span className="lp-brand-dim">-</span>OPS
            </span>
          </a>

          <nav className="lp-nav-links" aria-label="Sections">
            {NAV.map((item) => (
              <a key={item.href} href={item.href}>
                {item.label}
              </a>
            ))}
          </nav>

          <div className="lp-nav-actions">
            <a
              className="lp-link-quiet"
              href={config.GITHUB_URL}
              target="_blank"
              rel="noreferrer noopener"
            >
              GitHub
            </a>
            <Link className="lp-btn lp-btn--primary lp-btn--sm" to="/login">
              Sign in
            </Link>
          </div>
        </div>
      </header>

      <main id="main">
        <section className="lp-hero" aria-labelledby="hero-heading">
          <div className="lp-shell">
            <p className="lp-eyebrow">Autonomous log anomaly detection &amp; root cause analysis</p>
            <h1 id="hero-heading" className="lp-hero-title">
              Finds the failure your log search never fires on, explains it, and fixes the ones it can
              prove it fixed.
            </h1>
            <p className="lp-hero-sub">
              A closed loop over four microservices: structural anomaly detection on trace sequences,
              a locally hosted language model for root cause, and remediation that verifies its own
              work before it is trusted.
            </p>

            <div className="lp-hero-actions">
              <Link className="lp-btn lp-btn--primary" to="/login">
                Open the dashboard
              </Link>
              <a
                className="lp-btn lp-btn--ghost"
                href={config.GITHUB_URL}
                target="_blank"
                rel="noreferrer noopener"
              >
                Read the source
              </a>
            </div>

            <ul className="lp-hero-facts">
              <li>
                <strong>{pct(hdfs.lstm.precision)}</strong>
                <span>precision on labeled HDFS data</span>
              </li>
              <li>
                <strong>{pct(hdfs.lstm.falsePositiveRate)}</strong>
                <span>false-alarm rate, against {pct(hdfs.keyword.falsePositiveRate)} for keywords</span>
              </li>
              <li>
                <strong>{llmLatency.gpuSeconds}s</strong>
                <span>per incident report on a local GPU</span>
              </li>
            </ul>

            <PipelineDiagram />
          </div>
        </section>

        <section id="problem" className="lp-section" aria-labelledby="problem-heading">
          <div className="lp-shell lp-split">
            <div>
              <p className="lp-kicker">The problem</p>
              <h2 id="problem-heading">Grepping for ERROR only finds failures that announce themselves.</h2>
            </div>
            <div className="lp-prose">
              <p>
                In a microservice system one user action becomes a dozen log lines spread across
                several containers. When something breaks, the lines that matter are interleaved with
                everything else, and the only thing tying them together is a trace id nobody is
                reading.
              </p>
              <p>
                The harder case is the failure that logs nothing alarming at all. A dependency that
                answers correctly but two seconds late, a step that is skipped, a sequence that runs
                out of order: every line is <code>INFO</code>, so a keyword rule stays silent. On the
                labeled HDFS benchmark the keyword baseline did fire &mdash; on{" "}
                <strong>{hdfs.keyword.falseAlarms.toLocaleString()}</strong> of{" "}
                {hdfs.testNormal.toLocaleString()} healthy blocks. A detector that noisy gets muted
                within a week.
              </p>
              <p>
                What is needed is a model of what a <em>healthy</em> trace looks like, so deviation
                is measurable without anyone having to enumerate the failures in advance.
              </p>
            </div>
          </div>
        </section>

        <section id="how" className="lp-section lp-section--alt" aria-labelledby="how-heading">
          <div className="lp-shell">
            <p className="lp-kicker">How it works</p>
            <h2 id="how-heading">Five stages, no human in the path.</h2>
            <ol className="lp-steps">
              {STEPS.map((step) => (
                <li key={step.n}>
                  <span className="lp-step-n" aria-hidden="true">
                    {step.n}
                  </span>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="capabilities" className="lp-section" aria-labelledby="cap-heading">
          <div className="lp-shell">
            <p className="lp-kicker">Capabilities</p>
            <h2 id="cap-heading">What it actually does.</h2>
            <div className="lp-cards">
              {CAPABILITIES.map((cap) => (
                <article className="lp-card" key={cap.title}>
                  <span className="lp-card-tag">{cap.tag}</span>
                  <h3>{cap.title}</h3>
                  <p>{cap.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="results" className="lp-section lp-section--alt" aria-labelledby="results-heading">
          <div className="lp-shell">
            <p className="lp-kicker">Results</p>
            <h2 id="results-heading">Measured on public labeled data, not asserted.</h2>
            <p className="lp-section-lead">
              {hdfs.blocksTotal.toLocaleString()} blocks from {hdfs.dataset} (
              {hdfs.blocksAnomalous.toLocaleString()} anomalous, the natural {hdfs.anomalyRate} rate),
              held out as {hdfs.testNormal.toLocaleString()} normal and{" "}
              {hdfs.testAnomaly.toLocaleString()} anomalous blocks. The operating point was chosen on
              validation normals only &mdash; test labels were never used to pick it.
            </p>

            <div className="lp-table-wrap">
              <table className="lp-table">
                <caption className="sr-only">
                  Precision, recall, F1 and false-alarm rate for the LSTM detector and the keyword
                  baseline on the held-out HDFS test set
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Metric</th>
                    <th scope="col">{hdfs.lstm.label}</th>
                    <th scope="col">{hdfs.keyword.label}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row">Precision</th>
                    <td className="lp-win">{hdfs.lstm.precision.toFixed(3)}</td>
                    <td>{hdfs.keyword.precision.toFixed(3)}</td>
                  </tr>
                  <tr>
                    <th scope="row">False-alarm rate</th>
                    <td className="lp-win">{pct(hdfs.lstm.falsePositiveRate)}</td>
                    <td>{pct(hdfs.keyword.falsePositiveRate)}</td>
                  </tr>
                  <tr>
                    <th scope="row">Healthy blocks wrongly flagged</th>
                    <td className="lp-win">{hdfs.lstm.falseAlarms.toLocaleString()}</td>
                    <td>{hdfs.keyword.falseAlarms.toLocaleString()}</td>
                  </tr>
                  <tr>
                    <th scope="row">Recall</th>
                    <td>{hdfs.lstm.recall.toFixed(3)}</td>
                    <td className="lp-win">{hdfs.keyword.recall.toFixed(3)}</td>
                  </tr>
                  <tr>
                    <th scope="row">F1</th>
                    <td className="lp-win">{hdfs.lstm.f1.toFixed(3)}</td>
                    <td>{hdfs.keyword.f1.toFixed(3)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="lp-callouts">
              <div className="lp-callout">
                <h3>The advantage is precision and false alarms</h3>
                <p>
                  At the {hdfs.operatingPoint} operating point the detector flags{" "}
                  {hdfs.lstm.falseAlarms} healthy blocks where keyword matching flags{" "}
                  {hdfs.keyword.falseAlarms.toLocaleString()} &mdash; a{" "}
                  {hdfs.falseAlarmReduction} reduction in false alarms at{" "}
                  {(hdfs.lstm.precision / hdfs.keyword.precision).toFixed(1)}x the precision. It also
                  wins at matched recall: held to the baseline&rsquo;s own{" "}
                  {hdfs.keyword.recall.toFixed(3)} recall it reaches{" "}
                  {hdfs.matchedRecallPrecision.toFixed(3)} precision against{" "}
                  {hdfs.keyword.precision.toFixed(3)}.
                </p>
              </div>
              <div className="lp-callout lp-callout--caution">
                <h3>Recall is plainly lower</h3>
                <p>
                  The detector catches {hdfs.lstm.recall.toFixed(3)} of anomalies where keyword
                  matching catches {hdfs.keyword.recall.toFixed(3)}. ROC-AUC is{" "}
                  {hdfs.rocAuc.toFixed(4)} and average precision {hdfs.averagePrecision.toFixed(4)}:
                  moderate, not strong. A 16K-parameter model transferred to a foreign log domain is
                  well short of purpose-built HDFS detectors, which reach F1 above 0.9. This is a
                  precision-first detector and the recall cost is real.
                </p>
              </div>
            </div>

            <dl className="lp-stats">
              <div>
                <dt>ROC-AUC</dt>
                <dd>{hdfs.rocAuc.toFixed(4)}</dd>
              </div>
              <div>
                <dt>Average precision</dt>
                <dd>{hdfs.averagePrecision.toFixed(4)}</dd>
              </div>
              <div>
                <dt>Incident report, CPU to GPU</dt>
                <dd>
                  {llmLatency.cpuSeconds}s &rarr; {llmLatency.gpuSeconds}s
                </dd>
              </div>
              <div>
                <dt>Log delivery / assembly</dt>
                <dd>
                  {pipelineIntegrity.delivery} / {pipelineIntegrity.assembly}
                </dd>
              </div>
            </dl>

            <p className="lp-footnote">
              Full methodology, confusion matrices, threshold sweeps and the list of superseded runs
              are in <code>benchmark/RESULTS.md</code> in the repository.
            </p>
          </div>
        </section>

        <section id="stack" className="lp-section" aria-labelledby="stack-heading">
          <div className="lp-shell">
            <p className="lp-kicker">Tech stack</p>
            <h2 id="stack-heading">Everything runs on one machine.</h2>
            <div className="lp-stack">
              {STACK.map((group) => (
                <div className="lp-stack-group" key={group.group}>
                  <h3>{group.group}</h3>
                  <ul>
                    {group.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="team" className="lp-section lp-section--alt" aria-labelledby="team-heading">
          <div className="lp-shell">
            <p className="lp-kicker">Team {TEAM.id}</p>
            <h2 id="team-heading">Built as a final-year project.</h2>
            <ul className="lp-team">
              {TEAM.members.map((member) => (
                <li key={member}>
                  <span className="lp-avatar" aria-hidden="true">
                    {member
                      .split(" ")
                      .map((part) => part[0])
                      .join("")
                      .slice(0, 2)}
                  </span>
                  <span className="lp-team-name">{member}</span>
                </li>
              ))}
            </ul>
            <p className="lp-team-meta">
              {TEAM.institution}, {TEAM.university} &middot; Team ID {TEAM.id} &middot; Guide{" "}
              {TEAM.guide}
            </p>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-shell lp-footer-inner">
          <div>
            <span className="lp-brand lp-brand--footer">
              AI<span className="lp-brand-dim">-</span>OPS
            </span>
            <p>Autonomous log anomaly detection and root cause analysis for microservices.</p>
          </div>
          <div className="lp-footer-links">
            <a href={config.GITHUB_URL} target="_blank" rel="noreferrer noopener">
              github.com/yuvrajpawar09/AI-Ops
            </a>
            <a
              href={`${config.GITHUB_URL}/blob/main/LICENSE`}
              target="_blank"
              rel="noreferrer noopener"
            >
              MIT License
            </a>
            <Link to="/login">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
