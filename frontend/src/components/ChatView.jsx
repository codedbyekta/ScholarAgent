import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../api/client";
import MessageBubble from "./MessageBubble.jsx";
import ToolTrace from "./ToolTrace.jsx";
import FileUpload from "./FileUpload.jsx";

function getOrCreateSessionId() {
  let id = localStorage.getItem("scholaragent_session_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("scholaragent_session_id", id);
  }
  return id;
}

export default function ChatView() {
  const [sessionId] = useState(getOrCreateSessionId);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I'm ScholarAgent. Ask me a research question (e.g. *\"What is the Transformer architecture?\"*) and I'll search papers, verify claims, and give you a cited answer.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastTrace, setLastTrace] = useState(null);
  const [lastClaims, setLastClaims] = useState([]);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend() {
    const query = input.trim();
    if (!query || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setInput("");
    setLoading(true);

    try {
      const result = await sendChatMessage(sessionId, query);
      setMessages((prev) => [...prev, { role: "assistant", content: result.answer }]);
      setLastTrace(result.trace);
      setLastClaims(result.verified_claims || []);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Is the backend running and is GOOGLE_API_KEY configured?" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex h-full">
      <aside className="w-72 border-r border-border p-5 flex flex-col gap-4 overflow-y-auto">
        <div>
          <h1 className="text-lg font-semibold">ScholarAgent</h1>
          <p className="text-xs text-gray-400 -mt-1">Autonomous research paper assistant</p>
        </div>

        <FileUpload sessionId={sessionId} onUploaded={(doc) => setUploadedDocs((prev) => [...prev, doc])} />

        {uploadedDocs.length > 0 && (
          <div className="text-xs text-gray-400 space-y-1">
            <strong className="text-gray-200">Indexed documents:</strong>
            {uploadedDocs.map((d, i) => (
              <div key={i}>{d.doc_name} ({d.chunks_indexed} chunks)</div>
            ))}
          </div>
        )}

        <ToolTrace trace={lastTrace} verifiedClaims={lastClaims} />
      </aside>

      <main className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">
          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} />
          ))}
          {loading && (
            <div className="self-start bg-panel border border-border rounded-lg px-4 py-3 text-sm text-gray-400">
              Planning → searching papers → verifying → writing cited answer…
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="flex gap-2 p-4 border-t border-border">
          <textarea
            rows={2}
            placeholder="Ask a research question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-[#14161d] border border-border rounded-lg p-3 text-sm resize-none"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="bg-accent hover:bg-blue-600 disabled:bg-gray-600 text-white text-sm font-medium px-5 rounded-lg"
          >
            Send
          </button>
        </div>
      </main>
    </div>
  );
}
