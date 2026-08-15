import { useState, useEffect, useMemo } from "react";
import { runEvaluation, listEvalRuns, getEvalRun, downloadEvalRunUrl } from "../api/client";
import MetricCard from "./MetricCard.jsx";
import BarChart from "./BarChart.jsx";

// Client-side recomputation of Precision@K for a custom K, using the
// ACTUAL retrieved_titles stored from the real run - no re-running the
// pipeline needed, but every number still traces back to a real run.
function matchesExpected(title, expectedSources) {
  const t = title.toLowerCase();
  return expectedSources.some((exp) => t.includes(exp.toLowerCase()));
}

function precisionAtK(retrievedTitles, expectedSources, k) {
  const topK = retrievedTitles.slice(0, k);
  if (topK.length === 0) return 0;
  const matches = topK.filter((t) => matchesExpected(t, expectedSources)).length;
  return matches / k;
}

export default function EvalDashboard() {
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [running, setRunning] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [customK, setCustomK] = useState(5);
  const [error, setError] = useState("");

  async function refreshRunsList() {
    setLoadingRuns(true);
    try {
      const list = await listEvalRuns();
      setRuns(list);
      if (list.length > 0 && !selectedRun) {
        const detail = await getEvalRun(list[0].run_id);
        setSelectedRun(detail);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingRuns(false);
    }
  }

  useEffect(() => {
    refreshRunsList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleRunEvaluation() {
    setRunning(true);
    setError("");
    try {
      const result = await runEvaluation();
      if (result.not_evaluated_reason) {
        setError(result.not_evaluated_reason);
      } else {
        setSelectedRun(result);
        await refreshRunsList();
        setCustomK(result.aggregate?.top_k || 5);
      }
    } catch (err) {
      console.error(err);
      setError("Evaluation run failed. Check backend logs and your GOOGLE_API_KEY.");
    } finally {
      setRunning(false);
    }
  }

  async function handleSelectRun(runId) {
    const detail = await getEvalRun(runId);
    setSelectedRun(detail);
    setCustomK(detail.aggregate?.top_k || 5);
  }

  const recomputed = useMemo(() => {
    if (!selectedRun || !selectedRun.results) return null;
    const successful = selectedRun.results.filter((r) => !r.error);
    if (successful.length === 0) return null;

    const perQuestion = successful.map((r) => ({
      id: r.id,
      precision: precisionAtK(r.retrieved_titles, r.expected_sources, customK),
      success: r.retrieved_titles.some((t) => matchesExpected(t, r.expected_sources)),
      latency: r.latency_ms,
    }));

    const avgPrecision = perQuestion.reduce((a, b) => a + b.precision, 0) / perQuestion.length;
    const successRate = perQuestion.filter((p) => p.success).length / perQuestion.length;

    return { perQuestion, avgPrecision, successRate };
  }, [selectedRun, customK]);

  const agg = selectedRun?.aggregate;

  return (
    <div className="flex flex-col gap-6 p-6 overflow-y-auto h-full">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold">Evaluation Dashboard</h2>
          <p className="text-xs text-gray-400">
            Runs the real 10-question benchmark against the live ScholarAgent pipeline. No mocked results.
          </p>
        </div>
        <button
          onClick={handleRunEvaluation}
          disabled={running}
          className="bg-accent hover:bg-blue-600 disabled:bg-gray-600 text-white text-sm font-medium px-4 py-2 rounded-lg"
        >
          {running ? "Running 10 real questions… this can take a few minutes" : "Run Evaluation"}
        </button>
      </div>

      {error && (
        <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-lg p-3">{error}</div>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-gray-400">Past runs:</span>
        {loadingRuns && <span className="text-xs text-gray-500">loading…</span>}
        {runs.map((r) => (
          <button
            key={r.run_id}
            onClick={() => handleSelectRun(r.run_id)}
            className={`text-xs px-2 py-1 rounded-full border ${
              selectedRun?.run_id === r.run_id
                ? "bg-accent border-accent text-white"
                : "border-border text-gray-400 hover:text-gray-200"
            }`}
          >
            {new Date(r.created_at).toLocaleString()}
          </button>
        ))}
        {runs.length === 0 && !loadingRuns && (
          <span className="text-xs text-gray-500">No runs yet — click "Run Evaluation" above.</span>
        )}
      </div>

      {selectedRun && agg && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            <MetricCard
              label={`Retrieval Precision@${customK}`}
              value={recomputed ? recomputed.avgPrecision : agg.retrieval_precision_at_k}
              tone="good"
            />
            <MetricCard
              label="Retrieval Success Rate"
              value={recomputed ? recomputed.successRate : agg.retrieval_success_rate}
              tone="good"
            />
            <MetricCard label="Citation Verification Accuracy" value={agg.citation_verification_accuracy} tone="good" />
            <MetricCard label="Unsupported Claim Rate" value={agg.unsupported_claim_rate} tone="bad" />
            <MetricCard label="Avg Latency" value={agg.latency.average_ms} kind="ms" />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-panel border border-border rounded-lg p-4">
              <div className="text-xs text-gray-400 mb-1">Total Questions</div>
              <div className="text-lg font-semibold">{agg.total_questions}</div>
            </div>
            <div className="bg-panel border border-border rounded-lg p-4">
              <div className="text-xs text-gray-400 mb-1">Successful / Failed</div>
              <div className="text-lg font-semibold">{agg.successful_runs} / {agg.failed_runs}</div>
            </div>
            <MetricCard label="Min Latency" value={agg.latency.min_ms} kind="ms" />
            <MetricCard label="Max Latency" value={agg.latency.max_ms} kind="ms" />
          </div>

          <div className="bg-panel border border-border rounded-lg p-4">
            <label className="text-xs text-gray-400">
              Precision@K — K = {customK} (recomputed live from this run's actual retrieved papers)
            </label>
            <input
              type="range"
              min={1}
              max={10}
              value={customK}
              onChange={(e) => setCustomK(Number(e.target.value))}
              className="w-full mt-2"
            />
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-panel border border-border rounded-lg p-4">
              <div className="text-sm font-semibold mb-3">Precision@{customK} per question</div>
              {recomputed && (
                <BarChart
                  data={recomputed.perQuestion}
                  labelKey="id"
                  valueKey="precision"
                  valueFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                  color="#2563eb"
                />
              )}
            </div>
            <div className="bg-panel border border-border rounded-lg p-4">
              <div className="text-sm font-semibold mb-3">Latency per question (ms)</div>
              {recomputed && (
                <BarChart data={recomputed.perQuestion} labelKey="id" valueKey="latency" color="#22c55e" />
              )}
            </div>
          </div>

          <div className="flex gap-2">
            <a
              href={downloadEvalRunUrl(selectedRun.run_id, "json")}
              className="text-xs border border-border rounded-lg px-3 py-2 hover:bg-panel"
            >
              Download JSON report
            </a>
            <a
              href={downloadEvalRunUrl(selectedRun.run_id, "csv")}
              className="text-xs border border-border rounded-lg px-3 py-2 hover:bg-panel"
            >
              Download CSV report
            </a>
          </div>

          <div className="bg-panel border border-border rounded-lg overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-gray-400 border-b border-border">
                <tr>
                  <th className="text-left p-2">Question</th>
                  <th className="text-left p-2">Expected Source</th>
                  <th className="text-left p-2">Retrieved Match</th>
                  <th className="text-left p-2">Citation Accuracy</th>
                  <th className="text-left p-2">Unsupported Rate</th>
                  <th className="text-left p-2">Latency</th>
                  <th className="text-left p-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {selectedRun.results.map((r) => (
                  <tr key={r.id} className="border-b border-border/50">
                    <td className="p-2 max-w-xs truncate" title={r.query}>{r.query}</td>
                    <td className="p-2 text-gray-400">{r.expected_sources.join(", ")}</td>
                    <td className="p-2">
                      {r.error ? (
                        "—"
                      ) : r.retrieved_titles.some((t) => matchesExpected(t, r.expected_sources)) ? (
                        <span className="text-green-400">matched</span>
                      ) : (
                        <span className="text-red-400">no match</span>
                      )}
                    </td>
                    <td className="p-2">
                      {r.per_question_metrics?.citation_verification_accuracy != null
                        ? `${(r.per_question_metrics.citation_verification_accuracy * 100).toFixed(0)}%`
                        : "Not evaluated"}
                    </td>
                    <td className="p-2">
                      {r.per_question_metrics?.unsupported_claim_rate != null
                        ? `${(r.per_question_metrics.unsupported_claim_rate * 100).toFixed(0)}%`
                        : "Not evaluated"}
                    </td>
                    <td className="p-2">{r.latency_ms ? `${r.latency_ms.toFixed(0)} ms` : "—"}</td>
                    <td className="p-2">
                      {r.error ? (
                        <span className="text-red-400" title={r.error}>failed</span>
                      ) : (
                        <span className="text-green-400">ok</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {selectedRun && !agg && (
        <div className="text-sm text-gray-400">{selectedRun.not_evaluated_reason || "Not evaluated."}</div>
      )}
    </div>
  );
}
