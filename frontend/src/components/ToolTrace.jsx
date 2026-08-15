/**
 * Shows what the agent actually did for the last query: which
 * sub-questions it planned, how many papers/chunks/web results it used,
 * and the claim-level citation verification breakdown - this is what
 * makes the agent's reasoning and evidence-grounding visible, not a
 * black box.
 */
export default function ToolTrace({ trace, verifiedClaims }) {
  if (!trace) return null;

  const supported = (verifiedClaims || []).filter((c) => c.verdict === "SUPPORTED").length;
  const unsupported = (verifiedClaims || []).filter((c) => c.verdict === "UNSUPPORTED").length;

  return (
    <div className="bg-panel border border-border rounded-lg p-3 text-xs text-gray-400 space-y-3">
      <div className="font-semibold text-gray-200">Last run trace</div>

      {trace.sub_questions?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {trace.sub_questions.map((sq, i) => (
            <span key={i} className="bg-[#1d2433] text-[#7aa2ff] rounded-full px-2 py-0.5">
              {sq.length > 36 ? sq.slice(0, 36) + "…" : sq}
            </span>
          ))}
        </div>
      )}

      <div className="flex justify-between"><span>📄 Papers found</span><span>{trace.papers_found}</span></div>
      <div className="flex justify-between"><span>📚 RAG chunks used</span><span>{trace.rag_chunks_used}</span></div>
      <div className="flex justify-between">
        <span>🌐 Web results</span>
        <span>{trace.web_verification_ran ? trace.web_results_used : "skipped"}</span>
      </div>

      <div className="border-t border-border pt-2">
        <div className="font-semibold text-gray-200 mb-1">Claim verification</div>
        <div className="flex justify-between text-green-400">
          <span>✅ Supported claims</span><span>{supported}</span>
        </div>
        <div className="flex justify-between text-red-400">
          <span>⚠️ Unsupported claims</span><span>{unsupported}</span>
        </div>
      </div>
    </div>
  );
}
